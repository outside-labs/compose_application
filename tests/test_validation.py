from dataclasses import dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import unittest
from unittest.mock import AsyncMock, patch
from types import SimpleNamespace

from compose_application import ProfileError, ServiceConfig, application
from compose_application.reference import WorkItem, _accept_phase, _validation_profile

try:
    from expose_api import App, ConfigurationError, ValidationError
    from expose_api.enforce_type import EnforceTypeSchema
except ImportError:
    EnforceTypeSchema = None


def configuration(path, *, model=WorkItem):
    return ServiceConfig(model, path, namespace="work_items", table="app_work_items", type_key="example.work_item",
                         id_field="key", resource_path="/work-items", public=True, profile="cpython-service-enforce-type/1")


class ValidationConfigurationTests(unittest.IsolatedAsyncioTestCase):
    async def test_unavailable_adapter_is_refused_before_storage_opens(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "unopened.sqlite3"
            store = SimpleNamespace(open=AsyncMock())
            with patch("compose_application.service._dependencies", return_value=(None, store)), \
                 patch("compose_application.service.import_module", side_effect=ImportError):
                with self.assertRaises(ProfileError):
                    async with application(configuration(path)):
                        self.fail("unavailable adapter started")
            store.open.assert_not_awaited()
            self.assertFalse(path.exists())

    def test_reference_validation_selection_is_explicit(self):
        self.assertEqual(_validation_profile("builtin"), "cpython-service/1")
        self.assertEqual(_validation_profile("enforce-type"), "cpython-service-enforce-type/1")
        for value in (None, "auto", True, []):
            with self.subTest(value=value), self.assertRaises(ValueError):
                _validation_profile(value)


@unittest.skipIf(EnforceTypeSchema is None, "optional validation profile not installed")
class ValidationProfileTests(unittest.IsolatedAsyncioTestCase):
    async def test_selected_schema_constructor_rollback_persistence_and_cleanup(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "items.sqlite3"
            threads = {thread.ident for thread in threading.enumerate()}
            async with application(configuration(path)) as service:
                self.assertIsInstance(service.resource.schema, EnforceTypeSchema)
                self.assertEqual(service.app.state["profile"], "cpython-service-enforce-type/1")
                await service.resource.create({"key": "garden", "title": "Garden 🌱"})
                with self.assertRaises(ValidationError):
                    await service.resource.update("garden", {"title": ""})
                self.assertEqual((await service.store.get_row("garden")).revision, "1")
            await service.aclose()
            async with application(configuration(path)) as service:
                self.assertEqual((await service.resource.get("garden")).title, "Garden 🌱")
            self.assertEqual({thread.ident for thread in threading.enumerate()}, threads)

    async def test_real_checked_http_and_reopen_acceptance(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "work-items.sqlite3"
            receipts = [await _accept_phase(path, phase, "enforce-type") for phase in ("write", "reload")]
            self.assertEqual(sum(receipt["checks"] for receipt in receipts), 16)
            self.assertTrue(all(receipt["passed"] for receipt in receipts))

    async def test_invalid_schema_and_failed_startup_release_ownership(self):
        @dataclass
        class Computed:
            key: str
            count: int = field(init=False, default=1)
        with TemporaryDirectory() as directory:
            path = Path(directory) / "items.sqlite3"
            with self.assertRaises(ConfigurationError):
                async with application(configuration(path, model=Computed)):
                    self.fail("unsupported model started")
            self.assertFalse(path.exists())
            threads = {thread.ident for thread in threading.enumerate()}
            with patch.object(App, "include", side_effect=RuntimeError("failed startup")), self.assertRaises(RuntimeError):
                async with application(configuration(path)):
                    self.fail("failed startup yielded")
            self.assertEqual({thread.ident for thread in threading.enumerate()}, threads)
