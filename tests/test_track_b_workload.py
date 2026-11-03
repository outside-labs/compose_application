import asyncio
import json
import unittest

from examples.track_b_work_items import WorkItem, dump_item, load_item, reload_item, render_item, save_item


class MemoryHost:
    def __init__(self):
        self.values = {}

    async def save(self, key, payload, generation):
        self.values[key] = payload
        return {"generation": generation, "committed": True}

    async def load(self, key, generation):
        return self.values[key]


class WorkloadTests(unittest.TestCase):
    def test_save_reload_keeps_unicode_and_string_revision(self):
        async def scenario():
            host = MemoryHost()
            item = WorkItem("item-001", "Check café 🌱", True)
            self.assertEqual(await save_item(host, item, "9007199254740992", 3),
                             {"generation": 3, "committed": True})
            self.assertEqual(await reload_item(host, item.key, 4), (item, "9007199254740992"))
        asyncio.run(scenario())

    def test_view_preserves_text_values_without_html_evaluation(self):
        self.assertEqual(render_item(WorkItem("item-001", "<b>Garden</b>")),
                         {"kind": "text", "strings": ["", ": ", ""], "values": ["<b>Garden</b>", "False"]})

    def test_saved_version_unknown_fields_and_types_are_refused(self):
        good = json.loads(dump_item(WorkItem("item-001", "Garden"), "1"))
        bad = [{**good, "schema_version": True}, {**good, "schema_version": 2},
               {**good, "unexpected": 1}, {**good, "revision": "01"},
               {**good, "value": {"title": "Garden", "done": 1}},
               {**good, "value": {"title": "Garden"}}, {**good, "key": "../item"}]
        for data in bad:
            with self.subTest(data=data), self.assertRaises(ValueError):
                load_item(json.dumps(data))

    def test_failed_save_propagates_without_a_committed_receipt(self):
        class DeniedHost(MemoryHost):
            async def save(self, *args):
                raise PermissionError("Storage unavailable.")
        host = DeniedHost()
        with self.assertRaises(PermissionError):
            asyncio.run(save_item(host, WorkItem("item-001", "Garden"), "1", 1))
        self.assertEqual(host.values, {})

    def test_reload_refuses_a_different_domain_key(self):
        host = MemoryHost()
        host.values["item-001"] = dump_item(WorkItem("item-002", "Garden"), "1")
        with self.assertRaises(ValueError):
            asyncio.run(reload_item(host, "item-001", 1))
