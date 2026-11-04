# Cohesion Block A roadmap

Read current status and readiness in the [organization Project](https://github.com/orgs/wispsy/projects/18).
The following index records the task breakdown and owning issues. Candidate
targets describe proposed scope; package versions and publication remain independent.

## Optional compiled validation

The selected expose-api adapter reuses Enforce Type's published value operations
under the existing resource model and policy contracts. Its finite task sequence
is [the assessment](https://github.com/wispsy/enforce_type/issues/14),
[explicit schema selection](https://github.com/wispsy/expose_api/issues/52),
[compiled values](https://github.com/wispsy/expose_api/issues/53),
[HTTP/access/persistent events](https://github.com/wispsy/expose_api/issues/54),
[installed artifacts](https://github.com/wispsy/expose_api/issues/55), and
[service composition](https://github.com/wispsy/compose_application/issues/36).
The [held-snapshot acceptance repair](https://github.com/wispsy/expose_api/issues/59)
has its own issue. The [separate service selection](validation-reference.md)
preserves existing reference sources and base package independence.

## First rolling batch

The first batch establishes contracts and reusable foundations before the
dependent relational, API and UI implementations. Begin with Ready tasks;
take the relational contract after the shared contract prerequisite is accepted.

- [CA-02: Adopt shared application profiles and wire contracts](https://github.com/wispsy/compose_application/issues/2) — `compose_application`.
- [BP-NAME-01: Make Backpack Store the canonical product name](https://github.com/wispsy/backpack/issues/15) — `backpack`.
- [PN-STORAGE-01: Inventory reusable web storage and preserve extraction acceptance](https://github.com/wispsy/pretty-notebook/issues/186) — `pretty-notebook`.
- [BP-VAL-01: Add an optional Enforce Type model codec](https://github.com/wispsy/backpack/issues/16) — `backpack`.
- [BP-SQL-01: Adopt relational SQLite model and query contracts](https://github.com/wispsy/backpack/issues/17) — `backpack`.

## Ordered register

| Order | Task and owning issue | Phase | Candidate target | Prerequisites |
| --- | --- | --- | --- | --- |
| 1 | [CA-01: Establish package foundation and Cohesion Block A charter](https://github.com/wispsy/compose_application/issues/1) | A0 | Foundation | — |
| 2 | [CA-02: Adopt shared application profiles and wire contracts](https://github.com/wispsy/compose_application/issues/2) | A0 | Foundation | — |
| 3 | [BP-NAME-01: Make Backpack Store the canonical product name](https://github.com/wispsy/backpack/issues/15) | A0 | Foundation | — |
| 4 | [PN-STORAGE-01: Inventory reusable web storage and preserve extraction acceptance](https://github.com/wispsy/pretty-notebook/issues/186) | A0 | Foundation | — |
| 5 | [CA-06: Define the Track B application workload and prerequisite probes](https://github.com/wispsy/compose_application/issues/6) | A0 | Track B | [CA-02](https://github.com/wispsy/compose_application/issues/2) |
| 10 | [BP-VAL-01: Add an optional Enforce Type model codec](https://github.com/wispsy/backpack/issues/16) | A1 | Foundation | — |
| 11 | [BP-SQL-01: Adopt relational SQLite model and query contracts](https://github.com/wispsy/backpack/issues/17) | A1 | Foundation | [CA-02](https://github.com/wispsy/compose_application/issues/2) |
| 12 | [BP-SQL-02: Implement registered relational SQLite models and keyed CRUD](https://github.com/wispsy/backpack/issues/18) | A1 | 0.2 candidate | [BP-VAL-01](https://github.com/wispsy/backpack/issues/16), [BP-SQL-01](https://github.com/wispsy/backpack/issues/17) |
| 13 | [BP-TXN-01: Provide transaction-owned atomic updates and units of work](https://github.com/wispsy/backpack/issues/19) | A1 | 0.2 candidate | [BP-SQL-02](https://github.com/wispsy/backpack/issues/18) |
| 14 | [BP-ASYNC-01: Define and implement an owned asynchronous storage facade](https://github.com/wispsy/backpack/issues/20) | A1 | 0.2 candidate | [BP-TXN-01](https://github.com/wispsy/backpack/issues/19) |
| 15 | [BP-QUERY-01: Implement bounded typed relational queries and indexes](https://github.com/wispsy/backpack/issues/21) | A1 | 0.2 candidate | [BP-SQL-02](https://github.com/wispsy/backpack/issues/18) |
| 16 | [BP-MIG-01: Extract reusable ordered SQLite migrations and verified backups](https://github.com/wispsy/backpack/issues/22) | A1 | 0.2 candidate | [PN-STORAGE-01](https://github.com/wispsy/pretty-notebook/issues/186), [BP-TXN-01](https://github.com/wispsy/backpack/issues/19) |
| 17 | [BP-CONC-01: Qualify the SQLite application profile across real processes](https://github.com/wispsy/backpack/issues/23) | A1 | 0.2 candidate | [BP-MIG-01](https://github.com/wispsy/backpack/issues/22), [BP-ASYNC-01](https://github.com/wispsy/backpack/issues/20) |
| 18 | [PN-STORAGE-02: Migrate one web storage consumer to Backpack Store facilities](https://github.com/wispsy/pretty-notebook/issues/187) | A1 | 0.2 candidate | [PN-STORAGE-01](https://github.com/wispsy/pretty-notebook/issues/186), [BP-MIG-01](https://github.com/wispsy/backpack/issues/22), [BP-CONC-01](https://github.com/wispsy/backpack/issues/23) |
| 20 | [API-STORE-02: SQLite persistence contract](https://github.com/wispsy/expose_api/issues/6) | A2 | 0.2 candidate | [CA-02](https://github.com/wispsy/compose_application/issues/2), [BP-SQL-01](https://github.com/wispsy/backpack/issues/17), [BP-TXN-01](https://github.com/wispsy/backpack/issues/19) |
| 21 | [API-BP-01: Optional Backpack Store adapter](https://github.com/wispsy/expose_api/issues/10) | A2 | 0.2 candidate | [API-STORE-02](https://github.com/wispsy/expose_api/issues/6), [BP-VAL-01](https://github.com/wispsy/backpack/issues/16), [BP-ASYNC-01](https://github.com/wispsy/backpack/issues/20) |
| 22 | [API-AUTH-01: Authentication and record access contract](https://github.com/wispsy/expose_api/issues/12) | A2 | 0.2 candidate | [CA-02](https://github.com/wispsy/compose_application/issues/2) |
| 23 | [API-DOC-01: Generated OpenAPI](https://github.com/wispsy/expose_api/issues/7) | A2 | 0.2 candidate | [CA-02](https://github.com/wispsy/compose_application/issues/2), [API-BP-01](https://github.com/wispsy/expose_api/issues/10) |
| 24 | [ET-API-01: Assess optional expose-api adapter](https://github.com/wispsy/enforce_type/issues/14) | A2 | Later | — |
| 30 | [SUI-INPUT-01: Define typed form events and editing behavior](https://github.com/wispsy/spatial_ui/issues/7) | A3 | 0.2 candidate | [CA-02](https://github.com/wispsy/compose_application/issues/2) |
| 31 | [SUI-HOST-01: Select a production transport and concurrency policy](https://github.com/wispsy/spatial_ui/issues/11) | A3 | 0.2 candidate | [CA-02](https://github.com/wispsy/compose_application/issues/2) |
| 32 | [SUI-API-01: Add an optional REST resource binding](https://github.com/wispsy/spatial_ui/issues/22) | A3 | 0.2 candidate | [SUI-INPUT-01](https://github.com/wispsy/spatial_ui/issues/7), [API-BP-01](https://github.com/wispsy/expose_api/issues/10), [CA-02](https://github.com/wispsy/compose_application/issues/2) |
| 33 | [API-WS-01: Typed events and WebSockets](https://github.com/wispsy/expose_api/issues/8) | A3 | 0.3 candidate | [CA-02](https://github.com/wispsy/compose_application/issues/2), [API-AUTH-01](https://github.com/wispsy/expose_api/issues/12), [API-BP-01](https://github.com/wispsy/expose_api/issues/10) |
| 34 | [API-WS-02: Deliver committed resource events across workers with recovery](https://github.com/wispsy/expose_api/issues/24) | A3 | 0.3 candidate | [API-WS-01](https://github.com/wispsy/expose_api/issues/8), [BP-TXN-01](https://github.com/wispsy/backpack/issues/19), [BP-CONC-01](https://github.com/wispsy/backpack/issues/23) |
| 35 | [SUI-WS-01: Add a bounded WebSocket application transport](https://github.com/wispsy/spatial_ui/issues/23) | A3 | 0.3 candidate | [API-WS-01](https://github.com/wispsy/expose_api/issues/8), [API-WS-02](https://github.com/wispsy/expose_api/issues/24), [SUI-API-01](https://github.com/wispsy/spatial_ui/issues/22), [SUI-HOST-01](https://github.com/wispsy/spatial_ui/issues/11) |
| 40 | [CA-03: Assemble explicit application profiles and lifecycle ownership](https://github.com/wispsy/compose_application/issues/3) | A4 | 0.2 candidate | [CA-02](https://github.com/wispsy/compose_application/issues/2), [API-BP-01](https://github.com/wispsy/expose_api/issues/10) |
| 41 | [CA-04: Build the persistent REST reference application](https://github.com/wispsy/compose_application/issues/4) | A4 | 0.2 candidate | [CA-03](https://github.com/wispsy/compose_application/issues/3), [BP-QUERY-01](https://github.com/wispsy/backpack/issues/21), [BP-CONC-01](https://github.com/wispsy/backpack/issues/23) |
| 42 | [CA-05: Add the typed spatial UI and live reference workflow](https://github.com/wispsy/compose_application/issues/5) | A4 | 0.3 candidate | [CA-04](https://github.com/wispsy/compose_application/issues/4), [SUI-API-01](https://github.com/wispsy/spatial_ui/issues/22), [SUI-WS-01](https://github.com/wispsy/spatial_ui/issues/23), [API-AUTH-01](https://github.com/wispsy/expose_api/issues/12) |
| 43 | [PP-APP-B: Application engine Track B](https://github.com/wispsy/pocket-python/issues/601) | A4 | Track B | Owning runtime issue |
| 44 | [CA-07: Accept the Track B browser-local view and save application](https://github.com/wispsy/compose_application/issues/7) | A4 | Track B | [CA-06](https://github.com/wispsy/compose_application/issues/6); accepted Track B capability slices |
| 50 | [PP-LIB-01: Qualify selected standard-library APIs](https://github.com/wispsy/pocket-python/issues/126) | A5 | Track B | Owning runtime issue |
| 51 | [PP-PKG-01: Certify bounded real pure-Python package uses](https://github.com/wispsy/pocket-python/issues/128) | A5 | Track B | Owning runtime issue |
| 52 | [CA-08: Maintain the installed-package and application compatibility matrix](https://github.com/wispsy/compose_application/issues/8) | A5 | 0.2 candidate | [CA-03](https://github.com/wispsy/compose_application/issues/3) |
| 60 | [BP-PG-01: Select the PostgreSQL driver and backend contract](https://github.com/wispsy/backpack/issues/24) | A1 | Later | [BP-QUERY-01](https://github.com/wispsy/backpack/issues/21), [BP-CONC-01](https://github.com/wispsy/backpack/issues/23) |
| 61 | [BP-PG-02: Implement and qualify the optional PostgreSQL backend](https://github.com/wispsy/backpack/issues/25) | A1 | Later | [BP-PG-01](https://github.com/wispsy/backpack/issues/24), [CA-08](https://github.com/wispsy/compose_application/issues/8) |
| 62 | [CA-09: Derive a project style from accepted reference applications](https://github.com/wispsy/compose_application/issues/9) | A4 | Later | [CA-04](https://github.com/wispsy/compose_application/issues/4), [CA-05](https://github.com/wispsy/compose_application/issues/5) |

## Runtime gates and later choices

CA-09's accepted-reference layout is implemented by focused project-generation
tasks: [STYLE-01](https://github.com/wispsy/compose_application/issues/22),
[STYLE-02](https://github.com/wispsy/compose_application/issues/23),
[STYLE-03](https://github.com/wispsy/compose_application/issues/24),
[STYLE-04](https://github.com/wispsy/compose_application/issues/25),
[STYLE-05](https://github.com/wispsy/compose_application/issues/26) and
[STYLE-06](https://github.com/wispsy/compose_application/issues/27).
The [reference project layout](reference-projects.md) compares the accepted
service/UI/live workflows and records their explicit selection, ownership,
repeat-request behavior and installed acceptance.

The REST binding is implemented through focused children of SUI-API-01:
[SUI-INPUT-02](https://github.com/wispsy/spatial_ui/issues/25),
[SUI-FORM-01](https://github.com/wispsy/spatial_ui/issues/26),
[SUI-FORM-02](https://github.com/wispsy/spatial_ui/issues/27),
[SUI-REST-01](https://github.com/wispsy/spatial_ui/issues/28),
[SUI-API-02](https://github.com/wispsy/spatial_ui/issues/29) and
[CA-UI-01](https://github.com/wispsy/compose_application/issues/16).
[API-BP-02](https://github.com/wispsy/expose_api/issues/28) owns the
transaction-validation repair discovered by their actual service acceptance.
The [UI reference profile](ui-reference.md) qualifies the CPython REST slice;
CA-05's live transport and hosting/authentication decisions retain their gates.

Runtime roadmap parents remain the canonical owners for interpreter work.
Composition consumes accepted capability slices and package profiles; it does
not wait for closure of the full Track A/Track B roadmaps. Each owning issue
retains its broader prerequisites. New missing runtime slices are filed there.

The optional Enforce Type/API assessment is related deferred work. Choosing
Enforce Type for Backpack does not require replacing API validation.

PostgreSQL follows accepted SQLite storage behavior and explicit driver
selection. Application scaffolding follows demonstrated reference workflows.
Concrete browser persistence, event delivery, hosting destinations, license
terms, releases and repository-slug changes keep their stated decision gates.
