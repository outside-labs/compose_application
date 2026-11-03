# Persistent typed UI reference

The optional `ui` extra selects the finite `cpython-ui/1` reference over the
existing `cpython-service/1` profile. It combines spatial_ui's public typed forms
and checked REST client with the persistent work-item API. The base package stays
independent; the service extra does not install the UI. The
[compatibility register](compatibility-v1.json) records exact unreleased source
revisions. Published 0.1.0 package versions alone do not identify these features.

From a source checkout:

```sh
uv sync --locked --extra ui
uv run --locked --extra ui python -m compose_application.ui serve --database ./work-items.sqlite3
```

Open the printed loopback URL. Enter a new key and title, choose Save and press
Apply (or Enter in a text field). Refresh list reads a bounded page of saved
records. Each browser cookie owns a fresh editor and component tree. Different
browser contexts have independent drafts; tabs sharing a cookie share the session
and can invalidate each other's render bindings.

To edit an existing key, choose Load / refresh and Apply. The strong ETag revision
guards Save and Delete. A concurrent edit produces a conflict and retains the
local draft. Load / refresh then updates the committed value/revision and keeps
dirty fields for a deliberate merge. Expand Loaded server value to compare the
visible committed projection. Save submits the merge, Discard edits replaces the
draft with that loaded value, and Start new explicitly clears the editor.

Validation errors preserve text/checkboxes and focus visible invalid fields.
Backend errors without visible field paths use a fixed live status message.
The list and editor project only declared visible fields. Application identity,
render-binding versions and draft edit sequences have separate owners.

The command owns one asynchronous API service and a separate preview-server
thread. Both bind to loopback; callbacks remain synchronous and serialized under
the preview session lock. Ctrl+C stops HTTP admission, joins the preview thread
and drains storage. Durable records survive process restart; browser sessions and
unsaved DOM drafts do not. A disconnected or canceled dispatched save can still
commit and requires an explicit reload to reconcile. No write retries occur.

This synthetic example is explicitly public on loopback. It is not an identity
provider, row-level access profile, production host or live WebSocket application.
API-AUTH-01, SUI-HOST-01, SUI-WS-01 and CA-05 keep those owning gates. Track B
browser-local view/storage acceptance remains separate from this CPython service.

## Finite acceptance

```sh
uv run --locked --extra ui python -m compose_application.ui check
uv run --locked python scripts/check_distribution.py --matrix --ui --report /tmp/compatibility.json
uv sync --locked --extra ui --group browser-tests
uv run --locked --extra ui --group browser-tests python -m playwright install chromium
uv run --locked --extra ui --group browser-tests python -m unittest discover -s tests -p browser_ui.py -v
```

The first command provides 15 form/REST checks in two independent processes,
including validation, conflict/merge, persistence and deletion. Installed wheel
and source profiles each repeat those checks with exact dependency provenance,
alongside the existing minimum/current service and upgrade matrix. Linux Chromium
acceptance runs the actual preview and REST processes with independent browser
contexts, keyboard/checkbox input, validation focus, preserved edits, comparison,
discard, list refresh, phone/desktop widths, reduced motion and graceful process
restart. `ui-browser-receipt.json` records that finite browser acceptance; it is
retained by CI alongside the platform-specific compatibility receipts.
