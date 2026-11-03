"""Actual Chromium acceptance of the protected cross-worker live composition."""

import asyncio
from contextlib import contextmanager
from dataclasses import replace
import json
import os
from pathlib import Path
from queue import Queue
from tempfile import TemporaryDirectory
import threading
import unittest

from playwright.sync_api import sync_playwright, expect
from expose_api import NotFoundError
from compose_application.live import LiveApplication
from test_live_profile import ALICE, BOB, configuration
from test_live_process import run_worker_sync
from websocket_host import WireHost


@contextmanager
def running_reference(database, port=0):
    ready, failures, receipts = Queue(), [], []
    def worker():
        async def run():
            host = WireHost()
            async with host.listening(port):
                config, identities = configuration(database, origin=host.origin)
                app = LiveApplication(replace(config, retention=4))
                async with app:
                    try:
                        await app.resource.get("item-001")
                    except NotFoundError:
                        await app.resource.create({"key": "item-001", "title": "Initial", "owner": "alice"})
                    gate = asyncio.Event()
                    gate.set()
                    async def route(scope, receive, send):
                        if scope["type"] == "websocket":
                            await gate.wait()
                        await app(scope, receive, send)
                    host.app = route
                    stop = asyncio.Event()
                    ready.put((asyncio.get_running_loop(), stop, host, app, identities, gate))
                    await stop.wait()
                receipts.append({"api_sockets": len(app.api._sockets.tasks), "requests": len(app._requests),
                    "ui_sessions": sum(len(ui._app._sessions) for ui in app.adapters.values()),
                    "workers_closed": all(ui._executor is None for ui in app.adapters.values()), "storage_closed": app._stack is None})
        try:
            asyncio.run(run())
        except BaseException as error:
            failures.append(error)
            ready.put(None)
    thread = threading.Thread(target=worker, name="live-reference-host")
    thread.start()
    state = None
    try:
        state = ready.get(timeout=20)
        if state is None:
            raise RuntimeError("Live reference startup failed") from failures[0]
        class Control:
            origin, port = state[2].origin, state[2].port
            def update(self, title, **options):
                receipt = run_worker_sync(database, title, **options)
                if receipt["pid"] == os.getpid():
                    raise AssertionError("Expected a different OS writer process")
                return receipt
            def reconnect_after_retention(self):
                async def pause():
                    state[5].clear()
                    state[2].drop()
                asyncio.run_coroutine_threadsafe(pause(), state[0]).result(5)
                try:
                    return self.update("Offline ", count=8)
                finally:
                    state[0].call_soon_threadsafe(state[5].set)
            def revoke(self):
                async def revoke():
                    state[4].pop(ALICE)
                asyncio.run_coroutine_threadsafe(revoke(), state[0]).result(5)
            def resynced(self):
                return any(json.loads(message).get("type") == "resync" for message in state[2].messages)
        yield Control()
    finally:
        if state:
            state[0].call_soon_threadsafe(state[5].set)
            state[0].call_soon_threadsafe(state[1].set)
        thread.join(20)
        if thread.is_alive():
            raise RuntimeError("Live reference did not stop")
        if failures:
            raise RuntimeError("Live reference failed") from failures[0]
        if receipts != [{"api_sockets": 0, "requests": 0, "ui_sessions": 0, "workers_closed": True, "storage_closed": True}]:
            raise AssertionError(f"Live reference retained owned state: {receipts}")


INSTRUMENT = """(() => {
  const Socket = window.WebSocket, schedule = window.setTimeout, cancel = window.clearTimeout;
  window.liveSockets=[]; window.liveTimers=new Set();
  window.WebSocket=class extends Socket {constructor(...args){super(...args);liveSockets.push(this)}};
  window.setTimeout=(callback,delay,...args)=>{
    const live=new Error().stack.includes('/_spatial/live.js');
    const id=schedule(()=>{liveTimers.delete(id);callback(...args)},delay);
    if(live) liveTimers.add(id); return id;
  };
  window.clearTimeout=id=>{liveTimers.delete(id);cancel(id)};
})()"""


