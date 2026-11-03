"""Actual HTTP/SQLite/Chromium editing, conflict and process-restart acceptance."""

from contextlib import closing
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from playwright.sync_api import expect, sync_playwright

from browser_tabular import running_ui


def records(database):
    with closing(sqlite3.connect(database)) as connection:
        return {row[0]: row for row in connection.execute('SELECT key,title,owner,done,rank,score,_revision FROM app_tabular_items ORDER BY key')}


class BrowserEditableTabular(unittest.TestCase):
    def state(self, page, state):
        expect(page.locator("[data-table-edit-state]")).to_have_attribute("data-table-edit-state", state)

    def begin(self, page, column="title"):
        page.locator(f'[data-table-cell][data-row-key="item-055"][data-column-id="{column}"]').click()
        page.get_by_role("button", name="Edit selected cell", exact=True).click()

    def test_persisted_cell_edits_two_browser_conflicts_invalid_drafts_and_restart(self):
        with sync_playwright() as playwright, TemporaryDirectory() as directory:
            browser = playwright.chromium.launch()
            path = Path(directory) / "editable.sqlite"
            errors = []
            try:
                with running_ui(path, editable=True) as origin:
                    before = records(path)
                    contexts = [browser.new_context(viewport={"width": width, "height": 850}, reduced_motion="reduce") for width in (390, 1280)]
                    try:
                        first, second = [context.new_page() for context in contexts]
                        for page in (first, second):
                            page.on("pageerror", lambda error: errors.append(str(error)))
                            page.goto(origin)
                            expect(page.locator("[data-table-cell]").first).to_have_attribute("data-row-key", "item-040")
                        first.get_by_role("button", name="Sort Title: none", exact=True).click()
                        for page in (first, second):
                            page.get_by_label("Search table", exact=True).fill("%_")
                            expect(page.locator("tbody tr")).to_have_count(1)
                            self.begin(page)
                        first.get_by_label("Cell value", exact=True).fill("Browser durable edit")
                        second.get_by_label("Cell value", exact=True).fill("Accepted draft")
                        first.get_by_role("button", name="Save cell", exact=True).click()
                        self.state(first, "saved")
                        first.get_by_label("Search table", exact=True).fill("")
                        expect(first.locator('[data-table-cell][data-row-key="item-055"][data-column-id="title"]')).to_have_text("Browser durable edit")
                        expect(second.get_by_label("Cell value", exact=True)).to_have_value("Accepted draft")
                        second.get_by_role("button", name="Save cell", exact=True).click()
                        self.state(second, "conflict")
                        expect(second.get_by_label("Cell value", exact=True)).to_have_value("Accepted draft")
                        expect(second.get_by_role("button", name="Save cell", exact=True)).to_be_disabled()
                        second.get_by_role("button", name="Reload current row", exact=True).click()
                        self.state(second, "review")
                        expect(second.locator("form[data-table-editor]")).to_contain_text("Current value: Browser durable edit")
                        second.get_by_role("button", name="Reapply draft to current revision", exact=True).click()
                        second.get_by_role("button", name="Save cell", exact=True).click()
                        self.state(second, "saved")
                        second.get_by_label("Search table", exact=True).fill("")
                        expect(second.locator('[data-table-cell][data-row-key="item-055"][data-column-id="title"]')).to_have_text("Accepted draft")
                        self.begin(second)
                        second.get_by_label("Cell value", exact=True).fill("")
                        second.get_by_role("button", name="Save cell", exact=True).click()
                        self.state(second, "invalid")
                        expect(second.get_by_label("Cell value", exact=True)).to_have_value("")
                        second.get_by_label("Cell value", exact=True).press("Escape")
                        self.begin(second, "key")
                        self.state(second, "read_only")
                        after = records(path)
                        self.assertEqual(after["item-055"], (*before["item-055"][:1], "Accepted draft", *before["item-055"][2:-1], 3))
                        self.assertEqual({k: v for k, v in after.items() if k != "item-055"}, {k: v for k, v in before.items() if k != "item-055"})
                        for page in (first, second):
                            self.assertFalse(page.evaluate("document.documentElement.scrollWidth > innerWidth"))
                            page.locator("#sui-app").dispatch_event("sui:stop")
                    finally:
                        for context in contexts:
                            context.close()
                with running_ui(path, editable=True) as origin:
                    context = browser.new_context()
                    try:
                        page = context.new_page()
                        page.goto(origin)
                        page.get_by_label("Search table", exact=True).fill("Accepted draft")
                        expect(page.locator("tbody tr")).to_have_count(1)
                        expect(page.locator("[data-table-cell]").first).to_have_attribute("data-row-key", "item-055")
                        self.assertEqual(records(path), after)
                    finally:
                        context.close()
                self.assertEqual(errors, [])
                Path("tabular-edit-browser-receipt.json").write_text(json.dumps(dict(profile="cpython-tabular/1", browser="Chromium",
                    editable=True, durable_target=True, independent_drafts=True, stale_conflict=True, explicit_reapply=True,
                    invalid_read_only=True, unrelated_fields_preserved=True, process_restart=True, graceful_close=True,
                    widths=[390, 1280], reduced_motion=True, passed=True), indent=2) + "\n")
            finally:
                browser.close()
