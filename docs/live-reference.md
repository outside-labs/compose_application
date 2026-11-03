# Protected native live reference

`compose_application.live.LiveApplication` implements the optional
`cpython-live/1` reference. It combines the selected API's protected single-record
event profile, persistent Backpack journals, checked REST writes and native UI
sessions. Base installation remains dependency-free. This CPython profile is
independent of Track B browser-local grants and of public hosting activation.

```python
from pathlib import Path
from expose_api import Principal
from compose_application.live import Credential, LiveApplication, LiveConfig

# The application supplies existing credentials and their current verifier.
# No login route or credential issuance is provided by this reference.
principal = Principal("an-opaque-global-subject", scopes=frozenset({"work-items"}))
application = LiveApplication(LiveConfig(
    database=Path("live-work-items.sqlite3"),
    origin="https://work.example",
    verify=verify_current_credential,
    credentials=(Credential(principal, application_credential),),
))
```

Pass `application` to an explicitly selected ASGI host with lifespan enabled.
The host must support HTTP and WebSocket upgrades, preserve the exact configured
Host and bound headers, connections and send deadlines. HTTPS is required except
for explicit loopback HTTP. An explicit async context is also supported for
embedding in an already owned lifecycle. Construction opens no storage, sockets
or threads. The package neither installs a production server nor starts a public
listener. The existing `compose_application.ui` preview remains the REST example.

## Identity and sessions

Provision the configured `work_identity` cookie through the application owner,
with HttpOnly, SameSite=Strict, Path=/ and Secure on HTTPS. Tokens are bounded
opaque application inputs and never enter HTML, URLs, WebSocket subprotocols,
messages or receipts. The synchronous verifier must be nonblocking, bounded and
return the currently valid immutable Principal, or None. Exceptions and
awaitables fail closed. Expiry/revocation and credential replacement are owned
by that verifier. There is no external identity provider, credential database or
login endpoint in this profile.

Select at most eight credential bindings with globally unique subjects and the
`work-items` grant. Each selected principal owns a distinct native UI adapter,
worker, random session cookie and component registry. Browser contexts have
independent editors even for the same principal; switching identity cannot
reuse another principal's UI request token. Subject ownership is the reference's
record policy; applications needing tenant identities need a separately selected
model/policy. The UI cookie establishes component state only.

Browser snapshots use the same-origin identity cookie. Synchronous UI callbacks
use an explicit server-owned bearer bridge to that same origin; each callback
re-verifies the credential. The bridge supplies the owner on create, while owner
is excluded from visible API output. The server does not forward arbitrary
browser cookies. Cookie-authenticated HTTP writes require the exact Origin;
UI form writes additionally retain native session/request-token checks.
Authorization+Cookie ambiguity and duplicate sensitive headers fail closed.

## Editing and delivery

Save a record, then load its key in another context. Each loaded editor opens
one read-only `expose-api.events.v1` subscription. Remote values are a separate
projection: pending text, checkbox values, composition, selection and focus
survive updates. Remote cursors never become write revisions. Save uses the
loaded strong ETag/If-Match revision. A conflict preserves the draft; Load /
refresh updates the checked baseline while retaining edits for a deliberate
merge. Discard edits replaces them with that loaded baseline. Delete is checked
and authorized atomically. Denied existing records remain concealed before
revision comparison.

Snapshots may coalesce writes, repeat values or arrive after a concurrent
authorization change that followed their authorized read. The API re-verifies
current identity and record policy on every poll. A revoked or inaccessible
subscription closes generically and the browser clears the remote value.
Transient disconnects use bounded backoff and the last opaque cursor. Expired
cursors recover with resync plus a fresh snapshot, without historical replay.
Connection generations refuse older completions. Browser stop retires sockets,
handlers and retry timers; reload starts fresh. An uncertain REST write requires
an explicit reload/reconciliation, never an automatic retry.

## Storage and lifecycle

The profile owns `app_live_work_items` in namespace `live_work_items`, type key
`example.live_work_item`, and journal namespace `live_work_item_events`. Default
retention is 64 committed invalidations, configurable from 1 to 4096. Every
writer must use the same model, table/type key, retention and journal namespace
against the same local SQLite file. Separate processes poll committed keys and
read current authorized values. All writes use public adapter units of work;
direct SQL and non-journal writers are outside the profile.

This schema is separately owned from the public REST reference's work-item
table. Existing records are not silently imported or reinterpreted. To adopt
an event profile for existing application data, stop writers, make and verify
the application's backup, then start all compatible event-enabled writers.
Rollback stops writers/subscribers before restoring compatible code/data.
Never change journal retention while writers are running.

The wrapper admits at most 64 HTTP requests, each UI adapter retains the native
16-request bound and 128-session/1800-second idle bounds, and the API admits at
most 64 sockets with a 65536-byte event limit. Browser connection/retry bounds
come from the public spatial UI profile. One process/event loop owns each open
LiveApplication; multiple UI workers or distributed UI sessions are unqualified.
Shutdown stops admission, drains UI callbacks and admitted HTTP work, closes
subscriptions, clears UI sessions and joins workers before storage closes.
Cancellation waits for cleanup. Restart makes fresh UI sessions; committed
records and journal cursors persist. The host must drain its listeners before
shutdown; callbacks still require their own finite I/O bounds.

The exact immutable source revisions and acceptance evidence are recorded in
`compatibility-v1.json`. Releases, package uploads, production ASGI host/proxy
selection and actual public deployment remain separate decisions.
