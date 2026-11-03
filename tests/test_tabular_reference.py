import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from compose_application import ProfileError
from compose_application.tabular import accept_tabular, dependencies, tabular_application

try:
    dependencies()
    AVAILABLE = True
except ProfileError:
    AVAILABLE = False


class TabularIsolationTests(unittest.TestCase):
    def test_missing_profile_fails_before_storage(self):
        original = __import__
        def importing(name, *args, **kwargs):
            if name == "expose_api":
                raise ImportError
            return original(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=importing), self.assertRaises(ProfileError):
            dependencies()


@unittest.skipUnless(AVAILABLE, "optional tabular source profile is not installed")
class TabularReferenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_http_principals_stable_data_stale_pages_and_process_restart(self):
        receipt = await accept_tabular()
        self.assertEqual(receipt["checks"], 18)
        self.assertTrue(receipt["process_restart"])
        self.assertEqual([r["phase"] for r in receipt["phases"]], ["seed", "reopen"])

    async def test_headless_source_binding_uses_actual_public_snapshot(self):
        from headless_spreadsheets import Cell, Table, TableSource
        from spatial_ui import HeadlessTableClient, TableBrowser
        table = Table(["Title", "Value"], [["Zulu", Cell(2, formula="=1+1", number_format="0")], ["Alpha", 1]])
        before = table.to_json()
        component = TableBrowser(HeadlessTableClient(TableSource(table), owns_source=True), page_size=1, owns_client=True)
        try:
            component.binding.sort("c1")
            async with asyncio.timeout(5):
                while component.binding.status == "loading":
                    component.binding.poll()
                    await asyncio.sleep(.001)
            self.assertEqual(component.binding.page.rows[0].key, "r2")
            self.assertEqual(component.binding.page.rows[0].values, ("Alpha", "1"))
            self.assertEqual(table.to_json(), before)
            self.assertEqual(table.cell("B2").formula, "=1+1")
        finally:
            component.close()
        self.assertTrue(component.binding.client.source._closed)

    async def test_repeated_seed_preserves_existing_values_and_revisions(self):
        from dataclasses import replace
        with TemporaryDirectory() as directory:
            database = Path(directory) / "items.sqlite"
            async with tabular_application(database) as first:
                await first.store.update_checked("item-040", expected_revision="1", transform=lambda row: replace(row, title="Retained"))
            async with tabular_application(database) as second:
                row = await second.store.get_row("item-040")
                self.assertEqual((row.value.title, row.revision), ("Retained", "2"))
            self.assertFalse(second.store._backend._thread.is_alive())
