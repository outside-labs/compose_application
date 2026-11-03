import asyncio
from dataclasses import replace
from importlib import metadata
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import unittest
from unittest.mock import patch

from compose_application.live import Credential, LiveApplication, LiveConfig, _dependencies
from compose_application.service import ProfileError

try:
    from expose_api import Principal
    _dependencies()
    AVAILABLE = True
except (ImportError, ProfileError):
    AVAILABLE = False

ALICE = "synthetic-alice-token"
BOB = "synthetic-bob-token"


def configuration(path, *, origin="http://127.0.0.1:8000"):
    alice = Principal("alice", scopes=frozenset({"work-items"}))
    bob = Principal("bob", scopes=frozenset({"work-items"}))
    identities = {ALICE: alice, BOB: bob}
    config = LiveConfig(path, origin, identities.get, (Credential(alice, ALICE), Credential(bob, BOB)))
    return config, identities


async def exchange(app, method="GET", path="/work-items", *, token=ALICE, data=None, revision=None, headers=()):
    body = b"" if data is None else json.dumps(data).encode()
    selected = [(b"host", app.config.origin.split("://", 1)[1].encode()), *headers]
    if token is not None:
        selected.append((b"authorization", ("Bearer " + token).encode()))
    if data is not None:
        selected.append((b"content-type", b"application/json"))
    if revision is not None:
        selected.append((b"if-match", ('"' + revision + '"').encode()))
    incoming, outgoing = asyncio.Queue(), []
    await incoming.put({"type": "http.request", "body": body})
    async def send(event):
        outgoing.append(event)
    await app({"type": "http", "method": method, "path": path, "root_path": "", "query_string": b"",
               "headers": selected}, incoming.get, send)
    start = outgoing[0]
    return start["status"], dict(start["headers"]), b"".join(event.get("body", b"") for event in outgoing[1:])


class LiveConfigurationTests(unittest.TestCase):
    def test_configuration_is_explicit_bounded_and_redacts_credentials(self):
        credential = Credential(object(), ALICE)
        self.assertNotIn(ALICE, repr(credential))
        for token in ("short", "secret?in=url", "x" * 257):
            with self.assertRaises(ValueError):
                Credential(None, token)
        for options in ({"retention": True}, {"retention": 4097}, {"cookie_name": "invalid;cookie"},
                        {"credentials": ()}, {"credentials": (credential, credential)}):
            values = {"database": "unopened.sqlite3", "origin": "http://127.0.0.1:8000", "verify": lambda value: None,
                      "credentials": (credential,), **options}
            with self.assertRaises(ValueError):
                LiveConfig(**values)

    def test_dependency_refusal_is_explicit(self):
        with patch("compose_application.live.metadata.version", side_effect=metadata.PackageNotFoundError("missing")):
            with self.assertRaises(ProfileError):
                _dependencies()