class BrowserLiveReference(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch()
        cls.passed_cases = []

    def setUp(self):
        result = self._outcome.result
        self.failures_before = len(result.failures) + len(result.errors)

    def tearDown(self):
        result = self._outcome.result
        if len(result.failures) + len(result.errors) == self.failures_before:
            self.passed_cases.append(self._testMethodName)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        Path("live-reference-browser-receipt.json").write_text(json.dumps({
            "profile": "cpython-live/1", "browser": "Chromium", "widths": [390, 1280],
            "passed": len(cls.passed_cases) == 2, "passed_cases": cls.passed_cases,
            "principals": 2, "independent_contexts": 3, "writer": "separate OS process", "reduced_motion": True,
            "cases": ["protected-cookie", "field-validation", "keyboard-checkbox", "draft-focus-selection",
                "cross-worker-snapshot", "checked-conflict-merge-discard", "principal-isolation", "reconnect-resync",
                "stale-generation", "revocation", "stop-reload", "same-origin-restart-stale-token"],
            "shutdown": {"api_sockets": 0, "requests": 0, "ui_sessions": 0, "workers_closed": True, "storage_closed": True},
            "sources": json.loads(Path("docs/compatibility-v1.json").read_text())["live"]["packages"],
        }, indent=2) + "\n", encoding="utf-8")

    def context(self, origin, *, token=ALICE, width=1280):
        context = self.browser.new_context(viewport={"width": width, "height": 850}, reduced_motion="reduce")
        context.add_cookies([{"name": "work_identity", "value": token, "url": origin, "httpOnly": True, "sameSite": "Strict"}])
        context.add_init_script(INSTRUMENT)
        self.addCleanup(context.close)
        return context

    def apply(self, page, operation):
        page.locator('[name="operation"]').select_option(operation)
        page.get_by_role("button", name="Apply", exact=True).click()

    def loaded(self, context, origin):
        page = context.new_page()
        page.goto(origin)
        page.locator('[name="key"]').fill("item-001")
        self.apply(page, "load")
        expect(page.locator("#sui-status")).to_have_text("Loaded.")
        expect(page.locator("[data-sui-live]")).to_have_attribute("data-sui-live-state", "live")
        return page

    def test_cross_worker_edits_conflicts_merge_discard_and_principal_isolation(self):
        for width in (390, 1280):
            with self.subTest(width=width), TemporaryDirectory(prefix="live-reference-browser-") as directory:
                with running_reference(Path(directory) / "items.sqlite3") as service:
                    first, second, denied = self.context(service.origin, width=width), self.context(service.origin), self.context(service.origin, token=BOB)
                    try:
                        page, other = self.loaded(first, service.origin), self.loaded(second, service.origin)
                        errors = []
                        page.on("pageerror", lambda error: errors.append(str(error)))
                        title = page.locator('[name="title"]')
                        title.fill("")
                        self.apply(page, "save")
                        expect(title).to_have_attribute("aria-invalid", "true")
                        expect(title).to_be_focused()
                        title.fill("Local merge")
                        page.locator('[name="done"]').check()
                        title.focus()
                        title.evaluate("node=>node.setSelectionRange(2,5)")
                        service.update("Another worker 🌱")
                        expect(page.locator("[data-live-value]")).to_contain_text("Another worker 🌱")
                        expect(title).to_have_value("Local merge")
                        expect(title).to_be_focused()
                        self.assertEqual(title.evaluate("node=>[node.selectionStart,node.selectionEnd]"), [2, 5])
                        expect(other.locator('[name="title"]')).to_have_value("Initial")
                        title.press("Enter")
                        expect(page.locator("#sui-status")).to_contain_text("record changed")
                        self.apply(page, "load")
                        expect(page.locator("#sui-status")).to_have_text("Loaded.")
                        expect(title).to_have_value("Local merge")
                        title.press("Enter")
                        expect(page.locator("#sui-status")).to_have_text("Saved.")
                        expect(page.locator('[name="done"]')).to_be_checked()
                        expect(other.locator("[data-live-value]")).to_contain_text("Local merge")
                        other.locator('[name="title"]').fill("Discard me")
                        self.apply(other, "load")
                        expect(other.locator("#sui-status")).to_have_text("Loaded.")
                        expect(other.locator('[name="title"]')).to_have_value("Discard me")
                        self.apply(other, "discard")
                        expect(other.locator('[name="title"]')).to_have_value("Local merge")
                        foreign = denied.new_page()
                        foreign.goto(service.origin)
                        foreign.locator('[name="key"]').fill("item-001")
                        self.apply(foreign, "load")
                        expect(foreign.locator("#sui-status")).to_contain_text("request failed")
                        self.assertEqual(foreign.locator("[data-sui-live]").count(), 0)
                        self.assertNotIn("Another worker", foreign.locator("main").inner_text())
                        self.assertNotIn("owner", page.locator("[data-live-value]").inner_text())
                        self.assertFalse(page.evaluate("document.documentElement.scrollWidth>innerWidth"))
                        self.assertEqual(errors, [])
                    finally:
                        first.close(); second.close(); denied.close()

    def test_recovery_revocation_stop_and_same_origin_graceful_restart(self):
        with TemporaryDirectory(prefix="live-reference-restart-") as directory:
            database = Path(directory) / "items.sqlite3"
            with running_reference(database) as service:
                context = self.context(service.origin)
                page = self.loaded(context, service.origin)
                title = page.locator('[name="title"]')
                title.fill("Pending local draft")
                expect(page.locator("#sui-status")).to_have_text("Unsaved changes.")
                page.evaluate("()=>{window.oldMessage=liveSockets.at(-1).onmessage;}")
                service.reconnect_after_retention()
                expect(page.locator("[data-live-value]")).to_contain_text("Offline 7")
                self.assertTrue(service.resynced())
                expect(title).to_have_value("Pending local draft")
                page.evaluate('''()=>oldMessage({data:JSON.stringify({v:1,type:'snapshot',cursor:'f'.repeat(32),
                    value:{key:'item-001',title:'Stale forbidden',done:false}})})''')
                expect(page.locator("[data-live-value]")).not_to_contain_text("Stale forbidden")
                page.locator("#sui-app").dispatch_event("sui:stop")
                page.wait_for_function("()=>liveTimers.size===0 && liveSockets.every(s=>s.readyState===3 && s.onmessage===null && s.onclose===null)")
                page.reload()
                expect(page.locator('[name="title"]')).to_have_value("Pending local draft")
                expect(page.locator("[data-live-value]")).to_contain_text("Offline 7")
                service.revoke()
                expect(page.locator("[data-sui-live]")).to_have_attribute("data-sui-live-state", "unavailable")
                expect(page.locator("[data-live-value]")).to_have_text("")
                old = page.evaluate('''()=>({token:document.querySelector('meta[name="sui-token"]').content,
                    event:document.querySelector('form').dataset.suiForm,version:Number(document.querySelector('#sui-app').dataset.version)})''')
                port, origin = service.port, service.origin
            with running_reference(database, port=port) as restarted:
                self.assertEqual(restarted.origin, origin)
                page.reload()
                expect(page.locator('[name="title"]')).to_have_value("")
                stale = page.evaluate('''async old=>(await fetch('/_spatial/event',{method:'POST',headers:{'Content-Type':'application/json',
                    'X-Spatial-Token':old.token},body:JSON.stringify({event:old.event,version:old.version,
                    payload:{kind:'input',fields:{title:'Stale forbidden'}}})})).status''', old)
                self.assertEqual(stale, 403)
                page.locator('[name="key"]').fill("item-001")
                self.apply(page, "load")
                expect(page.locator("[data-live-value]")).to_contain_text("Offline 7")
                context.close()
