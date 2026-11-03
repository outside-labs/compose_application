"""Real HTTP/Chromium acceptance for persisted read-only dataset views."""

from contextlib import closing, contextmanager
import hashlib
import json
from pathlib import Path
from queue import Queue
import re
import signal
import sqlite3
import subprocess
import sys
from tempfile import TemporaryDirectory
import threading
import unittest

from playwright.sync_api import expect, sync_playwright


@contextmanager
def running_ui(database, principal="alice"):
    process = subprocess.Popen([sys.executable, "-I", "-u", "-m", "compose_application.tabular", "serve",
        "--database", str(database), "--port", "0", "--principal", principal], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    lines = Queue()
    threading.Thread(target=lambda: lines.put(process.stdout.readline()), daemon=True).start()
    try:
        line = lines.get(timeout=15)
        match = re.fullmatch(r"Table reference: (http://127\.0\.0\.1:[0-9]+)\n", line)
        if match is None:
            raise RuntimeError("Table reference did not start: " + line)
        yield match[1]
    finally:
        if process.poll() is None:
            process.send_signal(signal.SIGINT)
        try:
            output, errors = process.communicate(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            raise RuntimeError("Table reference did not drain.")
        if process.returncode:
            raise RuntimeError("Table reference failed: " + errors[-2000:])


def signature(database):
    with closing(sqlite3.connect(database)) as connection:
        rows = connection.execute('SELECT key,title,owner,done,rank,score,_revision FROM app_tabular_items ORDER BY key').fetchall()
    return hashlib.sha256(json.dumps(rows).encode()).hexdigest()


class BrowserTabular(unittest.TestCase):
    def test_independent_read_only_views_denials_controls_and_restart(self):
        with sync_playwright() as playwright, TemporaryDirectory() as directory:
            browser = playwright.chromium.launch()
            database = Path(directory) / "table.sqlite"
            errors = []
            try:
                with running_ui(database) as origin:
                    before = signature(database)
                    first = browser.new_context(viewport={"width": 390, "height": 844}, reduced_motion="reduce")
                    second = browser.new_context(viewport={"width": 1280, "height": 900})
                    try:
                        a, b = first.new_page(), second.new_page()
                        for page in (a, b):
                            page.on("pageerror", lambda error: errors.append(str(error)))
                            page.goto(origin)
                            expect(page.locator("[data-table-cell]").first).to_have_attribute("data-row-key", "item-040")
                        a.get_by_role("button", name="Next page", exact=True).click()
                        expect(a.locator("[data-table-cell]").first).to_have_attribute("data-row-key", "item-090")
                        a.get_by_role("button", name="Sort Title: none", exact=True).click()
                        expect(a.locator("thead th[aria-sort=ascending]")).to_have_count(1)
                        a.get_by_role("button", name="Sort Title: ascending", exact=True).click()
                        expect(a.locator("[data-table-cell]").first).to_have_attribute("data-row-key", "item-119")
                        a.get_by_role("button", name="Show Rank", exact=True).click()
                        expect(a.locator("thead th")).to_have_count(4)
                        a.get_by_role("button", name="Show Rank", exact=True).click()
                        a.get_by_role("button", name="Move rank earlier", exact=True).click()
                        expect(a.locator("thead th").nth(3)).to_have_text("Sort Rank: none")
                        search = a.get_by_label("Search table", exact=True)
                        search.fill("%_")
                        expect(a.locator("[data-table-cell]").first).to_have_attribute("data-row-key", "item-055")
                        expect(a.locator("tbody tr")).to_have_count(1)
                        expect(b.locator("[data-table-cell]").first).to_have_attribute("data-row-key", "item-040")
                        expect(b.get_by_label("Search table", exact=True)).to_have_value("")
                        self.assertNotIn("owner", a.locator("thead").inner_text())
                        self.assertFalse(a.evaluate("document.documentElement.scrollWidth > innerWidth"))
                        self.assertEqual(signature(database), before)
                        with running_ui(database, "bob") as bob_origin:
                            bob_context = browser.new_context()
                            try:
                                bob = bob_context.new_page()
                                bob.goto(bob_origin)
                                expect(bob.locator("[data-table-cell]").first).to_have_attribute("data-row-key", "item-000")
                                expect(bob.locator("tbody tr")).to_have_count(40)
                                expect(bob.get_by_role("button", name="Next page", exact=True)).to_be_disabled()
                            finally:
                                bob_context.close()
                    finally:
                        first.close()
                        second.close()
                self.assertEqual(signature(database), before)
                with running_ui(database) as origin:
                    context = browser.new_context()
                    try:
                        page = context.new_page()
                        page.goto(origin)
                        expect(page.locator("[data-table-cell]").first).to_have_attribute("data-row-key", "item-040")
                    finally:
                        context.close()
                self.assertEqual(signature(database), before)
                self.assertEqual(errors, [])
                Path("tabular-browser-receipt.json").write_text(json.dumps(dict(profile="cpython-tabular/1", browser="Chromium",
                    independent_views=True, principals=2, view_changes_preserve_data_and_revisions=True,
                    process_restart=True, graceful_close=True, widths=[390, 1280], reduced_motion=True, passed=True), indent=2) + "\n")
            finally:
                browser.close()
