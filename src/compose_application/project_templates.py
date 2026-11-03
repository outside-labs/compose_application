"""Source templates for finite, application-owned reference workflows."""

SERVICE_APP = '''"""Application-owned assembly of the accepted synthetic work-item service."""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from compose_application.reference import reference_application


@asynccontextmanager
async def open_application(database):
    async with reference_application(Path(database)) as application:
        yield application


@asynccontextmanager
async def open_server(database, *, port=0):
    from expose_api import serve
    async with open_application(database) as application:
        async with serve(application.app, port=port) as server:
            yield server


async def serve(database, *, port=8000):
    async with open_server(database, port=port) as server:
        port = server.sockets[0].getsockname()[1]
        print(f"Work items: http://127.0.0.1:{port}/work-items", flush=True)
        await asyncio.Event().wait()
'''

COMMAND = '''"""Run the selected reference or its isolated temporary-data acceptance."""

import argparse
import asyncio
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="check temporary data across independent processes")
    server = commands.add_parser("serve", help="start the loopback development reference")
    server.add_argument("--database", required=True, type=Path)
    server.add_argument("--port", type=int, default=8000)
    arguments = parser.parse_args()
    if arguments.command == "check":
        from .checks import accept
        print(json.dumps(asyncio.run(accept()), sort_keys=True))
    else:
        from .app import serve
        try:
            asyncio.run(serve(arguments.database, port=arguments.port))
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
'''

CHECK_RUNNER = '''"""Bounded acceptance using temporary data in independent processes."""

import asyncio
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory


def require(condition):
    if not condition:
        raise RuntimeError("Generated reference acceptance failed.")


async def accept():
    phases = []
    code = "import asyncio,faulthandler,json,sys; from __PROJECT_MODULE__.checks import phase; faulthandler.dump_traceback_later(15); print(json.dumps(asyncio.run(phase(sys.argv[1],sys.argv[2])))); faulthandler.cancel_dump_traceback_later()"
    with TemporaryDirectory(prefix="reference-project-check-") as directory:
        for name in ("write", "reload"):
            process = await asyncio.create_subprocess_exec(
                sys.executable, "-I", "-W", "error::ResourceWarning", "-c", code,
                str(Path(directory) / "check.sqlite3"), name,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            communication = asyncio.create_task(process.communicate())
            try:
                try:
                    output, errors = await asyncio.wait_for(asyncio.shield(communication), 30)
                except TimeoutError:
                    if process.returncode is None:
                        process.kill()
                    _, errors = await communication
                    raise RuntimeError("Generated check timed out during " + name + ": " + errors.decode("utf-8", errors="replace")[-8000:]) from None
                if process.returncode:
                    raise RuntimeError("Generated check failed during " + name + ": " + errors.decode("utf-8", errors="replace")[-4000:])
                phases.append(json.loads(output))
            finally:
                if process.returncode is None:
                    process.kill()
                await communication
    return {"profile": "__PROJECT_PROFILE__", "checks": sum(item["checks"] for item in phases),
            "phases": phases, "process_restart": True, "passed": True}
'''

HTTP_CHECKS = '''

async def request(port, method, path, *, data=None, revision=None):
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    try:
        body = b"" if data is None else json.dumps(data, allow_nan=False).encode()
        headers = [f"{method} {path} HTTP/1.1", f"Host: 127.0.0.1:{port}",
                   "Connection: close", f"Content-Length: {len(body)}"]
        if data is not None:
            headers.append("Content-Type: application/json")
        if revision is not None:
            headers.append(f'If-Match: "{revision}"')
        writer.write(("\\r\\n".join(headers) + "\\r\\n\\r\\n").encode("ascii") + body)
        await writer.drain()
        raw = await asyncio.wait_for(reader.readuntil(b"\\r\\n\\r\\n"), 5)
        status, *fields = raw.decode("latin-1").strip().split("\\r\\n")
        fields = dict(field.lower().split(": ", 1) for field in fields)
        size = int(fields.get("content-length", "0"))
        if not 0 <= size <= 65536:
            raise RuntimeError("Acceptance response exceeded its bound.")
        payload = await asyncio.wait_for(reader.readexactly(size), 5)
        value = json.loads(payload) if payload and "application/json" in fields.get("content-type", "") else payload.decode("utf-8")
        return int(status.split()[1]), fields, value
    finally:
        writer.close()
        await writer.wait_closed()
'''

