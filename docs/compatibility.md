# Application compatibility matrix v1

The [machine-readable register](compatibility-v1.json) selects two finite service
combinations and one optional typed UI combination. Service and installed UI
checks run CPython 3.14 on Linux, macOS and Windows; receipts record
the exact Python patch, OS, source revision and installed dependency commits.
These are explicitly qualified development sources. The separately published
0.1.0 packages alone do not provide the storage adapter or composition profile.

| Profile | Composition source | Expose API source | Backpack Store source | Enforce Type |
| --- | --- | --- | --- | --- |
| Minimum service | `5e9bdf4bb9479734f9214bbe241290bae28827fa` | `aef200defd2514c38e3857f6278ea45aa577e369` | `54f5a1e883fcc32f8d87cc553dc83dae0434300d` | Published `0.1.0` |
| Current service | Exact candidate source and wheel/source hashes in each receipt | `01d7c486ae9041532c8bfe01d8a2a00496523e68` | `54f5a1e883fcc32f8d87cc553dc83dae0434300d` | Published `0.1.0` |

The minimum composition commit contains the accepted REST reference and its
declared dependency pins. The current profile advances the optional API pin to
the accepted OpenAPI and transaction-validation repair revision. Both retain the same scalar
SQLite contract. Their package metadata versions happen to match; immutable
source revisions distinguish these development combinations. No Cartesian
product or synchronized package release is implied.

Run the same installed-package matrix used by CI:

```bash
uv run --locked python scripts/check_distribution.py \
  --matrix --ui --report /tmp/composition-compatibility.json
```

The checker builds the current wheel and source distribution, verifies their
installed Python source bytes, and tests base isolation before installing any
integration packages. It installs the immutable minimum composition separately
using its own declared extra. Every selected environment verifies exact package
versions/VCS provenance and dependency consistency, failed-startup/canceled-close
lifecycle, competing checked HTTP requests and the 16-check real HTTP/process
restart acceptance. Each current artifact also reopens a database written by
the minimum environment, checks exact committed values/revisions, rejects stale
edits/deletes and completes checked deletion in a new process.

Receipts contain package/artifact SHA-256 values, immutable dependency revisions,
base isolation, exact acceptance phases and code-upgrade outcomes. A local run
with uncommitted changes is marked `source_clean: false`; CI supplies the exact
clean candidate commit. Failure records identify the failing profile/phase and
exception type; command failures retain their ordinary CI diagnostics. Reports
contain no credentials, user databases or fixture paths. CI retains one receipt
per OS on both PR and final-main workflows.

This matrix qualifies a code/dependency upgrade over the existing schema. It
does not promise arbitrary schema migrations: unknown registrations still fail
closed. Ordered migration, verified backup and broader SQLite process behavior
retain their owning Backpack Store tests. The reference matrix directly covers
transaction rollback, stale revisions, concurrency, persistence and process
restart. Extend the selected combinations and acceptance only as an owning
feature is accepted.

Track B is separate. Its original-source prerequisite workload and reduced-source
qualification, granted view/storage APIs, browser devices and teardown evidence
remain under their existing runtime owners. The existing finite Node prerequisite
probe still runs in CI; it does not constitute browser application acceptance.
There is no accepted browser-local or connected-browser profile in this matrix.
Publication, deployment and identity/access policy retain their separate gates.

The optional [typed UI reference](ui-reference.md) adds a spatial_ui source pin
to the current service profile. Each current installed artifact verifies its
exact UI provenance and 15 public form/REST checks across process restart.
Chromium on Linux separately verifies the real loopback preview, independent
contexts, typing/keyboard/checkboxes, validation focus, conflict/merge/discard,
preserved drafts, phone/desktop widths, reduced motion and graceful restart.
Those finite browser receipts do not qualify Track B browser-local execution.
