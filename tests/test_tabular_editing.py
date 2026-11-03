import asyncio
from dataclasses import replace
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from compose_application import ProfileError
from compose_application.tabular import dependencies, tabular_application

try:
    dependencies()
    from headless_spreadsheets.backpack import BackpackSource
    AVAILABLE = True
except (ProfileError, ImportError):
    AVAILABLE = False


@unittest.skipUnless(AVAILABLE, "optional editable tabular profile is not installed")
class EditableReferenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_http_edits_and_real_process_restart(self):
        from compose_application.tabular_edits import accept_edits
        receipt = await accept_edits()
        self.assertTrue(receipt["passed"])
        self.assertTrue(receipt["process_restart"])
        self.assertEqual([r["phase"] for r in receipt["phases"]], ["write", "reopen"])
        self.assertEqual(receipt["checks"], 27)

    async def test_independent_headless_consumer_and_http_use_same_registered_rows(self):
        from compose_application.headless_tabular import accept_headless, headless_application
        self.assertEqual(accept_headless()["checks"], 7)
        with TemporaryDirectory() as directory:
            path = Path(directory) / "shared.sqlite"
            async with tabular_application(path, editable=True) as service:
                before = await service.store.get_row("item-055")
                # This trusted in-process consumer has independent connection ownership.
                with headless_application(path) as (source, _):
                    changed = source.edit(before.key, "title", "Same durable row", expected_revision=before.revision)
                after = await service.store.get_row(before.key)
                self.assertEqual(after.revision, changed.revision)
                self.assertEqual(after.value, replace(before.value, title="Same durable row"))

    async def test_canceled_committed_http_response_fresh_read_and_cleanup(self):
        with TemporaryDirectory() as directory:
            async with tabular_application(Path(directory) / "cancel.sqlite", editable=True) as service:
                profile = service.app._tables["/work-items"]
                committed = asyncio.Event()
                original = profile.edit
                async def delayed(data, principal):
                    result = await original(data, principal)
                    committed.set()
                    await asyncio.Future()
                    return result
                profile.edit = delayed
                body = json.dumps(dict(table_id="work_items", key="item-055", column_id="title", expected_revision="1", value="Committed response lost")).encode()
                sent = []
                first = True
                async def receive():
                    nonlocal first
                    if first:
                        first = False
                        return dict(type="http.request", body=body)
                    await asyncio.Future()
                async def send(event):
                    sent.append(event)
                task = asyncio.create_task(service.app(dict(type="http", method="POST", path="/work-items/_table/cell", query_string=b"",
                    headers=[(b"authorization", b"Bearer reader-alice"), (b"content-type", b"application/json")]), receive, send))
                await asyncio.wait_for(committed.wait(), 5)
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task
                self.assertEqual(sent, [])
                profile.edit = original
                fresh = await profile.query(dict(generation=2, filters=[dict(column_id="key", operator="eq", value="item-055")]),
                    __import__("expose_api").Principal("alice"))
                self.assertEqual((fresh["rows"][0]["revision"], fresh["rows"][0]["values"]["title"]), ("2", "Committed response lost"))
            self.assertFalse(service.store._backend._thread.is_alive())
