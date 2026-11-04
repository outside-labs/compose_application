# Reference project layout

The accepted REST, typed UI and protected live workflows demonstrate repeated
assembly needs. Project generation selects one of these finite CPython
references explicitly. It does not infer an application model or storage schema.

| Selection | Shared assembly | Profile-specific ownership |
| --- | --- | --- |
| `service` | Persistent SQLite, validated work items, checked REST, caller-owned shutdown | Public synthetic records and a loopback HTTP development listener |
| `ui` | The service workflow plus independent typed form sessions | Loopback REST/UI listeners, UI worker cleanup and explicit conflict/merge |
| `live` | Persistent checked work items, typed forms and committed single-record snapshots | Caller-supplied exact origin, current credential verifier, principal bindings and native ASGI host |

The REST/UI references share the public work-item schema; the protected live
reference owns a separate table and journal. Selecting a different project
profile never migrates or reinterprets an existing database. The common layout
contains `pyproject.toml`, `README.md`, `.gitignore`, a selection receipt and
`src/<module>/` with application assembly and a command entry point. Application
source and all data belong to the project owner after creation.

Names are lowercase portable distribution names with single hyphens; Python
imports replace hyphens with underscores. Names that shadow standard-library,
integration or reserved platform names are refused. Every project selects one
profile and the immutable accepted composition source
`8977963049023c7fe72bb8a2c9089633df049c3d`. That source owns the qualified API,
UI and storage pins. The generator adds no runtime dependency to the base
composition package and imports no optional integration to select a profile.

Generation is a local operation. It will neither install dependencies nor
start an application. A new destination is staged before creation; existing
destinations are refused unless their selection receipt matches exactly.
Repeating the same selection is a read-only no-op, including after application
edits or database writes. The receipt identifies a creation request, not current
file integrity. No refresh, force, overwrite or migration mode is provided.

Generated checks use temporary databases. Starting a persistent service requires
an explicit database path. Live credentials and host configuration are supplied
at runtime; generation never receives or stores credentials. Public hosting,
package publication, PostgreSQL and Track B remain separately owned choices.

## Create a service project

```sh
python -m compose_application.projects ./garden-board --name garden-board --profile service
cd garden-board
uv sync
uv run garden-board check
uv run garden-board serve --database ./work-items.sqlite3
```

The destination's parent must exist. Creation stages all source files in that
parent, reserves a new destination exclusively, then publishes complete files
using same-filesystem hard links. The selection receipt is published last.
The local filesystem must support hard links. A failed/interrupted creation
removes its unchanged files and empty directories; concurrent owner edits and
additions survive. An incomplete destination without its receipt requires
owner inspection before another creation request. Existing empty directories,
files and symbolic-link destinations are refused. A matching repeat returns
`created: false` and never recreates missing files or changes modification times.

Select `--profile ui` for the typed form workflow with the same install/check/
serve commands. Its generated `app.py` owns both loopback listeners and drains
the UI worker before REST/storage close. The generated check opens the real UI
page and verifies two independent public form sessions, validation, preserved
drafts on conflicts, explicit merge, durable reopen and checked deletion.
The accepted component's broader Chromium evidence remains in the UI matrix;
the generated-project checks verify the selected assembly and public forms.

Select `--profile live` for a protected native ASGI factory. Its command exposes
`check`; the application owner supplies the persistent database, exact origin,
current synchronous verifier, explicit principal/credential bindings and an
HTTP/WebSocket host through `create_application(...)`. There is no generated
listener, login route, token or environment-secret template. The generated README
describes cookie provisioning, principal isolation and drained restart/backup
requirements. Temporary checks generate disposable credentials in memory and
verify protected REST, concealed denial, native snapshots, revocation, reopen
and complete worker cleanup. The accepted live matrix retains broader Chromium,
cross-process delivery and reconnect evidence; generation chooses that reference.

Implementation and acceptance: [CA-09](https://github.com/wispsy/compose_application/issues/9),
[STYLE-01–06](https://github.com/wispsy/compose_application/issues/22).

## Installed acceptance

`scripts/check_distribution.py --projects --report /tmp/projects.json` builds
wheel and source artifacts, uses each isolated installed generator and normally
installs all three emitted profiles into separate environments. It verifies
immutable dependency provenance and exact installed application source hashes,
then runs the installed console scripts. Each uses two independent processes
for temporary data: nine service, 15 UI and 15 live checks per artifact.
Receipts also verify import isolation and unchanged bytes/modification times
after source edits, a data fixture and the same generation request. The normal
cross-platform compatibility job retains these results alongside existing
service/UI/live acceptance. The base package still installs independently.
