# CPython service profile

Install the selected checkout with `uv sync --locked --extra service`.
The base package has zero runtime requirements and imports without optional
packages or I/O. The `service` extra pins unreleased Expose API adapter source
to `aef200defd2514c38e3857f6278ea45aa577e369`, transitively using Backpack
`54f5a1e883fcc32f8d87cc553dc83dae0434300d` and published Enforce Type 0.1.0.
Published Expose API/Backpack 0.1.0 alone does not supply these development APIs.
Package versions remain independent; this is an explicitly qualified source
profile rather than a claim about those released versions.

```python
import asyncio
from dataclasses import dataclass
from pathlib import Path
from compose_application import ServiceConfig, application

@dataclass
class WorkItem:
    key: str
    title: str
    done: bool = False

async def main():
    config = ServiceConfig(
        WorkItem, Path("work-items.sqlite3"), namespace="work_items",
        table="app_work_items", type_key="example.work_item", id_field="key",
        resource_path="/work-items", public=True,
    )
    async with application(config) as service:
        item = await service.resource.create({"key": "item-001", "title": "Garden"})
        print(item.title)

if __name__ == "__main__":
    asyncio.run(main())
```

The synthetic example explicitly selects public access. Real applications must
supply their own `authorize` callback and chosen identity/access contract before
using sensitive records. No credential source or identity provider is selected.
The model is a trusted scalar dataclass in the shared storage/API intersection,
with a bounded immutable string key and finite scalar values. Unknown schema
versions or changed registrations fail closed; this initial assembly performs
only explicit initial schema registration, never an implicit upgrade.

## Ownership

`ServiceConfig` selects exactly `cpython-service/1` and explicit storage names,
database path, route, access policy, queue capacity, timeout and body size.
Construction opens no files. Missing extras, incompatible versions and missing
adapter capabilities fail before opening storage. Existing released versions
sharing a version number are still refused if they lack the qualified APIs.

Enter `application(config)` to open the async store and build the typed resource
and native ASGI app. The context yields `service.store`, `service.resource` and
`service.app`. Exit closes the owned worker and connection, including failed
construction after storage opens. Close is repeatable and finishes accepted
cleanup before propagating caller cancellation. Application subclasses may
explicitly select `store_type=...` to extend the qualified adapter while keeping
its public contract; no backend is discovered implicitly.

The caller owns HTTP admission. Nest a public `expose_api.serve(service.app)`
context **inside** the application context, then drain/close the listener before
exiting the application context. Alternatively, an ASGI host may own that outer
lifecycle explicitly. Do not continue sending requests after closing storage.
No listener starts merely by importing, constructing configuration or opening
this context. A service stays in its opening event loop/process; construct a
separate service in each worker. Accepted write cancellation retains Backpack's
outcome receipt; reconcile it or reload before retrying.

The accepted deployment profile is one host and local SQLite WAL. Before
changing code/schema, stop services and retain a complete version-matched
verified checkpoint. Application/domain files and migration selection remain
user-owned. Release publication and hosted deployment have separate gates.

## Verification

`python scripts/check_distribution.py --service` installs each wheel/source
artifact outside the checkout. It verifies base isolation first, then installs
the pinned optional profile and runs lifecycle, failed-startup, canceled-close
and reopen tests. CI runs this profile on Linux, macOS and Windows with Python
3.14. Track B remains separately qualified by its existing prerequisite probes.
