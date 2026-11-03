# Shared contract register

The [version 1 application contracts](application-contracts-v1.md) adopt the
shared profiles, identities, revision/error representation and recovery rules.
Their [finite fixtures](contracts/v1.json) are executable contract examples.
The register below names the remaining owner-specific implementation contracts.
The implementation queue is in [the Project](https://github.com/orgs/outside-labs/projects/18).

| Boundary | Adopted direction | Contract work before implementation |
| --- | --- | --- |
| Package composition | Independent libraries; optional adapters; explicit application profiles | Profile selection, configuration, dependency/version bounds, lifecycle ownership and missing-extra errors |
| Validation | Prefer `enforce_type` for new storage models; start with an optional adapter | Supported type intersection, strict check/load/dump parity, defaults, unknown fields, error mapping and Python floor |
| Identity | Domain identity and storage envelope UUID are separate concepts | Key types, uniqueness, stable lookup/mapping, immutable identities and migration of keys |
| Revisions | Checked writes expose meaningful conflict behavior | Revision representation, conditional request mapping and whether deletion requires an expected revision |
| Relational models | Explicit registration and model-to-table schema | Supported scalar types, nullability, defaults, primary/foreign keys, unique constraints, indexes and schema naming |
| Queries | Bounded, parameterized, typed operations | Filter operators, sorting, stable pagination, concurrent-page semantics, relation loading and unsupported-query errors |
| Transactions | Atomic transforms and multi-operation units of work | Isolation, nesting/savepoints, rollback, callback side effects, async connection ownership and cancellation outcomes |
| Migrations | Ordered history, preserved unknown versions, transactional changes and verified backup | Namespace ownership, upgrade locking, integrity validation, failure recovery and consumer migration policy |
| HTTP resources | Existing `Store[T]` and resource behavior provide the API baseline | Async adapter conformance, detached values, ordering, error mapping, field visibility and access policy |
| Live events | Versioned typed payloads published after commit | Event identity/revision, authorization, ordering, duplicates, replay/resync, queue bounds and cross-process delivery |
| Spatial sessions | Explicit component/session ownership and typed input | Form payloads, validation display, focus preservation, stale events, async callbacks and session routing across workers |
| Browser application | Track B owns state and bounded host capabilities | Actual syntax/library qualification, grants, durable storage, cancellation, stale completions and teardown |

## Existing owning contracts

- [API Store protocol](https://github.com/outside-labs/expose_api/blob/main/src/expose_api/stores.py)
- [API SQLite contract issue](https://github.com/outside-labs/expose_api/issues/6)
- [API Backpack adapter issue](https://github.com/outside-labs/expose_api/issues/10)
- [API WebSocket contract issue](https://github.com/outside-labs/expose_api/issues/8)
- [API identity and record access issue](https://github.com/outside-labs/expose_api/issues/12)
- [Spatial typed input issue](https://github.com/outside-labs/spatial_ui/issues/7)
- [Spatial hosting/transport issue](https://github.com/outside-labs/spatial_ui/issues/11)
- [Pretty Notebook server-state guarantees](https://github.com/outside-labs/pretty-notebook/blob/main/docs/server-state.md)
- [pocket-python application engine](https://github.com/outside-labs/pocket-python/issues/601)

## Decision boundaries

The [protected native live reference](live-reference.md) adopts the API's
read-only single-record snapshot protocol, opaque cursors, bounded polling and
fresh-snapshot resync. This concrete profile carries no write revision in an
event and does not adopt the early proposed event fixtures as a wire format.
Checked REST revisions, remote cursors, UI render versions and connection
generations remain separate. Credentials and current record policies are
application-owned; live UI admission preserves dirty edits until explicit
refresh/merge. The exact qualified source revisions are in the compatibility
register.

Select the concrete PostgreSQL driver, browser-local persistence adapter and
event delivery implementation in their owning tasks. No external broker,
browser SQL engine, ORM runtime or mandatory web dependency is selected by this
register. Compare the shared storage contract against both SQL backends before
promising equivalent isolation or SQL feature support.

The existing `enforce_type`/`expose_api` assessment remains an optional parity
investigation. Selecting validation for Backpack does not replace API-specific
identity, visibility or serialization rules. JSON Schema/OpenAPI generation
must describe actual runtime behavior for each supported model profile.

## Tabular sources

[Tabular interfaces version 1](tabular-v1.md) defines independent identities,
scalar/query limits, detached snapshots and checked single-cell outcomes.
[Finite fixtures](contracts/tabular-v1.json) are checked without integration imports.
