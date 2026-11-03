"""Optional loopback typed UI over the persistent checked work-item reference."""

import argparse
import asyncio
from importlib import metadata
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import threading

from .service import ProfileError

STYLESHEET = """* { box-sizing: border-box; }
body { margin: 0; color: #15243b; background: #f4f6fa; font: 16px/1.5 system-ui, sans-serif; }
main { max-width: 1100px; margin: auto; padding: 1.25rem; }
.workspace { display: grid; gap: 1.25rem; }
section { background: white; border: 1px solid #d5deea; border-radius: .75rem; padding: 1rem; min-width: 0; }
form { display: grid; gap: .6rem; }
form > div { display: grid; gap: .25rem; }
input, select, textarea, button { font: inherit; max-width: 100%; }
input[type=text], textarea, select { width: 100%; padding: .5rem; border: 1px solid #718096; border-radius: .3rem; }
button { padding: .6rem 1rem; background: #193f7b; color: white; border: 0; border-radius: .3rem; cursor: pointer; }
:focus-visible { outline: 3px solid #bc5e00; outline-offset: 3px; }
[aria-invalid=true] { outline: 2px solid #a32020; }
li, dd { overflow-wrap: anywhere; }
dd { margin-bottom: .5rem; }
@media (min-width: 760px) { .workspace { grid-template-columns: 2fr 1fr; align-items: start; } }
@media (prefers-reduced-motion: reduce) { * { scroll-behavior: auto; } }
"""


def _ui_dependencies():
    try:
        if metadata.version("spatial-ui") != "0.1.0":
            raise ProfileError("The UI package version does not match the qualified profile.")
        from spatial_ui import App, Component, Field, FormSchema, Session, html
        from spatial_ui.resource_form import ResourceForm
        from spatial_ui.rest import HTTPTransport, ResourceClient, ResourceSpec, TransportError
    except (ImportError, metadata.PackageNotFoundError):
        raise ProfileError("Install compose-application[ui] with its qualified development revisions.") from None
    return App, Component, Field, FormSchema, Session, html, ResourceForm, HTTPTransport, ResourceClient, ResourceSpec, TransportError


def resource_client(origin):
    """Build the explicit scalar work-item wire profile without ambient credentials."""
    _, _, Field, FormSchema, _, _, _, HTTPTransport, ResourceClient, ResourceSpec, _ = _ui_dependencies()
    schema = FormSchema((Field("key"), Field("title"), Field("done", "checkbox", False, False)))
    return ResourceClient(HTTPTransport(origin), ResourceSpec("/work-items", schema, ("key", "title", "done")))


def make_ui(origin, *, client=None, live=None):
    """Return a fresh-session loopback App; the caller owns the API's lifecycle."""
    App, Component, _, _, _, html, ResourceForm, _, _, _, TransportError = _ui_dependencies()
    client = resource_client(origin) if client is None else client

    class Workspace(Component):
        def __init__(self):
            self.editor = ResourceForm(client, title="Edit a work item", **({"live": live} if live is not None else {}))
            self.items, self.message = (), ""
            self.refresh()

        def refresh(self):
            try:
                self.items = client.list(limit=50)
                self.message = "List refreshed."
            except TransportError:
                self.message = "List unavailable. Refresh to try again."

        def render(self):
            rows = [html(t'<li><strong>{item["key"]}</strong>: {item["title"]} — {"Done" if item["done"] else "Open"}</li>') for item in self.items]
            return html(t'''<main><h1>Work items</h1>
              <p>Save a record, then load it in another browser to edit the same data.</p>
              <div class="workspace">{self.editor}<section key="list"><h2>Saved items</h2>
                <button type="button" on_click={self.refresh}>Refresh list</button>
                <p role="status">{self.message}</p><ul>{rows}</ul>
              </section></div></main>''')
    return App(Workspace, title="Work items", stylesheet=STYLESHEET)


