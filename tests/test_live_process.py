"""Required live-profile acceptance with independently opened OS processes."""

import asyncio
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from compose_application.live import LiveApplication
from test_live_profile import ALICE, AVAILABLE, configuration


WORKER = '''
import asyncio,json,os,sys
from dataclasses import replace
from pathlib import Path
from expose_api import Principal
from expose_api.backpack import BackpackStore
from compose_application.live import OwnedWorkItem,Credential,LiveApplication,LiveConfig
async def run():
    database,key,title,count,retention,mode=sys.argv[1:]
    if mode == "inspect":
        principal=Principal("alice",scopes=frozenset({"work-items"}))
        token="synthetic-alice-token"
        config=LiveConfig(Path(database),"http://127.0.0.1:8000",lambda value: principal if value==token else None,
                          (Credential(principal,token),),retention=int(retention))
        app=LiveApplication(config)
        async with app:
            row=await app.store.get_row(key)
            snapshot=await app.store.event_snapshot(key)
        return {"pid":os.getpid(),"title":row.value.title,"revision":row.revision,"cursor":snapshot.cursor,
                "closed":app._stack is None and all(ui._executor is None for ui in app.adapters.values())}
    async with await BackpackStore.open(OwnedWorkItem,Path(database),namespace="live_work_items",table="app_live_work_items",
            type_key="example.live_work_item",id_field="key",events=int(retention),event_namespace="live_work_item_events") as store:
        for index in range(int(count)):
            value=title if int(count)==1 else title+str(index)
            row=await store.update_checked(key,transform=lambda current:replace(current,title=value))
        snapshot=await store.event_snapshot(key)
        return {"pid":os.getpid(),"title":row.value.title,"revision":row.revision,"cursor":snapshot.cursor}
print(json.dumps(asyncio.run(run())))
'''


def worker_command(database, title="Remote", *, count=1, retention=4, mode="write"):
    return [sys.executable, "-I", "-c", WORKER, str(database), "item-001", title, str(count), str(retention), mode]


def run_worker_sync(database, title="Remote", **options):
    result = subprocess.run(worker_command(database, title, **options), capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise RuntimeError("Synthetic live worker failed: " + result.stderr[-3000:])
    return json.loads(result.stdout)


async def run_worker(database, title="Remote", **options):
    process = await asyncio.create_subprocess_exec(*worker_command(database, title, **options),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        output, errors = await asyncio.wait_for(process.communicate(), 30)
        if process.returncode:
            raise RuntimeError("Synthetic live worker failed: " + errors.decode("utf-8", errors="replace")[-3000:])
        return json.loads(output)
    finally:
        if process.returncode is None:
            process.kill()
            await process.communicate()


class Socket:
    def __init__(self, app):
        self.app = app
        self.incoming, self.outgoing = asyncio.Queue(), asyncio.Queue()
        self.task = None

    async def start(self, cursor=None):
        scope = {"type": "websocket", "path": "/work-items/item-001", "root_path": "", "query_string": b"",
            "scheme": "ws", "subprotocols": ["expose-api.events.v1"], "headers": [
                (b"host", b"127.0.0.1:8000"), (b"origin", self.app.config.origin.encode()),
                (b"cookie", ("work_identity=" + ALICE).encode())]}
        self.task = asyncio.create_task(self.app(scope, self.incoming.get, self.outgoing.put))
        await self.incoming.put({"type": "websocket.connect"})
        assert (await self.next())["type"] == "websocket.accept"
        await self.incoming.put({"type": "websocket.receive", "text": json.dumps({"v": 1, "type": "subscribe", "cursor": cursor})})

    async def next(self):
        event = await asyncio.wait_for(self.outgoing.get(), 5)
        return json.loads(event["text"]) if event["type"] == "websocket.send" else event

    async def snapshot(self, title):
        for _ in range(16):
            event = await self.next()
            if event.get("type") == "snapshot" and event["value"]["title"] == title:
                return event
        raise AssertionError("Current authorized snapshot was not delivered")

    async def close(self):
        if self.task is not None:
            await self.incoming.put({"type": "websocket.disconnect", "code": 1000})
            await asyncio.wait_for(self.task, 5)


@unittest.skipUnless(AVAILABLE, "optional live source profile is not installed")
class LiveProcessTests(unittest.IsolatedAsyncioTestCase):
    async def test_other_process_commits_are_delivered_to_independent_subscribers(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "items.sqlite3"
            config, _ = configuration(path)
            async with LiveApplication(replace(config, retention=4)) as app:
                await app.resource.create({"key": "item-001", "title": "Initial", "owner": "alice"})
                first, second = Socket(app), Socket(app)
                self.addAsyncCleanup(first.close)
                self.addAsyncCleanup(second.close)
                await first.start(); await second.start()
                before = await first.snapshot("Initial")
                await second.snapshot("Initial")
                receipt = await run_worker(path, "Committed from another process")
                self.assertNotEqual(receipt["pid"], os.getpid())
                for socket in (first, second):
                    changed = await socket.snapshot("Committed from another process")
                    self.assertNotEqual(changed["cursor"], before["cursor"])
                    self.assertNotIn("owner", changed["value"])
                await first.close(); await second.close()
                self.assertEqual(app.api._sockets.tasks, {})

    async def test_application_process_restart_retention_resync_and_store_cleanup(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "items.sqlite3"
            config, _ = configuration(path)
            app = LiveApplication(replace(config, retention=4))
            async with app:
                await app.resource.create({"key": "item-001", "title": "Initial", "owner": "alice"})
                first = Socket(app)
                await first.start()
                cursor = (await first.snapshot("Initial"))["cursor"]
            self.assertEqual((await first.next())["code"], 1001)
            await first.close()
            initial = await run_worker(path, mode="inspect")
            self.assertTrue(initial["closed"])
            self.assertEqual(initial["revision"], "1")
            await run_worker(path, "Missed ", count=8)
            restarted = await run_worker(path, mode="inspect")
            self.assertNotEqual(initial["pid"], restarted["pid"])
            self.assertTrue(restarted["closed"])
            self.assertEqual((restarted["title"], restarted["revision"]), ("Missed 7", "9"))
            async with app:
                second = Socket(app)
                self.addAsyncCleanup(second.close)
                await second.start(cursor)
                self.assertEqual(await second.next(), {"v": 1, "type": "resync"})
                snapshot = await second.snapshot("Missed 7")
                self.assertEqual(snapshot["cursor"], restarted["cursor"])
                await second.close()
            self.assertEqual(app.api._sockets.tasks, {})
            self.assertTrue(all(not adapter._app._sessions and adapter._executor is None for adapter in app.adapters.values()))