SERVICE_PHASE = '''

async def phase(database, name):
    import threading
    from .app import open_server
    threads = {thread.ident for thread in threading.enumerate()}
    async with open_server(database) as server:
        port = server.sockets[0].getsockname()[1]
        checks = 0
        async def check(method, path, expected, **options):
            nonlocal checks
            status, headers, value = await request(port, method, path, **options)
            require(status == expected)
            checks += 1
            return headers, value
        if name == "write":
            headers, value = await check("POST", "/work-items", 201, data={"key": "garden", "title": "Garden 🌱"})
            require(headers.get("etag") == '\"1\"' and value["done"] is False)
            await check("PATCH", "/work-items/garden", 422, revision="1", data={"done": 1})
            headers, _ = await check("PATCH", "/work-items/garden", 200, revision="1", data={"title": "Water garden"})
            require(headers.get("etag") == '\"2\"')
            await check("PATCH", "/work-items/garden", 409, revision="1", data={"done": True})
            await check("DELETE", "/work-items/garden", 428)
        elif name == "reload":
            headers, value = await check("GET", "/work-items/garden", 200)
            require(headers.get("etag") == '\"2\"' and value["title"] == "Water garden" and value["done"] is False)
            await check("DELETE", "/work-items/garden", 409, revision="1")
            await check("DELETE", "/work-items/garden", 204, revision="2")
            await check("GET", "/work-items/garden", 404)
        else:
            raise ValueError("Unknown acceptance phase.")
    require({thread.ident for thread in threading.enumerate()} == threads)
    return {"phase": name, "checks": checks, "closed": True}
'''

UI_APP = '''"""Application-owned loopback UI and persistent checked REST lifecycle."""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
import threading

from compose_application.reference import reference_application
from compose_application.ui import make_ui, resource_client


@asynccontextmanager
async def open_server(database, *, port=0):
    from expose_api import serve
    async with reference_application(Path(database)) as application:
        async with serve(application.app, port=0) as api:
            origin = f"http://127.0.0.1:{api.sockets[0].getsockname()[1]}"
            with make_ui(origin).make_server(port) as ui:
                thread = threading.Thread(target=ui.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
                thread.start()
                try:
                    yield ui, resource_client(origin)
                finally:
                    await asyncio.to_thread(ui.shutdown)
                    await asyncio.to_thread(thread.join, 5)
                    if thread.is_alive():
                        raise RuntimeError("UI server did not stop within its shutdown bound.")


async def serve(database, *, port=8000):
    async with open_server(database, port=port) as (ui, _):
        print(f"Work items: http://127.0.0.1:{ui.server_port}", flush=True)
        await asyncio.Event().wait()
'''

UI_PHASE = '''

async def phase(database, name):
    import threading
    from spatial_ui import Session
    from spatial_ui.resource_form import ResourceForm
    from .app import open_server
    threads = {thread.ident for thread in threading.enumerate()}
    checks = 0
    def check(value):
        nonlocal checks
        require(value)
        checks += 1
    async with open_server(database) as (ui, client):
        status, _, page = await request(ui.server_port, "GET", "/")
        check(status == 200 and "Work items" in page)
        first, second = Session(ResourceForm(client)), Session(ResourceForm(client))
        async def submit(session, **values):
            snapshot = session.render()
            fields = {**session.component.binding.draft, "operation": "save", **values}
            result = await asyncio.to_thread(session.dispatch, snapshot.event_ids[0], snapshot.version,
                                            {"kind": "submit", "fields": fields})
            return result.form_result.status
        if name == "write":
            check(await submit(first, key="garden", title="") == "invalid")
            check(await submit(first, key="garden", title="Garden 🌱") == "saved")
            check(await submit(second, key="garden", operation="load") == "loaded")
            check(await submit(first, title="Water garden") == "saved")
            check(await submit(second, title="Local merge") == "conflict")
            check(second.component.binding.draft["title"] == "Local merge")
            check(await submit(second, operation="load") == "loaded")
            check(second.component.binding.draft["title"] == "Local merge" and second.component.binding.committed["title"] == "Water garden")
            check(await submit(second) == "saved")
        elif name == "reload":
            check(await submit(first, key="garden", operation="load") == "loaded")
            check(first.component.binding.committed["title"] == "Local merge" and first.component.binding.revision == "3")
            check(await submit(first, operation="delete") == "deleted")
            check(await asyncio.to_thread(client.list) == ())
        else:
            raise ValueError("Unknown acceptance phase.")
    # The public form client uses asyncio's default executor; its caller owns
    # that executor until asyncio.run exits. Native UI/storage workers must close.
    remaining = {thread.ident for thread in threading.enumerate()
                 if not thread.name.startswith("asyncio")}
    require(remaining <= threads)
    return {"phase": name, "checks": checks, "closed": True}
'''

LIVE_APP = '''"""Application-owned protected live factory; the caller supplies its ASGI host."""

from pathlib import Path
from compose_application.live import LiveApplication, LiveConfig


def create_application(*, database, origin, verify, credentials):
    """Construct without I/O; the caller owns credentials, exact origin and lifespan."""
    return LiveApplication(LiveConfig(database=Path(database), origin=origin,
                                     verify=verify, credentials=credentials))
'''

