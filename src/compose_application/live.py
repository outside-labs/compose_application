"""Protected, single-origin native live composition with explicit credentials."""

import asyncio
from contextlib import AsyncExitStack, asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
import hmac
from importlib import metadata
import inspect
import json
import os
from pathlib import Path
import re

from .reference import WorkItem
from .service import ProfileError


@dataclass(frozen=True)
class OwnedWorkItem:
    key: str
    title: str
    done: bool = False
    owner: str = field(default="", metadata={"expose_api": {"write_only": True}})

    def __post_init__(self):
        WorkItem(self.key, self.title, self.done)
        if type(self.owner) is not str or len(self.owner) > 256:
            raise ValueError("Select a bounded owner identifier.")


@dataclass(frozen=True)
class Credential:
    principal: object
    token: str = field(repr=False)

    def __post_init__(self):
        if type(self.token) is not str or not re.fullmatch(r"[A-Za-z0-9._~-]{16,256}", self.token):
            raise ValueError("Select an explicit bounded application credential.")


@dataclass(frozen=True)
class LiveConfig:
    database: Path
    origin: str
    verify: object = field(repr=False)
    credentials: tuple[Credential, ...] = field(repr=False)
    cookie_name: str = "work_identity"
    retention: int = 64

    def __post_init__(self):
        if str(self.database) == ":memory:":
            raise ValueError("Select a persistent local database.")
        object.__setattr__(self, "database", Path(self.database))
        object.__setattr__(self, "credentials", tuple(self.credentials))
        if not callable(self.verify) or inspect.iscoroutinefunction(self.verify):
            raise ValueError("Select a bounded synchronous credential verifier.")
        if not 1 <= len(self.credentials) <= 8 or any(type(value) is not Credential for value in self.credentials):
            raise ValueError("Select between one and eight explicit principal/credential bindings.")
        if len({value.token for value in self.credentials}) != len(self.credentials):
            raise ValueError("Application credentials must be unique.")
        if type(self.cookie_name) is not str or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]{0,63}", self.cookie_name):
            raise ValueError("Select one application-owned identity cookie name.")
        if type(self.retention) is not int or not 1 <= self.retention <= 4096:
            raise ValueError("Select a bounded journal retention.")


def _dependencies():
    try:
        for package in ("spatial-ui", "expose-api", "backpack-store", "enforce-type"):
            if metadata.version(package) != "0.1.0":
                raise ProfileError("Installed packages do not match the selected live profile.")
        import expose_api as api
        from expose_api.backpack import BackpackStore
        from spatial_ui import ASGIApp
        from spatial_ui.live import LiveConfig as BrowserLiveConfig
        if "predicate" not in inspect.signature(BackpackStore.update_checked).parameters:
            raise ImportError
    except (ImportError, metadata.PackageNotFoundError):
        raise ProfileError("Install compose-application[live] with its qualified source revisions.") from None
    return api, BackpackStore, ASGIApp, BrowserLiveConfig


@asynccontextmanager
async def _api_lifespan(app):
    incoming, outgoing = asyncio.Queue(), asyncio.Queue()
    task = asyncio.create_task(app({"type": "lifespan"}, incoming.get, outgoing.put))
    try:
        await incoming.put({"type": "lifespan.startup"})
        result = await outgoing.get()
        if result["type"] != "lifespan.startup.complete":
            await task
            raise ProfileError("Live API startup failed.")
    except BaseException:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        raise
    try:
        yield
    finally:
        await incoming.put({"type": "lifespan.shutdown"})
        result = await outgoing.get()
        await task
        if result["type"] != "lifespan.shutdown.complete":
            raise ProfileError("Live API shutdown failed.")


class _BridgeTransport:
    def __init__(self, origin, credential):
        from spatial_ui.rest import HTTPTransport
        self.transport = HTTPTransport(origin, headers=(("Authorization", "Bearer " + credential.token),))
        self.owner = credential.principal.subject

    def request(self, method, path, *, data=None, revision=None):
        if method == "POST":
            data = {**data, "owner": self.owner}
        return self.transport.request(method, path, data=data, revision=revision)