@unittest.skipUnless(AVAILABLE, "optional live source profile is not installed")
class LiveProfileTests(unittest.IsolatedAsyncioTestCase):
    async def test_checked_policy_precedence_projection_and_atomic_journal(self):
        with TemporaryDirectory() as directory:
            config, _ = configuration(Path(directory) / "live.sqlite3")
            async with LiveApplication(config) as app:
                created = await exchange(app, "POST", data={"key": "a", "title": "Garden", "owner": "alice"})
                self.assertEqual((created[0], created[1][b"etag"]), (201, b'"1"'))
                self.assertNotIn(b"owner", created[2])
                self.assertEqual(created[1][b"cache-control"], b"no-store")
                for key in ("a", "missing"):
                    self.assertEqual((await exchange(app, path="/work-items/" + key, token=BOB))[0], 404)
                    self.assertEqual((await exchange(app, "PATCH", "/work-items/" + key, token=BOB,
                        data={"title": "Denied"}, revision="9"))[0], 404)
                    self.assertEqual((await exchange(app, "DELETE", "/work-items/" + key, token=BOB, revision="9"))[0], 404)
                before = await app.store.event_snapshot("a")
                self.assertEqual((await exchange(app, "PATCH", "/work-items/a", data={"title": "Stale"}, revision="9"))[0], 409)
                self.assertEqual((await exchange(app, "PATCH", "/work-items/a", data={"owner": "bob"}, revision="1"))[0], 403)
                self.assertEqual((await exchange(app, "PATCH", "/work-items/a", data={"title": "x" * 201}, revision="1"))[0], 422)
                self.assertEqual((await app.store.event_snapshot("a")).cursor, before.cursor)
                updated = await exchange(app, "PATCH", "/work-items/a", data={"done": True}, revision="1")
                self.assertEqual((updated[0], updated[1][b"etag"]), (200, b'"2"'))
                self.assertTrue((await app.store.event_changes(before.cursor, key="a")).changed)
                self.assertEqual((await exchange(app, "DELETE", "/work-items/a", revision="1"))[0], 409)
                self.assertEqual((await exchange(app, "DELETE", "/work-items/a", revision="2"))[0], 204)

    async def test_cookie_origin_and_principal_owned_ui_sessions(self):
        from spatial_ui.rest import Response
        with TemporaryDirectory() as directory:
            config, identities = configuration(Path(directory) / "live.sqlite3")
            async with LiveApplication(config) as app:
                pages = []
                for token in (ALICE, BOB):
                    with patch("compose_application.live._BridgeTransport.request", return_value=Response(200, [])):
                        page = await exchange(app, path="/", token=None,
                            headers=((b"cookie", ("work_identity=" + token).encode()),))
                    self.assertEqual(page[0], 200)
                    self.assertNotIn(token.encode(), page[2])
                    pages.append(page)
                self.assertNotEqual(pages[0][1][b"set-cookie"], pages[1][1][b"set-cookie"])
                self.assertEqual([len(value._app._sessions) for value in app.adapters.values()], [1, 1])
                self.assertEqual((await exchange(app, path="/", token=None))[0], 401)
                self.assertEqual((await exchange(app, "POST", token=None, data={},
                    headers=((b"cookie", ("work_identity="+ALICE).encode()),)))[0], 403)
                self.assertEqual((await exchange(app, headers=((b"host", b"other"),)))[0], 421)
                identities.pop(ALICE)
                self.assertEqual((await exchange(app))[0], 401)
            self.assertTrue(all(value._executor is None and not value._app._sessions for value in app.adapters.values()))

    async def test_failed_startup_and_cancelled_close_drain_before_restart(self):
        from expose_api import App
        with TemporaryDirectory() as directory:
            config, _ = configuration(Path(directory) / "live.sqlite3")
            threads = {thread.ident for thread in threading.enumerate()}
            app = LiveApplication(config)
            with patch.object(App, "subscribe", side_effect=RuntimeError("synthetic startup failure")):
                with self.assertRaises(RuntimeError):
                    await app.__aenter__()
            self.assertEqual({thread.ident for thread in threading.enumerate()}, threads)
            async with app:
                await app.resource.create({"key": "a", "title": "Persisted", "owner": "alice"})
                entered, release = asyncio.Event(), asyncio.Event()
                original = app.store.aclose
                async def close():
                    entered.set()
                    await release.wait()
                    await original()
                app.store.aclose = close
                task = asyncio.create_task(app.aclose())
                await entered.wait()
                task.cancel()
                release.set()
                with self.assertRaises(asyncio.CancelledError):
                    await task
            self.assertIsNone(app._stack)
            async with app:
                self.assertEqual((await app.resource.get("a")).title, "Persisted")

    async def test_protected_subscription_revocation_and_shutdown_cleanup(self):
        with TemporaryDirectory() as directory:
            config, identities = configuration(Path(directory) / "live.sqlite3")
            app = LiveApplication(config)
            async with app:
                await app.resource.create({"key": "a", "title": "Initial", "owner": "alice"})
                incoming, outgoing = asyncio.Queue(), asyncio.Queue()
                scope = {"type": "websocket", "path": "/work-items/a", "root_path": "", "query_string": b"",
                    "subprotocols": ["expose-api.events.v1"], "scheme": "ws", "headers": [
                        (b"host", b"127.0.0.1:8000"), (b"origin", config.origin.encode()),
                        (b"cookie", ("work_identity=" + ALICE).encode())]}
                task = asyncio.create_task(app(scope, incoming.get, outgoing.put))
                await incoming.put({"type": "websocket.connect"})
                self.assertEqual((await asyncio.wait_for(outgoing.get(), 2))["type"], "websocket.accept")
                await incoming.put({"type": "websocket.receive", "text": '{"v":1,"type":"subscribe","cursor":null}'})
                snapshot = json.loads((await asyncio.wait_for(outgoing.get(), 2))["text"])
                self.assertEqual(snapshot["value"], {"key": "a", "title": "Initial", "done": False})
                identities.pop(ALICE)
                self.assertEqual((await asyncio.wait_for(outgoing.get(), 2))["code"], 1008)
                await asyncio.wait_for(task, 2)
            self.assertEqual(app.api._sockets.tasks, {})

    async def test_invalid_origin_and_duplicate_principals_fail_before_storage(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "unopened.sqlite3"
            config, _ = configuration(path)
            for invalid in (replace(config, origin="https://example.test/path"),
                            replace(config, credentials=(config.credentials[0], Credential(config.credentials[0].principal, "another-synthetic-token")))):
                with self.assertRaises(ValueError):
                    await LiveApplication(invalid).__aenter__()
                self.assertFalse(path.exists())
