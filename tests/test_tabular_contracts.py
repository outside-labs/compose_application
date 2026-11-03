import copy
import json
from pathlib import Path
import unittest

from scripts.check_tabular import check_fixture


class TabularContractsTests(unittest.TestCase):
    def setUp(self):
        self.fixture = json.loads((Path(__file__).resolve().parents[1] / "docs/contracts/tabular-v1.json").read_text())

    def test_fixture(self):
        check_fixture(self.fixture)
        self.assertNotEqual(self.fixture["pages"][0]["rows"][0]["key"], "row-001")

    def test_hidden_values_and_invalid_capabilities_are_refused(self):
        for change in ("hidden", "capability", "revision", "boolean"):
            fixture = copy.deepcopy(self.fixture)
            if change == "hidden":
                fixture["pages"][0]["rows"][0]["values"]["owner"] = "secret"
            elif change == "capability":
                fixture["schema"]["columns"][2]["searchable"] = True
            elif change == "revision":
                fixture["pages"][0]["rows"][0]["revision"] = 1
            else:
                fixture["pages"][0]["rows"][0]["values"]["done"] = 1
            with self.subTest(change=change), self.assertRaises(ValueError):
                check_fixture(fixture)