LIVE_COMMAND = '''"""Check the protected live factory with disposable data and runtime-only identities."""

import argparse
import asyncio
import json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check",))
    parser.parse_args()
    from .checks import accept
    print(json.dumps(asyncio.run(accept()), sort_keys=True))


if __name__ == "__main__":
    main()
'''

LIVE_PHASE = '''

async def request(app, method="GET", path="/work-items", *, token=None, data=None, revision=None):
    body = b"" if data is None else json.dumps(data, allow_nan=False).encode()
    headers = [(b"host", b"reference.example")]
    if token is not None:
        headers.append((b"authorization", ("Bearer " + token).encode()))
    if data is not None:
        headers.append((b"content-type", b"application/json"))
    if revision is not None:
        headers.append((b"if-match", ('"' + revision + '"').encode()))
    incoming, outgoing = asyncio.Queue(), []
    await incoming.put({"type": "http.request", "body": body})
    async def send(event):
        outgoing.append(event)
    await asyncio.wait_for(app({"type": "http", "method": method, "path": path,
        "root_path": "", "query_string": b"", "headers": headers}, incoming.get, send), 5)
    return outgoing[0]["status"], dict(outgoing[0]["headers"]), b"".join(event.get("body", b"") for event in outgoing[1:])


async def phase(database, name):
    import secrets
    import threading
    from expose_api import Principal
    from compose_application.live import Credential
    from .app import create_application
    alice = Principal("check-alice", scopes=frozenset({"work-items"}))
    bob = Principal("check-bob", scopes=frozenset({"work-items"}))
    first, second = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
    identities = {first: alice, second: bob}
    threads = {thread.ident for thread in threading.enumerate()}
    app = create_application(database=database, origin="https://reference.example", verify=identities.get,
        credentials=(Credential(alice, first), Credential(bob, second)))
    checks = 0
    async def check(method, path, expected, **options):
        nonlocal checks
        result = await request(app, method, path, **options)
        require(result[0] == expected)
        checks += 1
        return result
    async with app:
        await check("GET", "/work-items", 401)
        if name == "write":
            created = await check("POST", "/work-items", 201, token=first,
                data={"key": "garden", "title": "Garden 🌱", "owner": alice.subject})
            require(created[1].get(b"etag") == b'"1"' and "owner" not in json.loads(created[2]))
            await check("GET", "/work-items/garden", 404, token=second)
            await check("PATCH", "/work-items/garden", 404, token=second, revision="9", data={"done": True})
            await check("PATCH", "/work-items/garden", 422, token=first, revision="1", data={"done": 1})
            incoming, outgoing = asyncio.Queue(), asyncio.Queue()
            scope = {"type": "websocket", "path": "/work-items/garden", "root_path": "", "query_string": b"",
                "subprotocols": ["expose-api.events.v1"], "scheme": "wss", "headers": [
                    (b"host", b"reference.example"), (b"origin", b"https://reference.example"),
                    (b"cookie", ("work_identity=" + first).encode())]}
            socket = asyncio.create_task(app(scope, incoming.get, outgoing.put))
            try:
                await incoming.put({"type": "websocket.connect"})
                require((await asyncio.wait_for(outgoing.get(), 2))["type"] == "websocket.accept")
                await incoming.put({"type": "websocket.receive", "text": '{"v":1,"type":"subscribe","cursor":null}'})
                snapshot = json.loads((await asyncio.wait_for(outgoing.get(), 2))["text"])
                require(snapshot["value"] == {"key": "garden", "title": "Garden 🌱", "done": False})
                checks += 1
                updated = await check("PATCH", "/work-items/garden", 200, token=first, revision="1", data={"done": True})
                require(updated[1].get(b"etag") == b'"2"')
                snapshot = json.loads((await asyncio.wait_for(outgoing.get(), 2))["text"])
                require(snapshot["value"]["done"] is True and "owner" not in snapshot["value"])
                checks += 1
            finally:
                await incoming.put({"type": "websocket.disconnect", "code": 1000})
                try:
                    await asyncio.wait_for(socket, 5)
                finally:
                    if not socket.done():
                        socket.cancel()
                        await asyncio.gather(socket, return_exceptions=True)
            await check("PATCH", "/work-items/garden", 409, token=first, revision="1", data={"title": "Stale"})
            identities.pop(first)
            await check("GET", "/work-items/garden", 401, token=first)
        elif name == "reload":
            result = await check("GET", "/work-items/garden", 200, token=first)
            require(result[1].get(b"etag") == b'"2"' and json.loads(result[2])["done"] is True)
            await check("DELETE", "/work-items/garden", 404, token=second, revision="9")
            await check("DELETE", "/work-items/garden", 409, token=first, revision="1")
            await check("DELETE", "/work-items/garden", 204, token=first, revision="2")
        else:
            raise ValueError("Unknown acceptance phase.")
    await app.aclose()
    require({thread.ident for thread in threading.enumerate()} == threads)
    return {"phase": name, "checks": checks, "closed": True}
'''
