"""Real-process checked editing acceptance for the optional table profile."""

import asyncio
from dataclasses import asdict, replace
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from .tabular import dependencies, tabular_application, transport


async def edit_phase(database, phase):
    from expose_api import serve
    checks = 0
    def check(value):
        nonlocal checks
        if not value:
            raise RuntimeError("Editable table acceptance failed.")
        checks += 1
    async with tabular_application(database, seed=phase == "write", editable=True) as service:
        async with serve(service.app, port=0) as server:
            client = transport(f"http://127.0.0.1:{server.sockets[0].getsockname()[1]}")
            async def request(path, data):
                return await asyncio.to_thread(client.request, "POST", "/work-items/_table/" + path, data=data)
            def edit(**values):
                return dict(table_id="work_items", key="item-055", column_id="title", expected_revision="1", value="Edited durable row", **values)
            async def query(**values):
                data = dict(generation=1, columns=["title", "done", "rank", "score", "key"], order=[], search=None, cursor=None, limit=50)
                data.update(values)
                return await request("query", data)
            if phase == "write":
                original = await service.store.get_row("item-055")
                visible = await query(order=[dict(column_id="title", descending=True)], search=dict(fields=["title"], term="%_"))
                check(visible.status == 200 and [r["key"] for r in visible.data["rows"]] == ["item-055"])
                saved = await request("cell", edit())
                check(saved.status == 200 and saved.data["row"]["revision"] == "2" and saved.data["row"]["values"]["title"] == "Edited durable row")
                current = await service.store.get_row("item-055")
                check(asdict(current.value) == {**asdict(original.value), "title": "Edited durable row"})
                all_rows = await query(limit=1000)
                check(next(r for r in all_rows.data["rows"] if r["key"] == "item-055")["revision"] == "2")
                stale = await request("cell", {**edit(), "column_id": "done", "value": True})
                check(stale.status == 409 and stale.data["error"]["code"] == "revision_conflict")
                for patch, status in [({"value": ""}, 422), ({"column_id": "key", "value": "other"}, 422),
                        ({"column_id": "owner", "value": "bob"}, 422), ({"value": "policy-denied"}, 403),
                        ({"column_id": "rank", "value": True}, 422), ({"column_id": "rank", "value": -1}, 422)]:
                    response = await request("cell", {**edit(), "expected_revision": "2", **patch})
                    check(response.status == status)
                    check(await service.store.get_row("item-055") == current)
                denied = await request("cell", {**edit(), "key": "item-000", "expected_revision": "9"})
                check(denied.status == 404)
                await service.store.update_checked("item-055", expected_revision="2", transform=lambda value: replace(value, owner="bob"))
                changed_policy = await request("cell", {**edit(), "expected_revision": "2"})
                check(changed_policy.status == 404)
                await service.store.update_checked("item-055", expected_revision="3", transform=lambda value: replace(value, owner="alice"))
                # Simultaneous different-cell writes use one row revision.
                results = await asyncio.gather(request("cell", {**edit(), "key": "item-056", "value": "Concurrent winner"}),
                    request("cell", {**edit(), "key": "item-056", "column_id": "done", "value": False}))
                check(sorted(r.status for r in results) == [200, 409])
                independent = await request("cell", {**edit(), "key": "item-057", "column_id": "rank", "value": None})
                check(independent.status == 200)
            elif phase == "reopen":
                row = await service.store.get_row("item-055")
                check((row.value.title, row.value.owner, row.revision) == ("Edited durable row", "alice", "4"))
                page = await query(filters=[dict(column_id="key", operator="eq", value="item-055")])
                check(page.status == 200 and page.data["rows"][0]["revision"] == "4")
                check((await service.store.get_row("item-056")).revision == "2")
                check((await service.store.get_row("item-057")).value.rank is None)
            else:
                raise ValueError("Unknown edit acceptance phase.")
    check(not service.store._backend._thread.is_alive())
    return dict(phase=phase, checks=checks, passed=True, closed=True)


async def accept_edits():
    dependencies()
    receipts = []
    code = "import asyncio,json,sys; from compose_application.tabular_edits import edit_phase; print(json.dumps(asyncio.run(edit_phase(sys.argv[1],sys.argv[2]))))"
    with TemporaryDirectory(prefix="editable-tabular-") as directory:
        for phase in ("write", "reopen"):
            process = await asyncio.create_subprocess_exec(sys.executable, "-I", "-c", code, str(Path(directory) / "items.sqlite"), phase,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            try:
                output, errors = await asyncio.wait_for(process.communicate(), 30)
                if process.returncode:
                    raise RuntimeError("Editable acceptance process failed: " + errors.decode(errors="replace")[-2000:])
                receipts.append(json.loads(output))
            finally:
                if process.returncode is None:
                    process.kill()
                    await process.communicate()
    return dict(profile="cpython-tabular/1", checks=sum(r["checks"] for r in receipts), phases=receipts,
                process_restart=True, editable=True, passed=True)
