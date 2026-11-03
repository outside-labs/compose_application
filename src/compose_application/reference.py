"""Synthetic local work-item REST application and offline acceptance command."""

import argparse
import asyncio
from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass
import json
from pathlib import Path
import re
import sys
from tempfile import TemporaryDirectory

from .service import ServiceConfig, _dependencies, application


@dataclass(frozen=True)
class WorkItem:
    key: str
    title: str
    done: bool = False

    def __post_init__(self):
        if type(self.key) is not str or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", self.key):
            raise ValueError("Invalid work item key.")
        if type(self.title) is not str or not 1 <= len(self.title) <= 200 or type(self.done) is not bool:
            raise ValueError("Invalid work item fields.")
        try:
            self.title.encode("utf-8")
        except UnicodeError:
            raise ValueError("Invalid work item text.") from None


class _RevisionApp:
    def __init__(self, app, expected, returned):
        self.app, self.state, self.expected, self.returned = app, app.state, expected, returned
        self.max_body_size = app.max_body_size

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        expected_token, returned_token = self.expected.set(None), self.returned.set(None)
        try:
            path, root = scope["path"], scope.get("root_path", "").rstrip("/")
            if root and path.startswith(root + "/"):
                path = path[len(root):]
            if scope["method"] in ("PATCH", "DELETE") and path.startswith("/work-items/") and "/" not in path[len("/work-items/"):] and path != "/work-items/":
                headers = [value for key, value in scope.get("headers", ()) if key.lower() == b"if-match"]
                match = re.fullmatch(rb'"([1-9][0-9]{0,18})"', headers[0]) if len(headers) == 1 else None
                if match is None or int(match[1]) > 9223372036854775807:
                    status, code = (428, "precondition_required") if not headers else (400, "precondition")
                    body = json.dumps({"error": {"code": code, "message": "Supply one canonical revision in If-Match.", "details": []}}).encode()
                    await send({"type": "http.response.start", "status": status, "headers": [
                        (b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]})
                    await send({"type": "http.response.body", "body": body})
                    return
                self.expected.set(match[1].decode("ascii"))
            async def response(event):
                if event["type"] == "http.response.start" and 200 <= event["status"] < 300 and self.returned.get() is not None:
                    event = {**event, "headers": [*event["headers"], (b"etag", ('"' + self.returned.get() + '"').encode("ascii"))]}
                await send(event)
            await self.app(scope, receive, response)
        finally:
            self.expected.reset(expected_token)
            self.returned.reset(returned_token)


@asynccontextmanager
async def reference_application(database):
    """Open the public synthetic work-item example; caller owns local HTTP serving."""
    api, adapter = _dependencies()
    expected, returned = ContextVar("expected_revision", default=None), ContextVar("returned_revision", default=None)
    def revision():
        value = expected.get()
        if value is None:
            raise api.ValidationError(api.Issue(("revision",), "required"))
        return value
    class CheckedStore(adapter):
        async def create(self, key, value):
            result = await super().create(key, value)
            returned.set("1")
            return result
        async def get(self, key):
            row = await self.get_row(key)
            returned.set(row.revision)
            return row.value
        async def update(self, key, transform):
            row = await self.update_checked(key, transform=transform, expected_revision=revision())
            returned.set(row.revision)
            return row.value
        async def delete(self, key):
            await self.delete_checked(key, expected_revision=revision())
    config = ServiceConfig(WorkItem, Path(database), namespace="work_items", table="app_work_items",
                           type_key="example.work_item", id_field="key", resource_path="/work-items", public=True)
    async with application(config, store_type=CheckedStore) as service:
        service.app = _RevisionApp(service.app, expected, returned)
        yield service


async def _exchange(port, method, path, *, data=None, revision=None, headers=()):
    """Bounded real loopback HTTP exchange used by the synthetic acceptance."""
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    try:
        body = b"" if data is None else json.dumps(data, ensure_ascii=False, allow_nan=False).encode()
        lines = [f"{method} {path} HTTP/1.1", f"Host: 127.0.0.1:{port}", "Connection: close", f"Content-Length: {len(body)}"]
        if data is not None:
            lines.append("Content-Type: application/json")
        if revision is not None:
            lines.append(f'If-Match: "{revision}"')
        lines.extend(headers)
        writer.write(("\r\n".join(lines) + "\r\n\r\n").encode("ascii") + body)
        await writer.drain()
        raw = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 5)
        status_line, *response_headers = raw.decode("latin-1").strip().split("\r\n")
        values = dict(line.lower().split(": ", 1) for line in response_headers)
        size = int(values.get("content-length", "0"))
        if not 0 <= size <= 65536:
            raise RuntimeError("Acceptance response exceeded its bound.")
        payload = await asyncio.wait_for(reader.readexactly(size), 5)
        return int(status_line.split()[1]), values, json.loads(payload) if payload else None
    finally:
        writer.close()
        await writer.wait_closed()


