# Shared application contracts, version 1

These are composition requirements for new adapters, not changes to existing
library APIs. The [fixtures](contracts/v1.json) are finite examples checked by
`python scripts/check_contracts.py`. Each implementing owner must test its
mapping before declaring support. Unknown profile or major contract versions
are refused before opening resources. Additive optional fields require an
explicit minor-profile revision; consumers must not silently widen admission.

## Profiles and lifecycle

| Profile | Runtime and resources | Ownership and failure behavior |
| --- | --- | --- |
| `cpython-service/1` | CPython 3.14+, one host, local relational SQLite, native ASGI HTTP | Application owns configuration, database and API construction. Start storage/migrations before accepting requests. Stop admission, drain bounded work, close API tasks, then storage. Failed startup unwinds already-created resources in reverse order. |
| `track-b-local/1` | Qualified pocket-python workload with granted view/input and durable storage adapters | A session owns Python state, tasks, callbacks, handles and generations. Acquire grants explicitly; denied/unavailable storage is a visible unsaved state. Stop invalidates generations, cancels/drains owned work and releases callbacks/listeners/handles. |
| `connected-browser/1` | Qualified browser workload plus an explicitly selected service | Browser owns pending edits and requests; service owns authorization and committed state. REST/WS require separate grants, endpoint/origin configuration and credentials supplied by the application. Disconnect preserves edits and marks remote state uncertain until resync. |

No profile is implemented merely by naming it. CA-03 assembles the service;
CA-06/CA-07 qualify and accept the browser workload. Base package import has no
I/O or optional imports. A selected integration must declare a tested package
range (or immutable development revision), Python floor and optional extra in
its owner. Missing extras/incompatible versions fail before resource creation;
there is no automatic driver, credential, listener or service selection.

Configuration is explicit and application-owned: profile/version, model
registry, local database path, bounded query/work queues and timeouts; browser
configuration adds granted capabilities, session and generation ownership.
Secrets do not belong in fixtures, URLs, error values or compatibility receipts.

## Values, identities and revisions

- A resource has a named collection, an application `key`, a `revision` and
  typed `value`. The pilot uses `work_items` with `title` and `done` fields.
  The key is immutable, case-sensitive ASCII matching
  `[A-Za-z0-9][A-Za-z0-9._-]{0,127}`. Other key profiles need separate adoption.
- Storage envelope UUIDs are internal storage identities, separate from domain
  keys. UUID assignment or reuse cannot rename a domain resource. Neither an
  envelope UUID nor an API transport correlation ID substitutes for its key.
- Revisions are opaque strings to wire consumers. The initial SQLite mapping
  uses canonical positive decimal integers from 1 through 9223372036854775807,
  serialized as strings to avoid JavaScript precision loss. A successful
  replacement increments once; overflow fails without mutation. Create starts
  at `"1"`. Replace and delete require an expected revision. A missing key is
  `not_found`; an existing key with another revision is `revision_conflict`.
  Recreating a deleted key requires a new resource incarnation; the initial
  storage owner must choose tombstones or prohibit key reuse before acceptance.
- Values are finite JSON: null, booleans, strings, safe integers (absolute
  value <= 9007199254740991), finite floats, arrays and string-keyed objects.
  The baseline envelope is at most 65536 UTF-8 bytes and 16 container levels.
  A narrower model/transport limit takes precedence. No implicit string/native
  coercion, non-finite number, dynamic model import or unknown model field.
- Storage schema history, codec payload schema version, domain revision,
  contract version and render-binding generation are independent counters.
  Incrementing a UI generation never changes a domain revision.

## Validation, errors and visibility

Validation checks trusted models at load/write boundaries. Defaults are
model-owned; a missing field differs from an explicit null. New adapters use
the supported strict Enforce Type profile without replacing existing codecs.
HTTP identities, writable/readable fields, authorization and immutable keys
remain owned by the API/application. A validator accepting a value never grants
permission to write or expose it.

The logical error shape is `code`, a fixed value-free `message`, and `issues`.
An issue has a string/integer path and a stable code; paths use public model
field names and zero-based array indexes. Redact hidden field paths as well as
values for unauthorized callers. Do not include inputs, database statements,
credentials or exception text. `request_id` is transport-only correlation and
must not become a domain key. The fixtures include field and non-field errors.

| Logical code | Proposed HTTP mapping | State guarantee |
| --- | --- | --- |
| `validation_error` | 422 | No mutation |
| `not_found` | 404 | No mutation; access policy may deliberately conceal existence |
| `revision_conflict` | 409 | Prior committed value remains; caller explicitly refreshes/merges |
| `already_exists` | 409 | Existing row unchanged |
| `unauthenticated` / `forbidden` | 401 / 403 | Access owner controls challenge and concealment policy |
| `unavailable` | 503 | Outcome must be reconciled if dispatch/commit may already have happened |

Existing expose_api HTTP behavior stays authoritative until API-STORE-02 maps
these contracts. API-AUTH-01 owns principal resolution, record access, origin
and credential policies. No sensitive-data reference profile is accepted before
that decision. Browser field visibility applies equally to REST and events.

## Commit, events and recovery

The event fixture is a **proposal**, not an implemented WebSocket protocol.
API-WS-01 owns final transport fields, authentication, bounds and serialization;
API-WS-02 owns cross-process delivery. An event is published only after the
domain transaction commits. Rollbacks emit nothing. A publish failure cannot
turn an already committed write into a reported rollback.

Proposed change identity is an event ID plus collection/key/revision; `deleted`
has no value. Session IDs, subscription IDs, request IDs and render generations
are transport-only fields, never domain revisions. Clients discard stale
generations and duplicate events, and do not replace a newer revision with an
older one. The initial recovery proposal is a fresh bounded REST snapshot on
reconnect or queue overflow, followed by explicit subscription synchronization;
durable replay is not promised. API-WS-01 must close snapshot/subscription races
before connected acceptance. Sharing SQLite does not deliver events to workers.

Browser save cancellation before dispatch leaves state unchanged. Cancellation
after dispatch has an uncertain outcome until a receipt or reload reconciles
it. A late completion for an old generation cannot overwrite current edits or
claim that committed data rolled back. Connected UI preserves in-progress input,
focus and field errors, and requires explicit conflict resolution on stale saves.

## Remaining owning decisions

| Boundary | Owner / next contract |
| --- | --- |
| Relational names, scalar mappings, keys, indexes, parameterized queries, detached values and pagination | [BP-SQL-01](https://github.com/wispsy/backpack/issues/17) |
| Transactions, revisions, nesting and async cancellation/connection ownership | [BP-TXN-01](https://github.com/wispsy/backpack/issues/19), [BP-ASYNC-01](https://github.com/wispsy/backpack/issues/20) |
| Migration namespaces, verified backup and startup locking | [BP-MIG-01](https://github.com/wispsy/backpack/issues/22), [Pretty Notebook inventory](https://github.com/wispsy/pretty-notebook/issues/186) |
| PostgreSQL driver/version and isolation | [BP-PG-01](https://github.com/wispsy/backpack/issues/24) |
| Browser persistence adapter, grant/value closure and actual runtime prerequisites | [CA-06](https://github.com/wispsy/compose_application/issues/6), [Track B](https://github.com/wispsy/pocket-python/issues/601) |
| Production hosting, session routing and event access | [SUI-HOST-01](https://github.com/wispsy/spatial_ui/issues/11), [API-AUTH-01](https://github.com/wispsy/expose_api/issues/12) |

No external service, broker, browser SQL engine or synchronized package release
is selected. The optional Enforce Type/API parity investigation remains separate.
