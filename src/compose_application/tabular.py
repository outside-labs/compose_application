"""Optional persisted read-only/editable tables over synthetic loopback records."""

import argparse
import asyncio
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass, field, replace
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import threading

from .service import ProfileError, Service


@dataclass(frozen=True)
class TableItem:
    key: str
    title: str
    owner: str = field(metadata={"expose_api": {"write_only": True}})
    done: bool = False
    rank: int | None = None
    score: float = 0.0

    def __post_init__(self):
        if not self.title.strip() or self.rank is not None and self.rank < 0:
            raise ValueError("A nonblank title and nonnegative nullable rank are required.")


def dependencies():
    try:
        import expose_api as api
        from expose_api.backpack import BackpackStore
        from spatial_ui import App, HTTPTableClient, TableBrowser
        from headless_spreadsheets import TableSource
        if not callable(getattr(api.App, "tabular", None)) or not callable(getattr(BackpackStore, "tabular_page", None)):
            raise ImportError
    except ImportError:
        raise ProfileError("Install compose-application[tabular] with its qualified source profile.") from None
    return api, BackpackStore


@asynccontextmanager
async def tabular_application(database, *, seed=True, editable=False):
    """Own a local worker and an explicitly protected synthetic table API."""
    api, adapter = dependencies()
    if str(database) == ":memory:" or type(seed) is not bool or type(editable) is not bool:
        raise ValueError("Select a persistent database and explicit seed behavior.")
    store = await adapter.open(TableItem, Path(database), namespace="tabular", table="app_tabular_items", type_key="reference.table_item", id_field="key")
    service = Service(Path(database), store, None, None)
    try:
        if seed:
            for index in range(120):
                key = f"item-{index:03}"
                try:
                    await store.get_row(key)
                except api.NotFoundError:
                    title = "Café %_ Needle" if index == 55 else f"Item {index:03}"
                    value = TableItem(key, title, "bob" if index < 40 else "alice", index % 2 == 0, None if index % 7 == 0 else index % 5, index / 10)
                    try:
                        await store.create(key, value)
                    except api.ConflictError:
                        # Another explicitly selected local reference can seed concurrently.
                        await store.get_row(key)
        def verify(token):
            return api.Principal(token[7:]) if token in {"reader-alice", "reader-bob"} else None
        app = api.App(authenticate=api.BearerAuth(verify), auth_challenge="Bearer", max_body_size=65536)
        resource = app.include(TableItem, store=store, id_field="key", path="/work-items", operations=("list", "get", "update") if editable else ("list", "get"),
            authorize=lambda request: request.principal is not None,
            record_policy=lambda principal, operation, value: value.owner == principal.subject and value.title != "policy-denied")
        app.tabular(resource, table_id="work_items", schema_version="1", application_scope="tabular-reference-v1", columns=[
            api.TableColumn("title", "title", "Title", sortable=True, searchable=True, writable=editable),
            api.TableColumn("done", "done", "Done", sortable=True, writable=editable),
            api.TableColumn("rank", "rank", "Rank", sortable=True, writable=editable),
            api.TableColumn("score", "score", "Score", sortable=True, writable=editable),
            *([api.TableColumn("key", "key", "Key", sortable=True)] if editable else [])])
        service.resource, service.app = resource, app
        yield service
    finally:
        await service.aclose()


def transport(origin, principal="alice"):
    from spatial_ui.rest import HTTPTransport
    if principal not in {"alice", "bob"}:
        raise ValueError("Select a synthetic reference principal.")
    return HTTPTransport(origin, headers=(("Authorization", f"Bearer reader-{principal}"),), max_response_body=4194304)


def make_ui(client, *, editable=False):
    from spatial_ui import App, TableBrowser
    from .ui import STYLESHEET
    return App(lambda: TableBrowser(client, title="Persistent work items", page_size=50, editable=editable),
               title="Editable work items" if editable else "Read-only work items", stylesheet=STYLESHEET)


async def fingerprint(store):
    values = await store.list(limit=1000)
    rows = [await store.get_row(value.key) for value in values]
    raw = [[row.key, row.revision, asdict(row.value)] for row in rows]
    return hashlib.sha256(json.dumps(raw, sort_keys=True, ensure_ascii=True).encode()).hexdigest()


