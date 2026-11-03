import asyncio
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import unittest
from unittest.mock import patch

from compose_application import ProfileError, ServiceConfig, application

try:
    from expose_api.backpack import BackpackStore
except ImportError:
    BackpackStore = None


@dataclass
class Item:
    id: str
    title: str


def configuration(path, **options):
    return ServiceConfig(Item, path, namespace="items", table="app_items", type_key="example.item", public=True, **options)


class ConfigurationTests(unittest.IsolatedAsyncioTestCase):
    async def test_unavailable_and_incompatible_dependencies_fail_before_io(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "missing.sqlite3"
            for failure in (metadata.PackageNotFoundError("missing"), None):
                with patch("compose_application.service.metadata.version", side_effect=failure, return_value="99.0"):
                    with self.assertRaises(ProfileError):
                        async with application(configuration(path)):
                            self.fail("incompatible service started")
                self.assertFalse(path.exists())

    def test_profile_access_and_capacity_are_explicit(self):
        for options in ({"profile": "track-b-local/1"}, {"queue_limit": True}, {"max_body_size": 65537}, {"resource_path": "/bad/"}):
            with self.subTest(options=options), self.assertRaises((ValueError, ProfileError)):
                configuration(Path("unopened.sqlite3"), **options)
        with self.assertRaises(ValueError):
            ServiceConfig(Item, Path("unopened.sqlite3"), "items", "app_items", "example.item")


@unittest.skipIf(BackpackStore is None, "optional service profile not installed")
class ServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_lifecycle_persists_and_repeated_close_is_safe(self):
        with TemporaryDirectory() as directory:
            config = configuration(Path(directory) / "items.sqlite3")
            async with application(config) as service:
                await service.resource.create({"id": "a", "title": "Garden"})
                self.assertEqual(service.app.state["profile"], "cpython-service/1")
            await service.aclose()
            async with application(config) as reopened:
                self.assertEqual((await reopened.resource.get("a")).title, "Garden")

    async def test_failed_startup_closes_owned_worker(self):
        from expose_api import App
        with TemporaryDirectory() as directory:
            config = configuration(Path(directory) / "items.sqlite3")
            before = {thread.ident for thread in threading.enumerate()}
            with patch.object(App, "include", side_effect=RuntimeError("failed startup")):
                with self.assertRaises(RuntimeError):
                    async with application(config):
                        self.fail("failed startup yielded")
            self.assertEqual({thread.ident for thread in threading.enumerate()}, before)
            async with application(config) as service:
                self.assertEqual(await service.resource.list(), [])

    async def test_cancelled_close_finishes_cleanup_before_returning(self):
        with TemporaryDirectory() as directory:
            async with application(configuration(Path(directory) / "items.sqlite3")) as service:
                gate = asyncio.Event()
                closed = []
                original = service.store.aclose
                async def delayed_close():
                    await gate.wait()
                    await original()
                    closed.append(True)
                service.store.aclose = delayed_close
                task = asyncio.create_task(service.aclose())
                await asyncio.sleep(0)
                task.cancel()
                gate.set()
                with self.assertRaises(asyncio.CancelledError):
                    await task
                self.assertEqual(closed, [True])
