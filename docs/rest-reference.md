# Persistent REST reference

This local synthetic work-item application composes Expose API validation/HTTP,
the Backpack relational SQLite adapter and the owned service lifecycle. Python
owns the domain rules and committed state. It uses the immutable development
dependencies in the [service profile](service-profile.md), not the published
0.1.0 packages alone. No identity or sensitive-data application is selected.

From this checkout:

```bash
uv sync --locked --extra service
uv run --frozen python -m compose_application.reference check
uv run --frozen python -m compose_application.reference serve \
  --database ./work-items.sqlite3 --port 8000
```

`check` uses its own temporary database and two independent Python processes.
It exercises actual loopback HTTP create/list/edit/delete, invalid and stale
writes, immutable keys, pagination and key tombstones. The second process
reopens the committed database, verifies exact state/revision, then deletes
using the current revision. It reports 16 checks as JSON and removes the
dedicated fixture afterward; it never opens the database passed to `serve`.
Once dependencies are installed this acceptance requires no internet access.

The development server binds to 127.0.0.1. While it runs, in another terminal:

```bash
curl --fail-with-body --include http://127.0.0.1:8000/work-items \
  --header 'Content-Type: application/json' \
  --data '{"key":"item-001","title":"Garden","done":false}'
curl --fail-with-body --include http://127.0.0.1:8000/work-items/item-001
curl --fail-with-body --include http://127.0.0.1:8000/work-items/item-001 \
  --request PATCH --header 'Content-Type: application/json' \
  --header 'If-Match: "1"' --data '{"done":true}'
curl --fail-with-body 'http://127.0.0.1:8000/work-items?offset=0&limit=10'
curl --fail-with-body --include http://127.0.0.1:8000/work-items/item-001 \
  --request DELETE --header 'If-Match: "2"'
```

Create and single-item GET/PATCH responses carry an ETag containing the exact
row revision, captured with the returned value. PATCH and DELETE require one
canonical quoted revision in `If-Match`; missing preconditions return 428,
malformed/duplicate headers return 400, and a stale revision returns 409 with
`revision_conflict`. Validation returns 422. Failed/stale requests preserve the
previous committed value. Read the current ETag before editing or deleting;
explicitly refresh/merge a stale edit. Revisions are decimal strings, distinct
from immutable application keys and internal storage UUIDs.

Keys use the shared 1–128 ASCII domain-key grammar. Titles have 1–200 Unicode
characters and valid UTF-8; done is an exact boolean. Bodies are bounded at
65536 bytes. Lists are key-ordered with offset 0–10000 and limit 1–1000; pages
under concurrent changes are independent committed views. Deleted keys remain
reserved, preventing an old revision from addressing a new resource incarnation.

The reference's explicit adapter subclass uses only public checked storage
methods. Per-request context keeps conditional mutations and response revisions
isolated across simultaneous requests. The API still owns writable fields,
identity validation, JSON parsing and HTTP errors. The application owns the
domain's ETag policy. Stop closes HTTP admission before draining the storage
worker; accepted canceled writes retain the backend's outcome-reconciliation
contract. No event transport or browser support is implied by this REST example.

The database is application state; preserve it across server restarts. This
profile initializes one explicitly owned schema and refuses changed/unknown
registrations. Before later upgrades, stop the server and retain a verified
database checkpoint plus matching code/dependencies. Do not run incompatible
old code against newer schema history. The example is public synthetic data;
production access control, hosted deployment and package publication retain
their separate decisions.
