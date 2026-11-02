# Cohesion Block A

## Purpose

Build optional composition of useful, independent Python libraries into web
applications and browser-local applications. Each library retains its own
repository, public API, versioning and release lifecycle. `compose_application`
owns application assembly, reference applications and integration acceptance.

The first storage profile is relational SQLite. PostgreSQL follows after the
model, transaction and query contracts have been exercised. pocket-python is a
required application target through its existing Track B roadmap.

## Ownership and dependency direction

| Project | Owns |
| --- | --- |
| `backpack-store` | Typed record storage, relational application models, storage identity, constraints, queries, transactions, payload evolution and database migrations |
| `enforce_type` | Compiled validation and supported Python/JSON value conversion |
| `expose_api` | REST resources, HTTP serialization and errors, access-policy integration, API documentation, event/subscription protocols and native ASGI transport |
| `spatial_ui` | Components, spatial layout, typed input, rendering, session state and transport-independent interaction |
| `compose_application` | Selected application profiles, explicit assembly, reference applications and cross-package compatibility evidence |
| pocket-python Track B | Python-owned application state, awaited host capabilities, browser input/rendering, durable save/reload and teardown |
| Pretty Notebook | Its application schema, notebook ownership, permissions, publication rules and consumer-level migration acceptance |

An optional `expose_api` adapter consumes Backpack Store's public interfaces.
An optional `spatial_ui` adapter consumes an explicit API/transport contract.
`compose_application` consumes those packages; they do not depend on it.
No library needs the integration repository for standalone use or testing.

Selected application profiles declare the dependencies they actually use.
Importing the base composition package must not import optional libraries,
choose a database, start a thread, open a listener or perform network I/O.
Optional extras and new drivers are introduced with their implementing tasks.

## Names and validation

Use Backpack Store as the canonical product name, `backpack-store` as the
distribution name and `backpack_store` as the Python import. A repository-slug
rename is a separate migration decision; preserve existing release identities.

Use `enforce_type` as the preferred validation implementation for new Backpack
application models. Begin with an optional codec using the existing public
check/load/dump operations. Preserve supported existing codecs. Stored type names
must never cause dynamic imports.

Backpack currently supports Python 3.11+, while the validation adapter and
composition profile require Python 3.14+. The initial adapter keeps that boundary
explicit. A later change to Backpack's base Python requirement needs its own
compatibility decision. Do not rely on unreleased validation features without
an explicitly qualified source/version profile.

Validation owns values and conversion. Identity immutability, field visibility,
authorization, transaction boundaries and persistence remain owned by the
relevant application/API/storage layer. Sharing a validator must preserve those
policies and existing error contracts.

## Storage development

Backpack's current SQLite backend persists typed JSON records with revisions,
provenance, tags and payload migrations. Relational application storage adds
explicit model-to-table mappings, keys, constraints, indexes and parameterized
bounded queries while keeping that record interface supported.

Define domain keys separately from storage envelope UUIDs. Specify detached
return values, stable ordering, pagination, optimistic conflicts and missing-row
behavior. Keep database schema versions, model payload versions and wire
protocol versions independent.

Provide transaction-owned atomic updates and a unit of work for multiple
operations. Specify connection/thread ownership and async cancellation before
adapting synchronous SQLite operations into asynchronous resource APIs. Moving
each call to an arbitrary thread is insufficient for an owned connection.

Adopt a bounded, single-host SQLite profile with explicit journal mode, timeouts,
foreign-key enforcement, startup/migration ownership and backup behavior. Test
real processes, simultaneous startup, competing writes, stale revisions and
restart. More workers do not promise more concurrent SQLite writers.

PostgreSQL will use an optional, explicitly selected driver and a separately
tested backend profile. Storage contracts distinguish shared guarantees from
backend-specific isolation and deployment behavior.

## Pretty Notebook extraction

Use the existing web application's migration, backup and worker tests as
evidence. Inventory Tortoise coupling, SQLite schema evolution, process locks,
database/file publication ordering and cache refresh behavior before extraction.

Extract reusable database facilities first: ordered migration history,
transactional schema changes, consistent private backup snapshots and
cross-process startup coordination. Keep application-specific schemas and
filesystem transaction policy in the consumer. Port supporting tests with each
facility, then migrate one narrow consumer with a documented rollback path.
Preserve the currently supported one-host, one-database worker profile until
fresh evidence supports a broader profile.

## REST, UI and live events

Start with persistent REST resource operations and typed form validation.
Define shared identities, revisions, error codes and correlation/version fields
before introducing live updates. Native ASGI is the service integration seam;
the bundled development servers keep their existing scope.

WebSocket contracts must specify authorization, origin policy, queue bounds,
cancellation, disconnect handling, ordering, duplicates, reconnect and resync.
Publish change events after successful commits. State whether durable replay
or a fresh REST snapshot recovers missed events. Delivery across processes
requires an explicit implementation; sharing a database is not sufficient.

HTTP field visibility and record access policies also apply to event payloads
and subscriptions. A reference application with sensitive records depends on
an adopted identity and record-access contract.

## Runtime profiles

| Profile | Application behavior | Persistence and transport |
| --- | --- | --- |
| CPython service | Python domain models, API resources and server-side UI behavior | Local relational SQLite first; PostgreSQL later; ASGI HTTP/WebSocket hosting |
| Track B browser-local | Python-owned state, typed input/rendering, durable save/reload and restart | Explicitly granted bounded browser storage/view capabilities |
| Connected browser | Browser application using local state and an optional service | Granted REST/WebSocket capabilities with explicit failures, cancellation and recovery |

Track B is owned by [pocket-python #601](https://github.com/outside-labs/pocket-python/issues/601).
Language, await/host semantics and package qualification retain their existing
owners. Probe real application source and entry points, including t-strings,
dataclasses, typing/reflection, JSON and async behavior. Record original source,
dependency closure, runtime profile and host grants. Qualify reduced source
separately when applicable.

Browser-local storage uses a declared host adapter. Running the CPython
`sqlite3` extension in a browser is not implied. A browser SQL engine is a
separate backend decision. Browser support is accepted through actual view/save,
reload/recovery, denied/stale capability, cancellation and teardown cases.

## Milestones and completion

| Phase | Goal | Completion evidence |
| --- | --- | --- |
| A0 | Architecture and contract adoption | Owned contracts, finite tasks, dependency direction and explicit open decisions |
| A1 | Application storage | Validated relational SQLite models, queries, transactions, migrations and concurrency; separately qualified PostgreSQL follow-up |
| A2 | Persistent APIs | Conforming optional storage adapter, revision/access rules and generated API documentation |
| A3 | Interactive application transport | Typed inputs, ASGI integration, WebSockets and delivery/recovery across workers |
| A4 | Reference composition | Working persistent REST/UI/live application and Track B browser-local view/save workload |
| A5 | Compatibility and release evidence | Supported installed package combinations, upgrades, concurrency, browser behavior and runtime qualification |

Compatibility work starts in A0 and accompanies every phase. A5 assembles the
evidence; it is not the first time compatibility is checked. Proposed 0.2/0.3
targets are candidate scopes for the relevant libraries, not synchronized
version requirements or publication approvals.

A small reference application should prove create, list, edit and delete,
field validation, persistence after restart, stale-update rejection, independent
browser sessions and later live updates. Its browser-local variant must save,
reload, recover and stop cleanly. Application templates/scaffolding follow
demonstrated repeated assembly needs.

The Project and owning issues record execution state. This charter records
product architecture and adopted boundaries. Publication, deployment, new
external services and repository renames retain their own decisions.