async def _accept_ui_phase(database, phase):
    from .reference import reference_application
    from expose_api import serve
    _, _, _, _, Session, _, ResourceForm, *_ = _ui_dependencies()
    async with reference_application(database) as service:
        async with serve(service.app, port=0) as server:
            client = resource_client(f"http://127.0.0.1:{server.sockets[0].getsockname()[1]}")
            checks = 0
            def check(value):
                nonlocal checks
                if not value:
                    raise RuntimeError(f"Typed UI acceptance failed during {phase}.")
                checks += 1
            async def submit(session, **values):
                snapshot = session.render()
                fields = {**session.component.binding.draft, "operation": "save", **values}
                return await asyncio.to_thread(session.dispatch, snapshot.event_ids[0], snapshot.version,
                                               {"kind": "submit", "fields": fields})
            first, second = Session(ResourceForm(client)), Session(ResourceForm(client))
            if phase == "write":
                invalid = await submit(first, key="item-001", title="")
                check(invalid.form_result.status == "invalid" and invalid.form_result.as_dict()["focus"] == "title")
                check((await submit(first, key="item-001", title="Garden 🌱")).form_result.status == "saved")
                check((await submit(second, key="item-001", operation="load")).form_result.status == "loaded")
                check((await submit(first, title="Changed remotely")).form_result.status == "saved")
                check((await submit(second, title="Local merge")).form_result.status == "conflict")
                check(second.component.binding.draft["title"] == "Local merge")
                check((await submit(second, operation="load")).form_result.status == "loaded")
                check(second.component.binding.draft["title"] == "Local merge" and second.component.binding.committed["title"] == "Changed remotely")
                check((await submit(second)).form_result.status == "saved")
                check((await submit(second, title="x" * 201)).form_result.status == "invalid")
                check((await asyncio.to_thread(client.list))[0]["title"] == "Local merge")
            elif phase == "reload":
                check((await submit(first, key="item-001", operation="load")).form_result.status == "loaded")
                check(first.component.binding.committed["title"] == "Local merge" and first.component.binding.revision == "3")
                check((await submit(first, operation="delete")).form_result.status == "deleted")
                check(await asyncio.to_thread(client.list) == ())
            else:
                raise ValueError("Select a known acceptance phase.")
            return {"phase": phase, "checks": checks, "passed": True}


async def accept_ui():
    """Qualify public forms/REST in two processes over a dedicated temporary DB."""
    _ui_dependencies()
    receipts = []
    code = "import asyncio,json,sys; from compose_application.ui import _accept_ui_phase; print(json.dumps(asyncio.run(_accept_ui_phase(sys.argv[1],sys.argv[2]))))"
    with TemporaryDirectory(prefix="typed-ui-acceptance-") as directory:
        for phase in ("write", "reload"):
            process = await asyncio.create_subprocess_exec(sys.executable, "-I", "-c", code,
                str(Path(directory) / "items.sqlite3"), phase, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            try:
                output, errors = await asyncio.wait_for(process.communicate(), 30)
                if process.returncode:
                    raise RuntimeError(f"UI acceptance process failed during {phase}: " + errors.decode("utf-8", errors="replace")[-4000:])
                receipts.append(json.loads(output))
            finally:
                if process.returncode is None:
                    process.kill()
                    await process.communicate()
    return {"profile": "cpython-ui/1", "checks": sum(item["checks"] for item in receipts),
            "phases": receipts, "process_restart": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="verify typed form/REST persistence across processes")
    server = commands.add_parser("serve", help="run the local persistent work-item UI")
    server.add_argument("--database", type=Path, required=True)
    server.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    async def run():
        if args.command == "check":
            print(json.dumps(await accept_ui(), sort_keys=True))
            return
        from .reference import reference_application
        from expose_api import serve
        async with reference_application(args.database) as service:
            async with serve(service.app, port=0) as api:
                origin = f"http://127.0.0.1:{api.sockets[0].getsockname()[1]}"
                with make_ui(origin).make_server(args.port) as ui:
                    thread = threading.Thread(target=ui.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
                    thread.start()
                    try:
                        print(f"Work items: http://127.0.0.1:{ui.server_port}", flush=True)
                        await asyncio.Event().wait()
                    finally:
                        await asyncio.to_thread(ui.shutdown)
                        thread.join(5)
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
