# compose_application

The optional [compiled validation reference](docs/validation-reference.md)
selects the expose-api Enforce Type adapter explicitly and qualifies it through
persistent checked HTTP and independent process restart.

Optional composition of typed storage, APIs and spatial interfaces.

`compose_application` is the application integration home for **Cohesion Block A**.
It coordinates optional use of `backpack-store`, `expose-api` and `spatial-ui`,
with `enforce-type` validation and a pocket-python Track B application target.

- Repository: `outside-labs/compose_application`
- Distribution: `compose-application`
- Import: `compose_application`
- Python: 3.14 or newer
- Runtime dependencies: none in the initial package foundation

The component libraries remain independently useful and independently released.
Application profiles explicitly select integrations and dependencies. The source
provides owned persistent REST and typed UI references. Track B browser-local
runtime support retains its separate application gates.

## Plan and development queue

- [Tabular Interfaces plan](IMPLEMENTATION_PLAN.md) and
  [cross-repository Project](https://github.com/orgs/outside-labs/projects/19)
- [Cohesion Block A Project](https://github.com/orgs/outside-labs/projects/18)
- [Architecture charter](docs/cohesion-block-a.md)
- [Shared contract register](docs/contracts.md)
- [Track B workload and prerequisite probes](docs/track-b-workload.md)
- [Roadmap and owning issues](docs/roadmap.md)

Issues hold scope, acceptance criteria and dependencies. The organization Project
coordinates the repositories without replacing their existing development queues.
The initial batch establishes contracts, canonical storage naming, the validation
adapter and an extraction inventory of Pretty Notebook's storage behavior.

## Development

```sh
uv sync --locked
uv run --locked python scripts/check_contracts.py
uv run --locked python -m unittest discover -s tests
uv run --locked python scripts/check_distribution.py
```

The distribution check builds and installs both wheel and source distributions
into independent temporary environments outside the checkout. CI runs it on
Linux, macOS and Windows using Python 3.14.

No release has been published for this project. Package publication and hosted
deployment require their own selected scope and authorization. License terms
will be selected before publication.
## Service composition

The optional [CPython service profile](docs/service-profile.md) provides explicit
configuration and an asynchronous application context owning validated storage,
the typed resource and the ASGI app. Install with `uv sync --extra service`;
base imports remain independent of the integration packages.

The [persistent REST reference](docs/rest-reference.md) adds synthetic work-item
CRUD with checked revisions and real HTTP/process-restart acceptance. Run
`python -m compose_application.reference check` in the selected service environment.

The [compatibility matrix](docs/compatibility.md) qualifies immutable minimum
and current development profiles, installed artifacts and code-upgrade recovery.
CI retains exact per-platform receipts; browser application acceptance remains
separate from CPython service support.

## Typed UI reference

The optional [persistent typed UI](docs/ui-reference.md) combines public spatial_ui
forms with the checked REST reference. Use `uv sync --locked --extra ui`, then
`uv run --locked --extra ui python -m compose_application.ui serve --database ./work-items.sqlite3`.
The preview remains on loopback, with independent browser drafts, checked edits,
explicit conflict/merge choices and durable SQLite records. The `check` command
provides 15 form/REST checks across process restart; CI also exercises the actual
UI in Chromium and the optional profile in installed wheel/source environments.

The optional [protected native live reference](docs/live-reference.md) adds
same-origin cookie verification, per-principal native UI sessions and persistent
single-record WebSocket snapshots. Install with `uv sync --locked --extra live`.
The caller supplies existing credentials and a WebSocket-capable ASGI host;
publication and public hosting remain separate.

## Reference projects

Create a small application-owned reference with an explicit profile:

```sh
python -m compose_application.projects ./garden-board --name garden-board --profile ui
cd garden-board
uv sync
uv run garden-board check
uv run garden-board serve --database ./work-items.sqlite3
```

Select `service` for checked REST, `ui` for the loopback typed workspace, or
`live` for a protected native ASGI factory with caller-supplied credentials,
origin and host. Each project pins the accepted immutable composition source.
Generation installs nothing. Matching repeat requests leave owner edits and
data untouched. See the [layout, setup and acceptance](docs/reference-projects.md).

The optional [persistent read-only and editable table reference](docs/tabular-reference.md)
provides dataset sorting, literal search, column controls and pagination over
protected registered records without changing stored values or revisions.
Explicit editable mode adds checked scalar saves, preserved conflict drafts
and process-restart acceptance; a separate headless example uses the same rows.
