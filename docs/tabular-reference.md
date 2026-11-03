# Persistent read-only table reference

The optional `cpython-tabular/1` profile composes declared Backpack rows, the
opt-in tabular API and reusable Spatial UI TableBrowser. It is independently
selected from the existing service/UI/live/validation profiles. Exact compatible
unreleased sources are in [tabular-sources-v1.json](tabular-sources-v1.json).
Base installation still imports and requires none of these packages.

```sh
uv sync --locked --extra tabular
uv run --frozen python -m compose_application.tabular check
uv run --frozen python -m compose_application.tabular serve --database ./table.sqlite --port 8000
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
values. Schema/query responses expose no writable columns, and no cell-save
route exists in this profile.

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

Editing remains under HS-TAB-02/API-TAB-03/SUI-TAB-03/TAB-03. Markdown package/API
selection stays under the separate MD-01 decision; this read-only profile does
not depend on extraction, hosting or browser-local SQLite/runtime qualification.
