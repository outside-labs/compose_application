import asyncio
from importlib import metadata
from unittest.mock import patch
import unittest

from compose_application import ProfileError
from compose_application.ui import _ui_dependencies, accept_ui, make_ui

try:
    from spatial_ui.resource_form import ResourceForm
    from expose_api.backpack import BackpackStore
except ImportError:
    ResourceForm = None


class UIIsolationTests(unittest.TestCase):
    def test_unavailable_or_incompatible_ui_dependency_is_explicit(self):
        for failure in (metadata.PackageNotFoundError("missing"), None):
            with patch("compose_application.ui.metadata.version", side_effect=failure, return_value="99.0"):
                with self.assertRaises(ProfileError):
                    _ui_dependencies()


@unittest.skipIf(ResourceForm is None, "optional UI service profile not installed")
class UIReferenceTests(unittest.TestCase):
    def test_loopback_preview_startup_never_queries_dns(self):
        with patch("socket.getfqdn", side_effect=AssertionError("unexpected reverse DNS")):
            with make_ui("http://127.0.0.1:8000").make_server(0) as server:
                self.assertEqual(server.server_name, "127.0.0.1")
                self.assertGreater(server.server_port, 0)

    def test_installed_public_forms_rest_and_process_restart_receipt(self):
        receipt = asyncio.run(accept_ui())
        self.assertEqual(receipt["profile"], "cpython-ui/1")
        self.assertEqual(receipt["checks"], 15)
        self.assertTrue(receipt["process_restart"])
        self.assertEqual([item["phase"] for item in receipt["phases"]], ["write", "reload"])
