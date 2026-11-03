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

HTTP_CHECKS = '''"""Bounded HTTP acceptance helpers; no user database or credentials."""

import asyncio
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory


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
        return int(status.split()[1]), fields, json.loads(payload) if payload else None
    finally:
        writer.close()
        await writer.wait_closed()


def require(condition):
    if not condition:
        raise RuntimeError("Generated reference acceptance failed.")


async def accept():
    phases = []
    code = "import asyncio,json,sys; from __PROJECT_MODULE__.checks import phase; print(json.dumps(asyncio.run(phase(sys.argv[1],sys.argv[2]))))"
    with TemporaryDirectory(prefix="reference-project-check-") as directory:
        for name in ("write", "reload"):
            process = await asyncio.create_subprocess_exec(
                sys.executable, "-I", "-W", "error::ResourceWarning", "-c", code,
                str(Path(directory) / "check.sqlite3"), name,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            try:
                output, errors = await asyncio.wait_for(process.communicate(), 30)
                if process.returncode:
                    raise RuntimeError("Generated check failed during " + name + ": " + errors.decode("utf-8", errors="replace")[-4000:])
                phases.append(json.loads(output))
            finally:
                if process.returncode is None:
                    process.kill()
                    await process.communicate()
    return {"profile": "__PROJECT_PROFILE__", "checks": sum(item["checks"] for item in phases),
            "phases": phases, "process_restart": True, "passed": True}
'''

SERVICE_PHASE = '''

async def phase(database, name):
    from .app import open_server
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
    return {"phase": name, "checks": checks, "closed": True}
'''
