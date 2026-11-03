import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from compose_application.reference import WorkItem, _exchange, accept_reference, reference_application

try:
    from expose_api import serve
    from expose_api.backpack import BackpackStore
except ImportError:
    BackpackStore = None


class WorkItemTests(unittest.TestCase):
    def test_invalid_domain_values_are_refused(self):
        for values in (("../item", "Garden", False), ("item", "", False), ("item", "x" * 201, False),
                       ("item", "\ud800", False), ("item", "Garden", 1)):
            with self.subTest(values=repr(values)), self.assertRaises(ValueError):
                WorkItem(*values)


@unittest.skipIf(BackpackStore is None, "optional service profile not installed")
class ReferenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_http_process_restart_acceptance(self):
        result = await accept_reference()
        self.assertEqual(result["checks"], 16)
        self.assertTrue(result["process_restart"])
        self.assertTrue(all(phase["passed"] for phase in result["phases"]))

    async def test_concurrent_checked_requests_and_precondition_admission(self):
        with TemporaryDirectory() as directory:
            async with reference_application(Path(directory) / "items.sqlite3") as service:
                async with serve(service.app, port=0) as server:
                    port = server.sockets[0].getsockname()[1]
                    self.assertEqual((await _exchange(port, "POST", "/work-items", data={"key": "a", "title": "Garden"}))[0], 201)
                    responses = await asyncio.gather(*[_exchange(port, "PATCH", "/work-items/a", data={"title": title}, revision="1")
                                                       for title in ("First", "Second")])
                    self.assertEqual(sorted(response[0] for response in responses), [200, 409])
                    for headers in (("If-Match: *",), ('If-Match: "01"',), ('If-Match: "2"', 'If-Match: "2"')):
                        response = await _exchange(port, "DELETE", "/work-items/a", headers=headers)
                        self.assertEqual(response[0], 400)
                    fetched = await _exchange(port, "GET", "/work-items/a")
                    self.assertEqual(fetched[1]["etag"], '"2"')
                    self.assertIn(fetched[2]["title"], {"First", "Second"})
