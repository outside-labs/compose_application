# Tabular Interfaces implementation plan

This plan selects a generalized read-only and editable table interface across
Backpack Store, Headless Spreadsheets, Expose API, Spatial UI, Pretty Notebook
and Compose Application. It builds on Cohesion Block A.

The [Tabular Interfaces Project](https://github.com/orgs/outside-labs/projects/19)
and owning issues hold execution status, acceptance criteria and dependencies.
This document records architecture and delivery order. Proposed interfaces below
require their owning implementation tasks; they are not claims of shipped APIs.

## Intended outcome

An application can declare a table source and choose either:

1. A read-only table whose row sorting, text search, pagination and displayed
   column selection/order change its view while preserving source data.
2. An editable table that stages a cell change and saves it to the same durable
   row in Backpack Store with validation and an expected row revision.

“Frozen data” means the first, read-only mode. Frozen scrolling headers/columns
are not part of the selected first milestone.

The first complete example will list registered work-item records, sort by a
column, search for text, edit a visible cell, save it, clear the search, restart
the application and show that the intended record retained the edit. A second
browser with an older revision must receive a conflict while keeping its draft.

The design must also work without a browser: Headless Spreadsheets can consume
a registered Backpack source, query it and make checked scalar edits. Later
views and applications can reuse these source/query/edit boundaries.

## Readiness and inspected baseline

Planning snapshot: 2026-11-03. These are inspected main revisions, not synchronized
release versions. The current compatibility register remains authoritative for
which combinations have actually been qualified together.

| Repository | Inspected main | Existing foundation |
| --- | --- | --- |
| [compose_application](https://github.com/outside-labs/compose_application/tree/619505491e72716f90d6db7dc16df65436550275) | `6195054` | Persistent REST/UI/live references, explicit profiles, installed compatibility matrix and generated reference projects |
| [backpack](https://github.com/outside-labs/backpack/tree/696936ea2af46876bee61aefbf703a52edecc529) | `696936e` | Registered relational SQLite models, checked updates, bounded typed queries, owned async worker, migrations and snapshots |
| [headless_spreadsheets](https://github.com/outside-labs/headless_spreadsheets/tree/07c9ed36840c021b7c7bc49d7e7c90f7f1aa0283) | `07c9ed3` | Released typed cells, tables, live read-only views, filters/sorts, source-address mapping and escaped table writers |
| [expose_api](https://github.com/outside-labs/expose_api/tree/c20ce4aa3487d4913b56ff244a031f83de2df285) | `c20ce4a` | Optional relational Backpack adapter, checked updates, field/access policies, native ASGI and protected single-record live snapshots |
| [spatial_ui](https://github.com/outside-labs/spatial_ui/tree/9e473497febdc505e54ba25536b65b68722d264b) | `9e47349` | Typed forms, independent sessions, REST bindings, draft/conflict handling and native ASGI/browser qualification |
| [pretty-notebook](https://github.com/outside-labs/pretty-notebook/tree/2bfc586cfce7e982f73cbbb0215c99260388f73c) | `2bfc586` | Source-preserving typed Markdown parser, document table nodes, safe standalone HTML and notebook-specific rendering |

We can begin the CPython table work now. Block A's remaining
[browser-local application gate](https://github.com/outside-labs/compose_application/issues/7),
[public-hosting selection](https://github.com/outside-labs/spatial_ui/issues/11)
and [PostgreSQL profile](https://github.com/outside-labs/backpack/issues/24)
do not block the initial SQLite-backed table.

The existing spreadsheet view is not an interactive browser component. Its
membership/order stays fixed while source values can change; it is not an
immutable data snapshot. Its row index/A1 address is also not a durable database
identity. Existing API collection routes accept offset/limit, not a complete
table search/sort contract. Current protected WebSockets watch one record,
not arbitrary queried collections. These gaps have their own tasks below.

Markdown extraction can proceed alongside these foundations. It does not block
record-backed tables: Headless Spreadsheets already provides native escaped
Markdown/HTML output and the interactive component renders declared cell values.

## Ownership and dependency direction

| Owner | Responsibility |
| --- | --- |
| Headless Spreadsheets | Renderer-independent table/source snapshots, in-memory identity and query behavior, typed cell metadata and optional storage/document adapters |
| Backpack Store | Durable registered rows, keys/revisions, parameterized query/search, checked whole-row transactions, schema ownership and persistence lifecycle |
| Expose API | Opt-in schema/query/edit wire profile, authentication/access/visibility, redacted errors, OpenAPI and transport behavior |
| Spatial UI | Table component, per-session view state, input/focus/accessibility, drafts, request generations and explicit conflict recovery |
| Compose Application | Shared contract fixtures, selected dependency profiles, reference assembly and cross-package/browser/installed acceptance |
| Pretty Notebook | Extraction inventory, notebook adapters, source-authoritative behavior and consumer migration acceptance |
| Selected Markdown package, after decision | Generic document nodes/spans, bounded parsing and safe HTML/table rendering with attributed fixtures |

The base libraries remain independently useful. An optional Headless
Spreadsheets adapter consumes Backpack's public interfaces. API and UI bindings
consume their own declared contracts; they do not require Compose Application
or a notebook application. The UI's optional headless binding consumes public
snapshots, while its HTTP binding consumes the wire profile.

Shared contract documentation and finite fixtures do not make Compose
Application a runtime dependency. No new generalized table repository or
mandatory core dependency is needed for this first implementation. Optional
dependencies are declared only when their implementing task needs them.

The generic Markdown package remains a separate selection. No package name,
repository creation or dependency version is selected by this plan.

## Source and identity contract

Applications declare trusted schemas and map stable column IDs to registered
fields. Display labels and displayed column order remain independent of those
IDs. Capabilities state which columns are visible, sortable, searchable and
writable; client controls never grant authority.

A source identifies:

- The table/source instance and schema version.
- Columns, types, nullability and capabilities.
- Rows by a stable key, with a row revision for checked persistent writes.
- Detached page/snapshot values and continuation metadata.
- Explicit read/query/edit operations and ownership/close behavior.

Existing Table/TableView behavior stays compatible. A new detached snapshot
must be distinguished from the existing view's fixed membership with live
values. Source-instance IDs may be ephemeral in memory; durable adapters use
registered domain keys and never reconstruct them from the current view index.

Storage envelope UUIDs, domain row keys, row revisions, schema versions, query
cursors, request generations, UI render versions and connection generations
serve different purposes. One must not substitute for another.

## First scalar and persistence profile

The first durable profile uses application-declared flat registered models:

| Value | Initial persisted behavior |
| --- | --- |
| Text | Exact Unicode string, no implicit normalization |
| Boolean | Exact Boolean, distinct from integer |
| Integer | Portable existing JSON integer bounds |
| Number | Finite float under the existing model/codec rules |
| Null | Accepted only for explicitly nullable columns |
| Decimal, date, datetime, formulas, nested values | Available where already supported by Headless Spreadsheets; rejected by this first persistent binding |

Use the existing model registration, initialization and migration boundaries.
This is a reusable interface over declared data, not a user-controlled SQL or
database-schema editor. Column insertion/deletion, row creation/deletion,
dynamic schema changes and bulk paste are outside the first cell-edit scope.

No adapter may silently turn a Decimal into float, a date into an untyped string
or a formula into an executable expression. A later lossless codec/profile can
expand the persisted intersection. Existing native spreadsheet serialization
retains its wider fidelity.

## Query and read-only behavior

Sorting changes row order by declared columns; users can choose direction and,
within the adopted bounds, multiple keys. Define deterministic primary-key tie
breaking and explicit null placement. Displayed column selection/order never
moves stored fields or changes the registered schema.

The first search is literal case-sensitive Unicode substring search without
normalization. It searches up to eight declared searchable text columns using
OR, combined with the existing typed predicates using AND. Limit the term to
256 code points; empty search clears it. Percent, underscore, backslash, quotes
and SQL-shaped strings remain literal. Case-insensitive/indexed search can
follow an explicitly tested profile.

Adopt the existing storage ceilings of 16 predicates, three explicit sort fields
and 1,000 rows per page as upper bounds. The reference starts with a 50-row page.
Select finite request/cell/column/scan budgets in TAB-01 and enforce them at
each boundary. A result limit does not bound work spent scanning denied or
unindexed records; budget exhaustion must be explicit.

In-memory operations may process a complete bounded local table. Remote
operations query the declared dataset rather than silently sorting/searching
only the loaded page. Local and remote mode must be clear to the caller/user.

Cursors bind to the schema and normalized query and, at the API boundary, the
application/access scope. Query changes reset continuation. Every request
reapplies current authorization. A cursor never authorizes a row.

Existing keyset pagination under concurrent edits does not promise a frozen
multi-page snapshot. Document possible movement/duplication/omission and provide
explicit refresh/resync. Do not fetch every row to disguise missing query
support or expose hidden counts/fields.

View state belongs to the browser/session. Sorting, search and displayed column
choices preserve source values and revisions. Durable user view preferences
can be a later application concern.

## Cell edits and failure behavior

A persistent edit addresses table/source ID, durable row key, stable column ID
and expected row revision. An A1 coordinate or visual row number can help display
a location, but cannot be the persisted write target.

The UI captures identity and revision when editing starts. It stages a draft,
commits with Enter or Save, and cancels with Escape. View changes preserve the
draft and its identity, including when its row leaves the visible page; the UI
must retain an explicit way to save or discard that draft.

The API/storage path checks the current row, expected revision, writable field,
new scalar value, complete resulting model and current/proposed record access
inside one owned transaction. It reuses existing checked transforms. A failed
edit preserves all fields and revisions; a successful edit increments the row
revision once and returns committed projected values.

Two different-cell edits to the same row may conflict because revision scope is
the whole row. Preserve the draft, show current values when authorized and
offer explicit reload/reapply/discard. Do not automatically merge or retry a
write against a new revision.

Preserve distinctions among validation, unsupported type/query, read-only field,
missing/concealed row, revision conflict, unavailable storage and budget errors.
Error payloads remain value-free under the existing contracts.

A canceled or lost response does not prove rollback. An uncertain save requires
a fresh authoritative read before another edit/retry. Refuse late completions
after source/query/session changes. Do not execute formulas or change read-only
cell metadata through the scalar editor.

## Transport, sessions and accessibility

Extend the API through an explicitly opted-in tabular profile. Preserve the
existing resource routes and response shapes. Return public schema/capabilities,
bounded projected pages with keys/revisions and checked single-cell results.

Sort/search is allowed only over declared visible query fields. Record policies
apply before filling the visible page, with an explicit finite scan budget.
Credentials, origin checks, private responses and policy ownership retain their
existing native ASGI contracts.

The component renders escaped text, semantic table headers, clear sort state,
keyboard navigation, visible focus and labels. Include empty/loading/error,
pending/saved/invalid/conflict and uncertain-save states. Preserve search/editor
composition, focus and drafts; test phone/desktop widths and reduced motion.

Each session owns query state and request generations. Cancel superseded work
and discard stale results without losing edits. Cleanup releases callbacks,
listeners, requests and owned storage workers. The initial milestone supports
manual refresh; collection live updates require TAB-LIVE-01.

## Markdown extraction and document tables

Reuse [the existing MD-01 decision](https://github.com/outside-labs/headless_spreadsheets/issues/11).
The inventory covers nodes, spans, parser/dialect boundaries, safe rendering,
input/work budgets, fixture notices and notebook coupling in render context,
links, routes, icons, graphs, images and publication fingerprints.

Before implementation, select the independent distribution/import/repository,
license/provenance, Python floor, public API and extension/context contract.
The selected package receives its own implementation issue before code moves.
Preserve history/provenance and avoid maintaining duplicate generic parsers.

Move generic source-preserving bounded parsing and document table rendering;
retain notebook policies in Pretty Notebook adapters. Keep escaped standalone
HTML as default and trusted rendering explicit. Port the attributed CommonMark
corpus, table edge cases and adversarial limits, then qualify notebook adoption
and import compatibility/rollback.

Spreadsheet Table and document Table remain separate. An optional adapter
converts explicit display snapshots/documents. A Markdown table can provide
a read-only text source. Importing it into persistent typed rows requires an
explicit application mapping, column identity and key allocation.

Original Markdown stays authoritative. Sorting a view never rewrites notebook
source. Automatic source round-tripping, inferred types and notebook table
cell write-back are separate future features.

## Ordered owning issues

The Project also records native GitHub blocked-by relationships. Readiness is
advanced when the exact prerequisites merge, rather than waiting for closure
of broad parent roadmaps.

| Order | Task | Repository | Phase | Prerequisites |
| --- | --- | --- | --- | --- |
| 1 | [TAB-00](https://github.com/outside-labs/compose_application/issues/38) | `compose_application` | T0 Planning | — |
| 2 | [TAB-01](https://github.com/outside-labs/compose_application/issues/39) | `compose_application` | T1 Foundations | [TAB-00](https://github.com/outside-labs/compose_application/issues/38) |
| 3 | [HS-TAB-01](https://github.com/outside-labs/headless_spreadsheets/issues/17) | `headless_spreadsheets` | T1 Foundations | [TAB-01](https://github.com/outside-labs/compose_application/issues/39) |
| 4 | [BP-TAB-01](https://github.com/outside-labs/backpack/issues/37) | `backpack` | T1 Foundations | [TAB-01](https://github.com/outside-labs/compose_application/issues/39) |
| 5 | [API-TAB-01](https://github.com/outside-labs/expose_api/issues/66) | `expose_api` | T1 Foundations | [TAB-01](https://github.com/outside-labs/compose_application/issues/39) |
| 6 | [PN-MD-EXTRACT-01](https://github.com/outside-labs/pretty-notebook/issues/191) | `pretty-notebook` | T1 Foundations | [TAB-00](https://github.com/outside-labs/compose_application/issues/38) |
| 7 | [API-TAB-02](https://github.com/outside-labs/expose_api/issues/67) | `expose_api` | T2 Read-only | [API-TAB-01](https://github.com/outside-labs/expose_api/issues/66), [BP-TAB-01](https://github.com/outside-labs/backpack/issues/37) |
| 8 | [SUI-TAB-01](https://github.com/outside-labs/spatial_ui/issues/53) | `spatial_ui` | T2 Read-only | [HS-TAB-01](https://github.com/outside-labs/headless_spreadsheets/issues/17) |
| 9 | [SUI-TAB-02](https://github.com/outside-labs/spatial_ui/issues/54) | `spatial_ui` | T2 Read-only | [SUI-TAB-01](https://github.com/outside-labs/spatial_ui/issues/53), [API-TAB-02](https://github.com/outside-labs/expose_api/issues/67) |
| 10 | [TAB-02](https://github.com/outside-labs/compose_application/issues/40) | `compose_application` | T2 Read-only | [SUI-TAB-02](https://github.com/outside-labs/spatial_ui/issues/54), [API-TAB-02](https://github.com/outside-labs/expose_api/issues/67) |
| 11 | [HS-TAB-02](https://github.com/outside-labs/headless_spreadsheets/issues/18) | `headless_spreadsheets` | T3 Editing | [HS-TAB-01](https://github.com/outside-labs/headless_spreadsheets/issues/17), [BP-TAB-01](https://github.com/outside-labs/backpack/issues/37) |
| 12 | [API-TAB-03](https://github.com/outside-labs/expose_api/issues/68) | `expose_api` | T3 Editing | [API-TAB-02](https://github.com/outside-labs/expose_api/issues/67) |
| 13 | [SUI-TAB-03](https://github.com/outside-labs/spatial_ui/issues/55) | `spatial_ui` | T3 Editing | [SUI-TAB-02](https://github.com/outside-labs/spatial_ui/issues/54), [API-TAB-03](https://github.com/outside-labs/expose_api/issues/68) |
| 14 | [TAB-03](https://github.com/outside-labs/compose_application/issues/41) | `compose_application` | T3 Editing | [TAB-02](https://github.com/outside-labs/compose_application/issues/40), [HS-TAB-02](https://github.com/outside-labs/headless_spreadsheets/issues/18), [SUI-TAB-03](https://github.com/outside-labs/spatial_ui/issues/55) |
| 15 | [TAB-04](https://github.com/outside-labs/compose_application/issues/42) | `compose_application` | T4 Qualification | [TAB-03](https://github.com/outside-labs/compose_application/issues/41) |
| 16 | [HS-MD-01](https://github.com/outside-labs/headless_spreadsheets/issues/11) | `headless_spreadsheets` | M0 Markdown decision | [PN-MD-EXTRACT-01](https://github.com/outside-labs/pretty-notebook/issues/191) |
| 17 | [PN-MD-EXTRACT-02](https://github.com/outside-labs/pretty-notebook/issues/192) | `pretty-notebook` | M1 Markdown | [PN-MD-EXTRACT-01](https://github.com/outside-labs/pretty-notebook/issues/191), [HS-MD-01](https://github.com/outside-labs/headless_spreadsheets/issues/11) |
| 18 | [PN-MD-EXTRACT-03](https://github.com/outside-labs/pretty-notebook/issues/193) | `pretty-notebook` | M1 Markdown | [PN-MD-EXTRACT-02](https://github.com/outside-labs/pretty-notebook/issues/192) |
| 19 | [HS-MD-02](https://github.com/outside-labs/headless_spreadsheets/issues/19) | `headless_spreadsheets` | M1 Markdown | [PN-MD-EXTRACT-02](https://github.com/outside-labs/pretty-notebook/issues/192) |
| 20 | [TAB-MD-01](https://github.com/outside-labs/compose_application/issues/43) | `compose_application` | M1 Markdown | [PN-MD-EXTRACT-03](https://github.com/outside-labs/pretty-notebook/issues/193), [HS-MD-02](https://github.com/outside-labs/headless_spreadsheets/issues/19), [TAB-04](https://github.com/outside-labs/compose_application/issues/42) |
| 21 | [TAB-LIVE-01](https://github.com/outside-labs/compose_application/issues/44) | `compose_application` | Later extensions | [TAB-04](https://github.com/outside-labs/compose_application/issues/42) |

The existing [CA-07](https://github.com/outside-labs/compose_application/issues/7)
and [pocket-python Track B](https://github.com/outside-labs/pocket-python/issues/601)
remain the canonical browser-local capability gates. A future table workload
consumes qualified capability slices; this plan does not claim browser-local
SQLite, whole-package compatibility or duplicate runtime implementation tasks.

## Rolling PR batches

**Setup:** TAB-00 creates this plan, linked Project and scoped issue queue.
Its documentation PR establishes the planning baseline.

**Batch 1 — five foundation PRs:** TAB-01, HS-TAB-01, BP-TAB-01,
API-TAB-01 and PN-MD-EXTRACT-01. The shared contract lands first; the in-memory
source, storage search, API contract and extraction inventory then proceed on
their declared prerequisites. This batch makes the next read-only work concrete
without waiting for a Markdown package-name decision.

**Batch 2 — four read-only PRs:** API-TAB-02, SUI-TAB-01,
SUI-TAB-02 and TAB-02. Deliver actual dataset query behavior, an accessible
component, session-owned controls and a persistent read-only reference.

**Batch 3 — four editing PRs:** HS-TAB-02, API-TAB-03,
SUI-TAB-03 and TAB-03. The headless binding and HTTP write path consume the same
identity/revision semantics; the browser/reference prove durable edits.

**Qualification checkpoint:** TAB-04 consolidates installed, upgrade and browser
evidence after the editable slice. Do not invent unrelated work to fill a batch.

**Markdown decision and batch:** HS-MD-01 follows the inventory. Package/API
selection is a genuine decision point. After adoption, use four focused PRs
for generic extraction/package implementation, Pretty Notebook adoption,
the optional spreadsheet adapter and TAB-MD-01 acceptance. The selected package
may split extraction into child PRs while retaining the parent acceptance gate.

**Later:** TAB-LIVE-01 selects queried-collection refresh semantics. Additional
views, generated table projects, row/bulk operations, rich cell persistence,
case-insensitive/indexed search and browser-local support get finite owner tasks
when their contracts are selected. Formula calculation, XLSX, Google Sheets,
joins and undo/history retain their existing spreadsheet roadmap owners.

Use one branch and focused PR per task. Start CI after each ready push and
continue the next task immediately. Stack only same-repository dependencies;
cross-repository work uses explicit qualified immutable sources and issue links.
Collect failures, fix them, squash merge passing dependencies first, reconcile
immediate dependents before deleting parents and update main. Stop after failed
Git operations to resolve them before continuing mutations.

## Acceptance and verification

| Boundary | Required evidence |
| --- | --- |
| Source/view | Stable identities through sort/filter/projection, detached versus live semantics, metadata fidelity and finite bounds |
| Query/storage | Literal search, null/tie ordering, query-bound cursors, budgets, invalid descriptors, atomic edits, two writers and independent reopen |
| HTTP/policy | Hidden fields, access before page filling, concealed rows, denied current/proposed updates, redacted failures and unchanged default CRUD |
| Browser | Sort/search without writes, saved cell after sort, independent view state, keyboard/composition/focus, conflicts, invalid drafts and late-response refusal |
| Lifecycle | Lost committed response reconciliation, process restart, cancellation, complete task/session/connection cleanup |
| Installed profiles | Exact optional dependency sources, base isolation, wheel/source use, supported platform checks and data-preserving upgrades |
| Markdown | Full attributed existing corpus, table syntax/escaping, source spans, parser budgets, notebook compatibility and publication fingerprints |

Implement behavior and its focused checks together. Use the smallest relevant
local checks and each repository's existing relevant CI. Reuse fresh passing
evidence for unchanged code. TAB-04 assembles cross-package evidence; it is not
the first point at which integration is tested.

Publication, hosted deployment, a PostgreSQL driver/service and public activation
remain separate operations. This plan creates no release, changes no current
runtime dependency versions and selects no new external service.
