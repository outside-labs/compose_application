# Persistent read-only and editable table reference

The optional `cpython-tabular/1` profile composes declared Backpack rows, the
opt-in tabular API and reusable Spatial UI TableBrowser. It is independently
selected from the existing service/UI/live/validation profiles. Exact compatible
unreleased sources are in [tabular-sources-v1.json](tabular-sources-v1.json).
Base installation still imports and requires none of these packages.

```sh
uv sync --locked --extra tabular
uv run --frozen python -m compose_application.tabular check
uv run --frozen python -m compose_application.tabular serve --database ./table.sqlite --port 8000
uv run --frozen python -m compose_application.tabular serve --editable --database ./table.sqlite --port 8000
uv run --frozen python -m compose_application.tabular check-edits
uv run --frozen python -m compose_application.headless_tabular check
```

The reference binds only numeric loopback HTTP. It seeds 120 synthetic records
without overwriting existing values/revisions. Alice sees 80 rows and Bob 40;
select `--principal bob` to run the second synthetic reader. The fixed
`reader-alice`/`reader-bob` demonstration credentials are local synthetic inputs,
not a production account system. Deployment, production credentials and package
publication remain separate decisions.

The UI shows mode, header sort directions, literal case-sensitive Unicode
substring search, displayed-column buttons/order, 50-row pagination and explicit
loading/empty/error states. Queries operate over the declared dataset. Source
keys, row revisions, schema versions, UI render versions and query generations
retain distinct meanings. Record access runs before page filling: the initial
40 rows denied to Alice do not truncate her visible page. The owner field stays
hidden and cannot filter/sort/search through the table profile.

Every browser owns independent query/selection state and one bounded query
worker. Search composition/focus survives rendering. Canceled/superseded queries
cannot replace a newer source/generation. Explicit refresh discards continuation;
keyset pages across concurrent writes can move/duplicate/omit rows and do not
promise a frozen snapshot. Query/scalar/cell/response/candidate/VM limits retain
[tabular/1](tabular-v1.md). Errors disclose neither hidden counts nor query/row
values. The default read-only mode exposes no writable columns or cell-save
route. `--editable` explicitly enables checked scalar edits and the immutable
public key column used by authoritative reloads.

The owned API SQLite worker, reference HTTP listener, UI sessions and per-browser
query workers drain on close. Preview server cleanup runs off the API event loop
so outstanding local HTTP reads can finish. Browser stop/pagehide asks the UI
host to close its session through the authenticated same-origin close endpoint.
Original Markdown and application schemas are never changed by view operations.

## Acceptance

`check` runs 18 actual HTTP/storage checks in independent seed/reopen processes:
more than one page, literal search, deterministic sort/nulls/ties, projection,
hidden-field refusal, principal cursor isolation, changed queries, no view
mutations, a trusted concurrent writer, continuation after restart and drained
workers. The concurrent writer is an acceptance fixture, not a browser edit path.

Four focused reference tests additionally qualify the actual public Headless
Spreadsheets snapshot/client boundary, formula metadata preservation, source
ownership, profile isolation and idempotent seeding. Each wheel/source artifact
is installed into a separate tabular environment; dependency receipts verify
the immutable source commits before running the checks. Existing profiles retain
their original pins and qualification.

The separate Chromium check uses actual HTTP and SQLite with phone/desktop
widths, reduced motion, independent browser contexts, header sorting, dataset
search, column visibility/order, pagination, two reader principals, restart and
graceful close. A before/after database signature proves that browser view
changes preserve every stored value and revision. It writes
`tabular-browser-receipt.json`, retained by CI.

```sh
uv sync --locked --extra tabular --group browser-tests
uv run --frozen python -m playwright install chromium
uv run --frozen python -W error::ResourceWarning -m unittest discover -s tests -p browser_tabular.py -v
```

## Editable workflow and independent headless consumer

With `--editable`, select a cell and choose **Edit selected cell**. Sort/search
before editing, stage a value, Save or press Enter, then clear search. The same
durable row retains the change after process restart. The title/done/rank/score
fields are writable; the domain key is immutable and owner remains concealed.
Titles must be nonblank and nullable ranks nonnegative. View state stays in each
browser; SQLite stores the records and revisions.

Drafts preserve captured row key/column/revision through sort/search/projection
changes. A second browser with an old whole-row revision receives a conflict
and retains its draft. Reload current row, review its value/revision, explicitly
reapply the draft and Save, or discard. Invalid/read-only/denied outcomes preserve
data and revisions. A canceled or lost response can follow commit, so reload
before retrying. The UI refuses superseded source/query/session completions and
drains accepted work on teardown.

`check-edits` runs 27 actual HTTP/storage checks in independent write/reopen
processes: sorted/filtered targets, committed projections, unrelated fields,
whole-row conflicts, invalid scalars/full models, immutable/hidden fields,
current/proposed authorization, independent rows and closed workers. An
additional cancellation test delays the HTTP response after commit and verifies
the committed row with a fresh exact-key query.

The separate `headless_tabular` example owns its synchronous public Backpack
registration and connection, supplies an explicitly imported BackpackSource,
and consumes detached scalar snapshots with the same keys/revisions/field IDs.
Its seven checks cover sort/search, a checked edit, unrelated fields, a second
writer, invalid-model rollback and independent reopen. A shared-database test
demonstrates that the API and this headless consumer see the same registered
row. It is trusted in-process access and has no HTTP authentication policy.
Native in-memory formulas/Decimal/date/datetime remain their independent profile;
the first durable adapter never silently converts them.

The separate `browser_tabular_edits.py` check uses actual HTTP, SQLite and
Chromium: sort/search/edit/save/clear search/restart, independent drafts, stale
conflicts with explicit review/reapply, invalid/read-only edits and unchanged
unrelated fields. It retains `tabular-edit-browser-receipt.json`. Run it with
the browser group and command above, replacing the test pattern with
`browser_tabular_edits.py`.

Markdown package/API selection remains a separate MD-01 decision. Collection
subscriptions, bulk edits, dynamic schema editing, PostgreSQL, hosting and
browser-local SQLite/runtime qualification remain separate extensions.
