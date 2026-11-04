# Explicit compiled validation service

The `validation` extra selects the qualified expose-api Enforce Type adapter and
the existing Backpack SQLite profile. It is a separate dependency combination
from the immutable service/UI/live references; install it in its own environment.
The base composition package still imports no optional libraries and installs
no runtime dependencies.

```sh
uv sync --locked --extra validation
uv run --frozen python -m compose_application.reference check --validation enforce-type
uv run --frozen python -m compose_application.reference serve --validation enforce-type --database ./work-items.sqlite3
```

The public `reference_application(database, validation="enforce-type")` selects
`cpython-service-enforce-type/1`. For explicit domain assembly, use that same
`ServiceConfig.profile` with `application(config)`. Both compile
`EnforceTypeSchema(model, id_field=...)` before opening storage. An unavailable
adapter or unsupported model fails before database I/O. The default reference
and default `ServiceConfig` continue to use their existing built-in schema.

The API still owns its admitted model surface, identities, constructor/default
checks, field projection and value-free HTTP errors. Enforce Type supplies
published synchronous compiled leaf operations; the adapter selects no coercion,
constraints, new model types or error/collection bounds. Storage retains its
own scalar intersection, codec, transactions and checked revision ownership.

The temporary-data command performs the same sixteen real HTTP checks across
two independent processes: construction, validation, immutable keys, checked
write/delete conflicts, durable reopen and cleanup. Five additional profile
checks verify explicit selection, missing-adapter refusal before storage,
schema admission, failed-startup cleanup and constructor rollback/reopen.
Wheel and source installations resolve their declared optional profile normally,
verify exact API/storage revisions and the published engine's source digest,
and retain receipts on Linux, macOS and Windows.

Automatic macOS qualification uses the standard `macos-15-intel` runner; the
Checks workflow retains manual `macos-latest` ARM64 selection with the same
acceptance. Receipts record the actual machine architecture. This follows the
[explicit runner repair](https://github.com/wispsy/expose_api/issues/62)
for the observed hosted ARM64 capacity failures.

Existing generated projects retain their previously accepted composition source
and dependency pins. This finite service selection does not introduce a new
UI/live source combination or change their prior browser evidence. Package
publication and hosted activation remain separately owned operations.