async def accept_phase(database, phase, continuation=None):
    from expose_api import serve
    from spatial_ui import HTTPTableClient
    api, _ = dependencies()
    checks = 0
    def check(value):
        nonlocal checks
        if not value:
            raise RuntimeError("Tabular reference acceptance failed.")
        checks += 1
    async with tabular_application(database, seed=phase == "seed") as service:
        async with serve(service.app, port=0) as server:
            origin = f"http://127.0.0.1:{server.sockets[0].getsockname()[1]}"
            alice, bob = transport(origin), transport(origin, "bob")
            client = await asyncio.to_thread(HTTPTableClient.open, alice, "/work-items")
            before = await fingerprint(service.store)
            def descriptor(**values):
                return dict(generation=1, columns=[c.id for c in client.columns], order=[], search=None, cursor=None, limit=50, **values)
            def query(**values):
                data = descriptor()
                data.update(values)
                return alice.request("POST", "/work-items/_table/query", data=data)
            if phase == "seed":
                first = await asyncio.to_thread(query)
                check(first.status == 200 and len(first.data["rows"]) == 50 and first.data["rows"][0]["key"] == "item-040")
                continuation = first.data["next_cursor"]
                check(type(continuation) is str and all(row["revision"] == "1" for row in first.data["rows"]))
                second = await asyncio.to_thread(query, cursor=continuation)
                check(second.status == 200 and len(second.data["rows"]) == 30 and second.data["next_cursor"] is None)
                literal = await asyncio.to_thread(query, search={"fields": ["title"], "term": "%_"})
                check(literal.status == 200 and [row["key"] for row in literal.data["rows"]] == ["item-055"])
                sorted_page = await asyncio.to_thread(query, order=[{"column_id": "rank", "descending": True}])
                check(sorted_page.status == 200 and sorted_page.data["rows"][0]["key"] == "item-044")
                projected = await asyncio.to_thread(query, columns=["score", "title"])
                check(projected.status == 200 and set(projected.data["rows"][0]["values"]) == {"score", "title"})
                hidden = await asyncio.to_thread(query, search={"fields": ["owner"], "term": "alice"})
                check(hidden.status == 400 and "alice" not in json.dumps(hidden.data))
                changed = await asyncio.to_thread(query, cursor=continuation, search={"fields": ["title"], "term": "Item"})
                check(changed.status == 400 and changed.data["error"]["code"] == "invalid_cursor")
                other = await asyncio.to_thread(bob.request, "POST", "/work-items/_table/query", data=descriptor())
                check(other.status == 200 and len(other.data["rows"]) == 40 and all(row["key"] < "item-040" for row in other.data["rows"]))
                replay = await asyncio.to_thread(bob.request, "POST", "/work-items/_table/query", data={**descriptor(), "cursor": continuation})
                check(replay.status == 400 and replay.data["error"]["code"] == "invalid_cursor")
                check(await fingerprint(service.store) == before)
                await service.store.update_checked("item-095", expected_revision="1", transform=lambda value: replace(value, title="Changed between pages"))
                moved = await asyncio.to_thread(query, cursor=continuation)
                check(next(row for row in moved.data["rows"] if row["key"] == "item-095")["revision"] == "2")
            elif phase == "reopen":
                second = await asyncio.to_thread(query, cursor=continuation)
                row = next(row for row in second.data["rows"] if row["key"] == "item-095")
                check(second.status == 200 and row["revision"] == "2" and row["values"]["title"] == "Changed between pages")
                check(await fingerprint(service.store) == before)
                denied = await asyncio.to_thread(alice.request, "GET", "/work-items/item-000")
                check(denied.status == 404)
                writes = await asyncio.to_thread(alice.request, "POST", "/work-items/_table/cell", data={})
                check(writes.status == 404)
            else:
                raise ValueError("Unknown table acceptance phase.")
    check(not service.store._backend._thread.is_alive())
    return dict(phase=phase, checks=checks, passed=True, continuation=continuation)


async def accept_tabular():
    dependencies()
    receipts, continuation = [], None
    code = "import asyncio,json,sys; from compose_application.tabular import accept_phase; print(json.dumps(asyncio.run(accept_phase(sys.argv[1],sys.argv[2],None if sys.argv[3]=='-' else sys.argv[3]))))"
    with TemporaryDirectory(prefix="tabular-reference-") as directory:
        for phase in ("seed", "reopen"):
            process = await asyncio.create_subprocess_exec(sys.executable, "-I", "-c", code,
                str(Path(directory) / "table.sqlite"), phase, continuation or "-", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            try:
                output, errors = await asyncio.wait_for(process.communicate(), 30)
                if process.returncode:
                    raise RuntimeError("Tabular acceptance process failed: " + errors.decode(errors="replace")[-2000:])
                receipt = json.loads(output)
                continuation = receipt.pop("continuation")
                receipts.append(receipt)
            finally:
                if process.returncode is None:
                    process.kill()
                    await process.communicate()
    return dict(profile="cpython-tabular/1", checks=sum(receipt["checks"] for receipt in receipts), phases=receipts, process_restart=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check")
    commands.add_parser("check-edits")
    serve = commands.add_parser("serve")
    serve.add_argument("--database", type=Path, required=True)
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--principal", choices=("alice", "bob"), default="alice")
    serve.add_argument("--editable", action="store_true")
    args = parser.parse_args()
    async def run():
        if args.command == "check":
            print(json.dumps(await accept_tabular(), sort_keys=True))
            return
        if args.command == "check-edits":
            from .tabular_edits import accept_edits
            print(json.dumps(await accept_edits(), sort_keys=True))
            return
        dependencies()
        from expose_api import serve
        from spatial_ui import HTTPTableClient
        async with tabular_application(args.database, editable=args.editable) as service:
            async with serve(service.app, port=0) as server:
                origin = f"http://127.0.0.1:{server.sockets[0].getsockname()[1]}"
                client = await asyncio.to_thread(HTTPTableClient.open, transport(origin, args.principal), "/work-items", key_column="key" if args.editable else None)
                with make_ui(client, editable=args.editable).make_server(args.port) as ui:
                    thread = threading.Thread(target=ui.serve_forever, kwargs={"poll_interval": .02}, daemon=True)
                    thread.start()
                    try:
                        print(f"Table reference: http://127.0.0.1:{ui.server_port}", flush=True)
                        await asyncio.Event().wait()
                    finally:
                        await asyncio.to_thread(ui.shutdown)
                        thread.join(5)
                        await asyncio.to_thread(ui.server_close)
        print("Table reference closed.", flush=True)
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
