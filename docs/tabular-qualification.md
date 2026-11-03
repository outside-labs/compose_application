# Installed tabular qualification

The finite `cpython-tabular/1` profile selects the immutable dependencies in
[tabular-sources-v1.json](tabular-sources-v1.json). The
[compatibility manifest](tabular-compatibility-v1.json) records the prior
read-only composition and its exact dependencies for retained-data upgrade
checks. These are unreleased source combinations, independent of the existing
service, validation, UI and live profiles and their original pins.

The selected runtime is CPython 3.14 on Linux, macOS and Windows. CI records
the concrete OS, Python version and machine in each receipt; the default hosted
macOS runner is Intel. There is no implication of another interpreter, browser
engine or database backend.

```sh
uv sync --locked --extra tabular
uv run --frozen python scripts/check_distribution.py --tabular --report tabular-installed.json

uv sync --locked --extra tabular --group browser-tests
uv run --frozen python -m playwright install chromium
uv run --frozen python scripts/check_distribution.py --tabular --tabular-browser --report tabular-installed-browser.json
```

The script builds the exact candidate wheel/source pair, installs each in a
separate environment outside the checkout and verifies installed package bytes.
Each base environment has no optional integration packages available, including
Headless Spreadsheets. Each selected tabular environment resolves its declared
dependencies normally, verifies all five dependency versions/source revisions,
checks dependency consistency and hashes the installed API table module, UI
binding/runtime and headless source/Backpack adapter.

Nine contract/reference tests must execute with zero skips from each artifact.
They cover the 18-check read-only HTTP/process workflow, the 27-check editable
HTTP/process workflow, the seven-check headless consumer, original native
formula metadata, caller ownership, idempotent seeding, same-database consumer
interoperation and a canceled committed response reconciled by a fresh read.
The standalone commands and assembly are in the
[reference guide](tabular-reference.md).

For each artifact, a separate database is seeded by the previous immutable
read-only composition. The current installed composition then performs checked
edits and reopens in a new process. The remaining 117 of 120 records must retain
the exact same value/revision fingerprint, including the old profile's prior
concurrent writer. Every phase checks worker close. This qualifies a code and
dependency upgrade with the same registered reference schema; schema changes
require their own public migration and qualification.

With `--tabular-browser`, both read-only and editable Chromium scenarios execute
from each artifact's own installed interpreter and subprocesses. Each run must
execute both tests without skips. Their nested receipts retain phone/desktop
widths, reduced motion, independent view/draft state, two synthetic principals,
sort/search/projection, checked durable targets, stale-row conflict with explicit
review/reapply, invalid/read-only drafts, unrelated-field preservation, process
restart and graceful close. Browser binaries are installed explicitly through
the already-declared browser test group.

The normal platform jobs retain `compatibility-<platform>` artifacts with wheel
and source receipts. The browser job retains `tabular-browser`, containing
`tabular-installed-browser.json` with both artifact-specific browser receipts.
Failures retain their phase and error type; selected claims cannot silently skip.

## Supported bounds and extension seams

The first persisted schema is declared flat text, Boolean, portable integer,
finite float and explicitly nullable null. Whole-row checked transforms retain
unrelated fields and validate the complete proposed model. Native spreadsheet
formulas, Decimal, date and datetime remain available independently; this
durable profile refuses them without conversion or execution.

Queries admit at most 64 visible columns, 1,000 rows and 16,000 cells per page.
The reference requests 50 rows. Literal case-sensitive search admits eight
declared text fields and 256 code points. The API admits 10,000 policy candidates
and at most 1,000,000 approximate SQLite instructions per underlying query;
request and response bounds are 65,536 and 4,194,304 bytes. Exhaustion is explicit.
The UI editor uses the existing 4,096-byte typed form field bound. A caller
declares the public immutable key column used for exact-key reloads.

The row is the concurrency unit: different-cell writes to the same revision
can conflict, while other rows have independent revisions. Keyset pages across
concurrent edits can move, duplicate or omit rows; refresh starts a new query.
Drafts retain identity through view changes. A lost/canceled response can follow
commit, so uncertain writes require fresh read/review before explicit reapply.
No automatic overwrite or cross-cell merge is promised.

Collection refresh/live semantics stay under TAB-LIVE-01. Rich persistence
codecs, multi-cell transactions/bulk paste, dynamic schema editing, PostgreSQL,
public hosting and browser-local runtime/storage each need their own selected
contracts and evidence. Generated project support follows demonstrated repeated
assembly rather than this qualification gate. Markdown package/API selection
remains the separate MD-01 decision; notebook source is authoritative.