async def _accept_phase(database, phase):
    from expose_api import serve
    async with reference_application(database) as service:
        async with serve(service.app, port=0) as server:
            port, checks = server.sockets[0].getsockname()[1], 0
            async def check(method, path, status, *, data=None, revision=None, etag=None, code=None):
                nonlocal checks
                actual, headers, result = await _exchange(port, method, path, data=data, revision=revision)
                if actual != status or etag is not None and headers.get("etag") != etag or code is not None and result["error"]["code"] != code:
                    raise RuntimeError(f"Reference {phase} acceptance failed: {method} expected status {status}, received {actual}.")
                checks += 1
                return result
            if phase == "write":
                await check("POST", "/work-items", 201, data={"key": "item-001", "title": "Garden 🌱"}, etag='"1"')
                await check("PATCH", "/work-items/item-001", 422, revision="1", data={"done": 1})
                await check("GET", "/work-items/item-001", 200, etag='"1"')
                await check("PATCH", "/work-items/item-001", 200, revision="1", data={"title": "Changed locally"}, etag='"2"')
                await check("PATCH", "/work-items/item-001", 409, revision="1", data={"done": True}, code="revision_conflict")
                await check("DELETE", "/work-items/item-001", 428, code="precondition_required")
                await check("POST", "/work-items", 201, data={"key": "item-002", "title": "Second"})
                page = await check("GET", "/work-items?offset=1&limit=1", 200)
                if [item["key"] for item in page] != ["item-002"]:
                    raise RuntimeError("Reference pagination returned an unexpected page.")
                await check("GET", "/work-items?offset=10001", 422)
                await check("DELETE", "/work-items/item-002", 204, revision="1")
            elif phase == "reload":
                item = await check("GET", "/work-items/item-001", 200, etag='"2"')
                if item != {"key": "item-001", "title": "Changed locally", "done": False}:
                    raise RuntimeError("Reference restart did not retain the committed value.")
                await check("PATCH", "/work-items/item-001", 422, revision="2", data={"key": "changed"})
                await check("DELETE", "/work-items/item-001", 409, revision="1", code="revision_conflict")
                await check("DELETE", "/work-items/item-001", 204, revision="2")
                await check("GET", "/work-items/item-001", 404)
                await check("POST", "/work-items", 409, data={"key": "item-001", "title": "Reused key"})
            else:
                raise ValueError("Unknown acceptance phase.")
            return {"phase": phase, "checks": checks, "passed": True}


async def accept_reference():
    """Run real HTTP in two independent processes over a dedicated temporary DB."""
    _dependencies()
    receipts = []
    code = "import asyncio,json,sys; from compose_application.reference import _accept_phase; print(json.dumps(asyncio.run(_accept_phase(sys.argv[1],sys.argv[2]))))"
    with TemporaryDirectory(prefix="work-item-acceptance-") as directory:
        for phase in ("write", "reload"):
            process = await asyncio.create_subprocess_exec(sys.executable, "-I", "-c", code, str(Path(directory) / "work-items.sqlite3"), phase,
                                                          stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            try:
                output, errors = await asyncio.wait_for(process.communicate(), 30)
                if process.returncode:
                    raise RuntimeError(f"Reference acceptance process failed during {phase}: " + errors.decode("utf-8", errors="replace")[-4000:])
                receipts.append(json.loads(output))
            finally:
                if process.returncode is None:
                    process.kill()
                    await process.communicate()
    return {"profile": "cpython-service/1", "phases": receipts, "checks": sum(item["checks"] for item in receipts), "process_restart": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="exercise a dedicated temporary database across real processes")
    server = commands.add_parser("serve", help="serve synthetic work items on loopback")
    server.add_argument("--database", required=True, type=Path)
    server.add_argument("--port", type=int, default=8000)
    arguments = parser.parse_args()
    async def run():
        if arguments.command == "check":
            print(json.dumps(await accept_reference(), sort_keys=True))
        else:
            from expose_api import serve
            async with reference_application(arguments.database) as service:
                async with serve(service.app, port=arguments.port):
                    print(f"Synthetic work items: http://127.0.0.1:{arguments.port}/work-items", flush=True)
                    await asyncio.Event().wait()
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
