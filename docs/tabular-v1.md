# Tabular interfaces, version 1

This owner-neutral contract is `tabular/1`. Its finite examples are in
[`contracts/tabular-v1.json`](contracts/tabular-v1.json). Consumers implement
their own boundaries; this repository is not a runtime dependency.

## Identities and source ownership

`table_id` identifies an application-declared source; `schema_version` identifies
its column contract. Column `id` is independent of its display label and position.
`key` identifies a row independently of sort, search, projection and page number.
Persistent keys use the existing 1–128 ASCII domain-key grammar. A row `revision`
is a canonical positive decimal string through 9223372036854775807. It is never
a JSON number. In-memory sources may use source-instance keys and null revisions;
they must not promise identity across restart. A detached snapshot owns immutable
cells, including formats, formula locations and cached values. Existing live
views retain fixed membership and live values; materializing displayed values
does not preserve formula or edit identity.

`generation` is a nonnegative request counter, distinct from schema, row revision,
UI render version and connection generation. A cursor is opaque continuation,
not identity or authorization. Source closure releases owned resources and
refuses new work; closing a binding does not close a caller-owned source.

## Columns and scalar profile

Schemas are trusted application declarations, not editable database schemas.
Each column declares `id`, `label`, `type`, `nullable`, `visible`, `sortable`,
`searchable` and `writable`. Searchable columns must be visible text columns;
sortable/writable columns must also be visible. Client controls confer no rights.
The first persisted types are exact text, Boolean, portable integer
[-9007199254740991, 9007199254740991], finite float and explicit nullable null.
Boolean is distinct from integer. Decimal, date, datetime, formula and nested
values are refused without a separately qualified lossless codec. Native
Headless Spreadsheets rich values keep their existing independent fidelity.

## Queries and finite limits

`columns` is a unique ordered projection of visible column IDs. `order` contains
at most three distinct sortable IDs with exact Boolean `descending` directions.
Nulls sort last in either direction. Persistent queries append the ascending
primary key as a tie breaker; in-memory sources use original source row order.
Up to 16 typed AND predicates retain the storage query vocabulary.
`search` contains `fields` and `term`: literal case-sensitive Unicode substring
matching, no normalization, regex, wildcard or SQL interpretation. Fields form
an OR within the AND predicates. There are 1–8 distinct searchable text fields,
at most 256 term code points, and empty term clears search (canonical no-search).
Field order is canonicalized. Percent, underscore, quotes, backslash, NUL and
injection-shaped input remain literal. Remote queries operate on the declared
dataset, while local queries operate on a complete bounded in-memory source.

| Boundary | Maximum |
| --- | --- |
| Schema / visible columns | 128 / 64 |
| Rows per page / default | 1,000 / 50 |
| Cells per page | 16,000 |
| Text per displayed cell | 16,384 code points (explicit display truncation) |
| HTTP request / response | 65,536 / 4,194,304 bytes |
| Cursor | 16,384 characters |
| Policy candidate rows per page request | 10,000 |
| SQLite VM instructions per query | 1,000,000 |
| Complete local query rows / cells | 100,000 / 1,000,000 |

Applications may lower limits, never silently raise them. Page limits do not
bound scans. Policy candidate and SQLite work exhaustion return a value-free
`budget_exceeded`, without an incomplete page or hidden count. Sorting may
require scanning unindexed data; VM limits are approximate interrupt points,
not a wall-clock deadline or hard CPU sandbox.

Cursors bind normalized search, filters, order, schema and dataset. API cursors
also bind the configured application and current principal/access scope.
Projection and page size may change without changing storage ordering; the UI
resets continuation on any query/source change for clarity. Reauthorize every
request. Concurrent mutation may move, duplicate or omit rows between pages;
version 1 promises no frozen multi-page snapshot. Refresh starts again.
Superseded operations are canceled where supported; refuse results whose
source/generation no longer matches, even if cancellation arrives too late.

## Edits and recovery

Single-cell requests capture `table_id`, `key`, `column_id`, `expected_revision`
and `value` at edit start. A visual index or A1 address never identifies a write.
The server checks the writable allowlist, scalar, complete resulting model,
expected whole-row revision, and access to current and proposed values within
one owned transaction. A successful edit increments revision exactly once.
Missing/concealed rows, invalid/unsupported scalars, read-only columns and stale
revisions preserve all stored data and the draft. Another-cell edit on the same
row may conflict. No automatic merge, retry or revision substitution is allowed.

Each session owns its view and drafts independently. Sorting/search/projection
does not write data or schema. A draft keeps its captured row/column identity
when its row leaves the page, with an explicit save/discard affordance. Enter or
Save commits; Escape cancels. Conflicts offer explicit refresh/reapply/discard.
Canceled/disconnected saves can have committed: mark outcome uncertain, refuse
late completion and read authoritative state before another save. Errors are
value-free and distinguish `validation_error`, `unsupported_query`,
`unsupported_type`, `read_only`, `not_found`, `revision_conflict`,
`storage_unavailable`, `budget_exceeded` and `invalid_cursor`.

Version 1 excludes bulk/row/schema edits and collection subscriptions. Markdown
source remains authoritative and view operations never rewrite it.
