"""Chromium acceptance of the runnable persistent UI reference."""

from contextlib import contextmanager
import json
from pathlib import Path
from queue import Queue
import re
import signal
import subprocess
import sys
from tempfile import TemporaryDirectory
import threading
import unittest

from playwright.sync_api import sync_playwright, expect


@contextmanager
def running_ui(database):
    process = subprocess.Popen([sys.executable, "-I", "-u", "-m", "compose_application.ui", "serve",
                                "--database", str(database), "--port", "0"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    lines = Queue()
    threading.Thread(target=lambda: lines.put(process.stdout.readline()), daemon=True).start()
    try:
        line = lines.get(timeout=15)
        match = re.fullmatch(r"Work items: (http://127\.0\.0\.1:[0-9]+)\n", line)
        if match is None:
            raise RuntimeError("Reference UI failed to start: " + line)
        yield match[1]
    finally:
        if process.poll() is None:
            process.send_signal(signal.SIGINT)
        try:
            output, errors = process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            raise RuntimeError("Reference UI failed to stop.")
        if process.returncode != 0:
            raise RuntimeError("Reference UI exited unsuccessfully: " + errors[-4000:])


class BrowserUI(unittest.TestCase):
    def test_persistent_independent_editors_conflicts_focus_layout_and_restart(self):
        with sync_playwright() as playwright, TemporaryDirectory() as directory:
            browser = playwright.chromium.launch()
            first = browser.new_context(viewport={"width": 390, "height": 844}, reduced_motion="reduce")
            second = browser.new_context(viewport={"width": 1280, "height": 900})
            errors = []
            pages = [first.new_page(), second.new_page()]
            for page in pages:
                page.on("pageerror", lambda error: errors.append(str(error)))
            a, b = pages
            def field(page, name):
                return page.locator(f"#resource-editor-{name}")
            def apply(page, operation="save"):
                field(page, "operation").select_option(operation)
                page.get_by_role("button", name="Apply", exact=True).click()
            def revision(page, value):
                expect(page.get_by_text(f"Revision: {value}", exact=True)).to_be_visible()
            database = Path(directory) / "items.sqlite3"
            try:
                with running_ui(database) as origin:
                    a.goto(origin)
                    b.goto(origin)
                    field(a, "key").fill("item-001")
                    apply(a)
                    expect(field(a, "title")).to_be_focused()
                    expect(field(a, "title")).to_have_attribute("aria-invalid", "true")
                    field(a, "title").fill("Initial 🌱")
                    field(a, "done").check()
                    field(a, "title").press("Enter")
                    revision(a, "1")
                    expect(field(b, "title")).to_have_value("")
                    field(b, "key").fill("item-001")
                    apply(b, "load")
                    revision(b, "1")
                    expect(field(b, "title")).to_have_value("Initial 🌱")
                    expect(field(b, "done")).to_be_checked()
                    field(a, "title").fill("Remote title")
                    apply(a)
                    revision(a, "2")
                    field(b, "title").fill("Local draft")
                    apply(b)
                    expect(b.locator("#sui-status")).to_contain_text("record changed")
                    expect(field(b, "title")).to_have_value("Local draft")
                    apply(b, "load")
                    revision(b, "2")
                    expect(field(b, "title")).to_have_value("Local draft")
                    b.get_by_text("Loaded server value", exact=True).click()
                    expect(b.locator("dd").filter(has_text="Remote title")).to_be_visible()
                    apply(b, "discard")
                    expect(field(b, "title")).to_have_value("Remote title")
                    field(b, "title").fill("Retained after restart")
                    apply(b)
                    revision(b, "3")
                    field(a, "title").fill("Pending first draft")
                    a.get_by_role("button", name="Refresh list", exact=True).click()
                    expect(a.locator("li")).to_contain_text("Retained after restart")
                    expect(field(a, "title")).to_have_value("Pending first draft")
                    for width in (390, 1280):
                        a.set_viewport_size({"width": width, "height": 900})
                        self.assertFalse(a.evaluate("document.documentElement.scrollWidth > innerWidth"))
                with running_ui(database) as origin:
                    a.goto(origin)
                    field(a, "key").fill("item-001")
                    apply(a, "load")
                    revision(a, "3")
                    expect(field(a, "title")).to_have_value("Retained after restart")
                    apply(a, "delete")
                    expect(field(a, "key")).to_have_value("")
                    a.get_by_role("button", name="Refresh list", exact=True).click()
                    expect(a.locator("li")).to_have_count(0)
                self.assertEqual(errors, [])
                receipt = {"profile": "cpython-ui/1", "browser": "Chromium", "passed": True,
                           "independent_sessions": 2, "widths": [390, 1280], "process_restart": True,
                           "checks": ["validation-focus", "keyboard-submit", "checkbox", "checked-conflict",
                                      "preserved-draft", "refresh-merge-discard", "committed-projection",
                                      "independent-session-edit", "bounded-list", "restart-persistence", "delete", "reduced-motion"]}
                Path("ui-browser-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
            finally:
                first.close()
                second.close()
                browser.close()