class LiveApplication:
    """One process/event loop; caller supplies the ASGI host and credentials.

    Constructing configuration opens no storage or worker. Use host lifespan,
    or an explicit async context for embedding, and drain the host on shutdown.
    """

    max_body_size = 65536

    def __init__(self, config: LiveConfig):
        if not isinstance(config, LiveConfig):
            raise TypeError("LiveApplication requires LiveConfig.")
        self.config = config
        self.state = {"profile": "cpython-live/1"}
        self.store = self.resource = self.api = None
        self.adapters = {}
        self._stack = self._close_task = self._idle = None
        self._requests = set()
        self._closing = False
        self._opening = False
        self._loop = self._pid = None

    def _credential(self, scope, *, bearer=True):
        headers = scope.get("headers", ())
        authorization = [value for name, value in headers if name.lower() == b"authorization"]
        cookies = [value for name, value in headers if name.lower() == b"cookie"]
        if len(authorization) > 1 or len(cookies) > 1:
            return None
        token = None
        if authorization:
            if not bearer or cookies:
                return None
            match = re.fullmatch(rb"Bearer ([A-Za-z0-9._~-]{16,256})", authorization[0])
            if match:
                token = match[1].decode("ascii")
        elif cookies:
            if len(cookies[0]) > 8192:
                return None
            matches = [part.strip().partition(b"=")[2] for part in cookies[0].split(b";")
                if part.strip().partition(b"=")[0] == self.config.cookie_name.encode("ascii")]
            if len(matches) == 1 and re.fullmatch(rb"[A-Za-z0-9._~-]{16,256}", matches[0]):
                token = matches[0].decode("ascii")
        if token is None:
            return None
        binding = next((value for value in self.config.credentials if hmac.compare_digest(value.token, token)), None)
        if binding is None:
            return None
        try:
            principal = self.config.verify(token)
            if inspect.isawaitable(principal):
                if inspect.iscoroutine(principal):
                    principal.close()
                return None
            return binding if type(principal) is type(binding.principal) and principal == binding.principal else None
        except Exception:
            return None

    async def __aenter__(self):
        if self._stack is not None or self._opening:
            raise RuntimeError("Live application is already open.")
        self._opening = True
        try:
            return await self._open()
        finally:
            self._opening = False

    async def _open(self):
        api, adapter, ASGIApp, BrowserLiveConfig = _dependencies()
        from spatial_ui.rest import ResourceClient
        from .ui import make_ui, resource_client
        if any(type(item.principal) is not api.Principal for item in self.config.credentials):
            raise ValueError("Bind explicit immutable API principals.")
        if len({item.principal.subject for item in self.config.credentials}) != len(self.config.credentials):
            raise ValueError("Select one credential binding per globally unique subject.")
        expected, returned, current = (ContextVar(name, default=None) for name in ("expected", "returned", "principal"))
        self._expected, self._returned, self._current = expected, returned, current
        def policy(principal, operation, value):
            return principal is not None and "work-items" in principal.scopes and principal.subject == value.owner
        class CheckedStore(adapter):
            async def create(self, key, value):
                result = await super().create(key, value)
                returned.set("1")
                return result
            async def get(self, key):
                row = await self.get_row(key)
                returned.set(row.revision)
                return row.value
            async def update(self, key, transform):
                principal = current.get()
                row = await self.update_checked(key, expected_revision=expected.get(), transform=transform,
                    predicate=(lambda value: policy(principal, "update", value)) if principal is not None else None)
                returned.set(row.revision)
                return row.value
            async def delete_where(self, key, predicate):
                await super().delete_where(key, predicate, expected_revision=expected.get())
        # Validate native origin/configuration before opening persistent storage.
        adapters = {}
        for credential in self.config.credentials:
            client = ResourceClient(_BridgeTransport(self.config.origin, credential), resource_client(self.config.origin).spec)
            adapters[credential.principal] = ASGIApp(make_ui(self.config.origin, client=client,
                live=BrowserLiveConfig("/work-items")), origin=self.config.origin)
        stack = AsyncExitStack()
        try:
            store = await CheckedStore.open(OwnedWorkItem, self.config.database, namespace="live_work_items",
                table="app_live_work_items", type_key="example.live_work_item", id_field="key",
                events=self.config.retention, event_namespace="live_work_item_events")
            await stack.enter_async_context(store)
            application = api.App(authenticate=lambda request: (binding.principal if (binding := self._credential(request.scope)) else None), auth_challenge="Custom")
            def authorize(request):
                current.set(request.principal)
                return "work-items" in request.principal.scopes
            resource = application.include(OwnedWorkItem, store=store, path="/work-items", id_field="key",
                authorize=authorize, record_policy=policy)
            application.subscribe(resource, origins=(self.config.origin,),
                hosts=(self.config.origin.split("://", 1)[1],), connections=64,
                max_message_bytes=65536, poll_interval=0.05)
            await stack.enter_async_context(_api_lifespan(application))
            for ui in adapters.values():
                await stack.enter_async_context(ui)
        except BaseException:
            await stack.aclose()
            raise
        self._stack, self.store, self.api, self.resource, self.adapters = stack, store, application, resource, adapters
        self._idle = asyncio.Event()
        self._idle.set()
        self._closing, self._close_task = False, None
        self._loop, self._pid = asyncio.get_running_loop(), os.getpid()
        return self

    async def __aexit__(self, *_):
        await self.aclose()

    async def aclose(self):
        if self._opening:
            raise RuntimeError("Live application startup is still running.")
        if self._stack is None:
            return
        self._owner()
        if self._close_task is None:
            self._closing = True
            self._close_task = asyncio.create_task(self._drain())
        task = self._close_task
        cancelled = False
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                cancelled = True
        task.result()
        if cancelled:
            raise asyncio.CancelledError

    async def _drain(self):
        await asyncio.gather(*(adapter.aclose() for adapter in self.adapters.values()))
        await self._idle.wait()
        await self._stack.aclose()
        self._stack = None
        self._loop = self._pid = None

    def _owner(self):
        if self._loop is not asyncio.get_running_loop() or self._pid != os.getpid():
            raise RuntimeError("Live application must stay in its opening process and event loop.")

    async def _error(self, scope, send, status):
        if scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 1008 if status != 503 else 1001})
            return
        body = json.dumps({"error": "Live application unavailable."}).encode()
        await send({"type": "http.response.start", "status": status, "headers": [
            (b"content-type", b"application/json"), (b"content-length", str(len(body)).encode()), (b"cache-control", b"no-store")]})
        await send({"type": "http.response.body", "body": b"" if scope["method"] == "HEAD" else body})

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            return await self._lifespan(receive, send)
        if self._stack is None or self._closing:
            return await self._error(scope, send, 503)
        self._owner()
        headers = scope.get("headers", ())
        hosts = [value for name, value in headers if name.lower() == b"host"]
        if hosts != [self.config.origin.split("://", 1)[1].encode("ascii")] or scope.get("root_path"):
            return await self._error(scope, send, 421)
        if scope["type"] == "websocket":
            return await self.api(scope, receive, send)
        if scope["type"] != "http":
            raise RuntimeError("Unsupported live application scope.")
        if len(self._requests) >= 64:
            return await self._error(scope, send, 503)
        marker = object()
        self._requests.add(marker)
        self._idle.clear()
        try:
            if scope["path"] == "/work-items" or scope["path"].startswith("/work-items/"):
                return await self._http_api(scope, receive, send)
            binding = self._credential(scope, bearer=False)
            if binding is None:
                return await self._error(scope, send, 401)
            await self.adapters[binding.principal](scope, receive, send)
        finally:
            self._requests.remove(marker)
            if not self._requests:
                self._idle.set()

    async def _http_api(self, scope, receive, send):
        headers = scope.get("headers", ())
        if scope["method"] in ("POST", "PATCH", "DELETE"):
            origins = [value for name, value in headers if name.lower() == b"origin"]
            bearer = any(name.lower() == b"authorization" for name, value in headers)
            if not bearer and origins != [self.config.origin.encode("ascii")]:
                return await self._error(scope, send, 403)
        expected = None
        if scope["method"] in ("PATCH", "DELETE"):
            revisions = [value for name, value in headers if name.lower() == b"if-match"]
            match = re.fullmatch(rb'"([1-9][0-9]{0,18})"', revisions[0]) if len(revisions) == 1 else None
            if match is None or int(match[1]) > 2**63 - 1:
                return await self._error(scope, send, 428 if not revisions else 400)
            expected = match[1].decode("ascii")
        tokens = self._expected.set(expected), self._returned.set(None), self._current.set(None)
        async def response(event):
            if event["type"] == "http.response.start" and 200 <= event["status"] < 300 and self._returned.get() is not None:
                event = {**event, "headers": [*event["headers"], (b"etag", ('"'+self._returned.get()+'"').encode("ascii"))]}
            await send(event)
        try:
            await self.api(scope, receive, response)
        finally:
            self._expected.reset(tokens[0]); self._returned.reset(tokens[1]); self._current.reset(tokens[2])

    async def _lifespan(self, receive, send):
        if (await receive())["type"] != "lifespan.startup":
            raise RuntimeError("Expected lifespan.startup.")
        try:
            await self.__aenter__()
        except Exception:
            await send({"type": "lifespan.startup.failed", "message": "Live application startup failed."})
            return
        try:
            await send({"type": "lifespan.startup.complete"})
            if (await receive())["type"] != "lifespan.shutdown":
                raise RuntimeError("Expected lifespan.shutdown.")
        finally:
            await self.aclose()
        await send({"type": "lifespan.shutdown.complete"})
