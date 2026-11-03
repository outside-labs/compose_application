import asyncio
from importlib import metadata
from unittest.mock import patch
import unittest

from compose_application import ProfileError
from compose_application.ui import _ui_dependencies, accept_ui

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
    def test_installed_public_forms_rest_and_process_restart_receipt(self):
        receipt = asyncio.run(accept_ui())
        self.assertEqual(receipt["profile"], "cpython-ui/1")
        self.assertEqual(receipt["checks"], 15)
        self.assertTrue(receipt["process_restart"])
        self.assertEqual([item["phase"] for item in receipt["phases"]], ["write", "reload"])
