import unittest

from scripts.check_contracts import check_json, check_resource, check_revision


class ContractTests(unittest.TestCase):
    def test_revision_round_trips_without_javascript_number_conversion(self):
        check_revision("9007199254740992")
        check_revision("9223372036854775807")
        for value in (1, True, "0", "01", "+1", "1.0", "9223372036854775808", "١"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                check_revision(value)

    def test_non_json_and_unbounded_values_are_refused(self):
        for value in (float("nan"), float("inf"), 9007199254740992, {1: "value"}, (1, 2)):
            with self.subTest(value=value), self.assertRaises(ValueError):
                check_json(value)
        value = None
        for _ in range(16):
            value = [value]
        check_json(value)
        with self.assertRaises(ValueError):
            check_json([value])

    def test_deletion_has_no_value_and_domain_keys_are_bounded(self):
        resource = {"collection": "work_items", "key": "item-001", "revision": "3"}
        check_resource(resource, deleted=True)
        with self.assertRaises(ValueError):
            check_resource({**resource, "value": {}}, deleted=True)
        for key in ("", "../item", "x" * 129, "café"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                check_resource({**resource, "key": key}, deleted=True)
