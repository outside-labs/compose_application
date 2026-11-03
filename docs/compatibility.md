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
| Current service | Exact candidate source and wheel/source hashes in each receipt | `5d284e18bce7ae9f07ba64ac9297dad55a3fc5b1` | `54f5a1e883fcc32f8d87cc553dc83dae0434300d` | Published `0.1.0` |

The minimum composition commit contains the accepted REST reference and its
declared dependency pins. The current profile advances the optional API pin to
the accepted access, event and checked-predicate revision. Both retain the same scalar
SQLite contract. Their package metadata versions happen to match; immutable
source revisions distinguish these development combinations. No Cartesian
product or synchronized package release is implied.

Run the same installed-package matrix used by CI:

```bash
uv run --locked python scripts/check_distribution.py \
  --matrix --ui --live --projects --report /tmp/composition-compatibility.json
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
No Track B browser-local or connected-browser runtime profile is accepted by this matrix.
Publication and deployment retain their separate gates. The optional
[protected live reference](live-reference.md) selects an explicit identity and
record-access profile; it does not select browser-local Track B capabilities.

The optional [typed UI reference](ui-reference.md) adds a spatial_ui source pin
to the current service profile. Each current installed artifact verifies its
exact UI provenance and 15 public form/REST checks across process restart.
Chromium on Linux separately verifies the real loopback preview, independent
contexts, typing/keyboard/checkboxes, validation focus, conflict/merge/discard,
preserved drafts, phone/desktop widths, reduced motion and graceful restart.
Those finite browser receipts do not qualify Track B browser-local execution.

The `live` extra selects API `5d284e18bce7ae9f07ba64ac9297dad55a3fc5b1` and UI
`dccfb4c465051fee87254687ac4b59a09f61369f`. The existing service/UI entry points
consume these current compatible sources; the immutable minimum service and
prior REST/UI receipts remain recorded separately in the register. Installing
the base package still imports none of the integration packages.

Each installed `live` profile additionally runs nine required native/process
checks without skips, including writes from a different OS process, independent
subscribers, application-process reopen, retention/resync, concealed checked
denials and complete shutdown. Linux Chromium retains a separate protected-live
browser receipt for editing, principal isolation and same-origin restart.

## Generated reference projects

`--projects` uses the installed current wheel and source generator to create
each explicit `service`, `ui` and `live` project in a separate directory outside
the checkout. It installs all six emitted projects normally into independent
environments, resolving their declared immutable reference source
`64fdd88efec0238fa5a224d490cabd5e6a49c766` and its qualified dependency pins.
No candidate dependency override, editable source or `--no-deps` shortcut is
used for the generated applications. Service installation has no UI package.

Each installed console command performs two independent temporary-database
process phases. Service verifies nine HTTP/checked-revision/reopen cases; UI
verifies 15 page/form/conflict/reopen cases; live verifies 15 protected HTTP,
native snapshot, revocation and reopen cases. All phases drain owned workers;
the live factory uses in-memory disposable credentials and no listener. The
broader native/browser acceptance remains in the corresponding reference
profiles. Checks never consume an owner database or identity configuration.

Receipts retain exact generated source hashes, installed dependency revisions,
base import isolation, command results and read-only repeat acceptance after
source edits and a preexisting synthetic data file. Linux, macOS and Windows
run the same installed checks. These prove finite reference-project creation
and operation; arbitrary domains/schema migrations and production host selection
remain application work. See [project setup](reference-projects.md).
