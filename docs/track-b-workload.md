# Track B work-item workload, version 1

The [original Python source](../examples/track_b_work_items.py) selects a finite
Python-owned domain/view/save use for `track-b-local/1`. This is a prerequisite
qualification, not browser acceptance. The workload creates a work item,
validates edits, renders typed text segments from a t-string, saves a versioned
JSON record through an awaited host, and reloads/validates that same domain key.
The pilot uses synthetic garden/checklist titles and no sensitive data.

## Source and dependency closure

The one workload source file has no package-relative imports or resources.
It uses CPython 3.14 `dataclasses.dataclass`/`fields`,
`typing.get_type_hints`, `json.loads`/`dumps`, t-string `strings` and
`interpolations`/`value`, strict primitives, dictionaries, generators and native
coroutines. `asyncio.run` is used only by the CPython test harness, not the
workload. No full asyncio, dataclasses, typing or JSON module claim is implied
by selecting these entry points. The future package qualification must include
the actual transitive sources/resources/notices for any supplied modules.

`WorkItem`, `check_item`, `dump_item`, `load_item`, `render_item`, `save_item`
and `reload_item` are the selected entry points. Records have schema version 1,
a domain key, string revision and `title`/`done` values under the shared contract.
Titles contain 1–200 characters. Unknown/missing fields, wrong primitive types,
wrong schema versions and changed reload keys are refused. Templates carry text
segments and values; a renderer must not evaluate HTML or Python.

## Runnable qualification

```sh
uv run --locked python -m unittest discover -s tests
uv run --locked python scripts/probe_track_b.py --output /tmp/cpython-probes.json
uv run --locked python scripts/probe_track_b.py \
  --runtime ../pocket_python --output /tmp/track-b-probes.json
```

The runtime checkout must be explicitly selected and have no tracked changes.
The command never downloads it or changes it. The Node runner uses the owning
runtime's `runSourceRequest`, `classes-source/1` and an application-only source
registry (the core-only library closure). Module grants without supplied module
sources are refused. Each supported case must match isolated CPython stdout;
an unexpected runtime failure or nonzero logical teardown fails the check.
Refused syntax/import prerequisites are reported without turning them into
supported workload claims. Native-await's small probe checks syntax admission;
awaited execution requires the complete workload and later host acceptance.

The [recorded receipt](track-b-probes-v1.json) includes the original source and
individual probe SHA-256 values, runtime commit, host/version, supported/refused
results and logical close statistics. It records CPython 3.14.7 on macOS arm64
and Node 24.19.0 against pocket-python
`5072ae1b11c24bae219a73c35caa30c5406194d4`:

| Probe | Selected engine outcome | Owning prerequisite |
| --- | --- | --- |
| Domain dictionary/state values | Supported, matches CPython, zero logical close counters | Existing source profile |
| T-string view | Refused by source profile | [Track A #600](https://github.com/outside-labs/pocket-python/issues/600), shared formatting/syntax ownership |
| Dataclass fields | Module absent from the supplied registry | [Library profiles #126](https://github.com/outside-labs/pocket-python/issues/126), [package qualification #128](https://github.com/outside-labs/pocket-python/issues/128) |
| Typing reflection | Module absent from the supplied registry | Same selected-library owners; select actual APIs before reuse |
| JSON round trip | Module absent from the supplied registry | [JSON API slice in #126](https://github.com/outside-labs/pocket-python/issues/126) |
| Native await | Refused by source profile | [Async/host #34](https://github.com/outside-labs/pocket-python/issues/34), [Track B #601](https://github.com/outside-labs/pocket-python/issues/601) LB-1/LB-2 |
| Original workload | Refused at dependency admission | All selected syntax/library prerequisites above, before host execution |

The application-only registry result does not establish that no other library
profile could supply an API. The original workload is not yet executable on the
selected engine. Chromium/device acceptance and Shimify-reduced source remain
unqualified and are explicitly marked in the receipt. Do not replace original
source with handwritten reduced code to make the probe pass.

## Proposed granted host surface

These are requirements for CA-07 and the Track B host owner, not implemented
grants. Browser persistence selection stays with those owners; no browser SQL
engine or CPython `sqlite3` extension is assumed.

| Capability | Finite values and ownership | Required failure/cleanup behavior |
| --- | --- | --- |
| View/text | Python supplies `kind`, text `strings`/`values`, session and generation; host owns DOM handles | Apply only current generation, preserve input/focus, render as text, release handles/listeners on stop |
| Input/change | Domain key plus typed title/done edit, event-binding generation and session; Python validates/owns state | At most 16 queued changes; serialize per session, reject stale bindings and invalid types, detach listeners on restart |
| Storage/read | Application namespace, domain key, generation; at most 64 KiB per record and 100 pilot records | Denied/missing/corrupt/version-unknown records are visible errors; no silent reset; discard stale reload completions |
| Storage/write | Awaited `save(key, JSON text, generation)`; one in-flight save per key; positive committed receipt carries generation | Explicitly granted durable adapter, atomic per-record replacement; denial/failed save cannot claim success. Reconcile cancellation after dispatch by receipt/reload; old completions never overwrite edits |
| Optional REST | Explicit endpoint/origin, selected credentials, bounded resources/errors/string revisions | Separate grant; API-AUTH-01 owns access; preserve edits and reconcile uncertain writes |
| Optional WebSocket | Selected event protocol, subscription/session/generation, bounded queue | Separate grant; reconnect via accepted snapshot/subscription synchronization; reject stale/duplicate events and release tasks/listeners |

The CPython memory host in tests proves workload wiring and explicit failed-save
propagation only. It supplies no durable browser storage, generation scheduler,
quota policy or transaction/cancellation guarantee. CA-07 must accept durable
save/reload/recovery, unavailable storage, cancelled saves, stale completions,
and stop/restart with zero callbacks/listeners/tasks before adopting this pilot.
Connected acceptance additionally depends on the existing REST/WS/auth owners.

No runtime implementation is duplicated here. Follow the existing runtime and
library issues for missing capabilities; broad roadmap parents need not close
before their accepted slices can be consumed. This task adds no runtime package
dependencies, new service, publication or deployment.
