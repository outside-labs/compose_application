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
`64fdd88efec0238fa5a224d490cabd5e6a49c766`. That source owns the qualified API,
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

Implementation and acceptance: [CA-09](https://github.com/outside-labs/compose_application/issues/9),
[STYLE-01–06](https://github.com/outside-labs/compose_application/issues/22).
