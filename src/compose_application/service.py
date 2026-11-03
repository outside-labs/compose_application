"""Explicit CPython service configuration and asynchronous resource ownership."""

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, is_dataclass
from importlib import import_module, metadata
from pathlib import Path
import re


class ProfileError(RuntimeError):
    """A selected application profile is unavailable or incompatible."""


@dataclass(frozen=True)
class ServiceConfig:
    model: type
    database: Path
    namespace: str
    table: str
    type_key: str
    id_field: str = "id"
    resource_path: str = "/items"
    public: bool = False
    authorize: object = None
    profile: str = "cpython-service/1"
    timeout: float = 5.0
    queue_limit: int = 64
    max_body_size: int = 65536

    def __post_init__(self):
        if self.profile != "cpython-service/1":
            raise ProfileError("Select the supported cpython-service/1 profile.")
        if not isinstance(self.model, type) or not is_dataclass(self.model):
            raise ValueError("Select an explicit trusted dataclass model.")
        if str(self.database) == ":memory:":
            raise ValueError("The service profile requires a persistent local database path.")
        object.__setattr__(self, "database", Path(self.database))
        if type(self.public) is not bool or (self.public and self.authorize is not None) or (not self.public and not callable(self.authorize)):
            raise ValueError("Choose public=True or an explicit authorization callback.")
        if type(self.queue_limit) is not int or not 1 <= self.queue_limit <= 1024:
            raise ValueError("Queue capacity must be between 1 and 1024.")
        if type(self.max_body_size) is not int or not 1 <= self.max_body_size <= 65536:
            raise ValueError("Body size must be between 1 and 65536 bytes.")
        if type(self.resource_path) is not str or not re.fullmatch(r"/[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*", self.resource_path):
            raise ValueError("Choose an explicit static resource path.")


def _dependencies():
    try:
        for name in ("expose-api", "backpack-store", "enforce-type"):
            if metadata.version(name) != "0.1.0":
                raise ProfileError("Installed package versions do not match the qualified service profile.")
        api = import_module("expose_api")
        adapter = import_module("expose_api.backpack").BackpackStore
    except (ImportError, metadata.PackageNotFoundError):
        raise ProfileError("Install compose-application[service] with the qualified development dependencies.") from None
    if not all(callable(getattr(adapter, name, None)) for name in ("open", "get_row", "update_checked", "delete_checked", "aclose")):
        raise ProfileError("The installed storage adapter does not implement the selected profile.")
    return api, adapter


class Service:
    """Opened storage, typed resource and API; the caller owns HTTP admission."""

    def __init__(self, config, store, resource, app):
        self.config, self.store, self.resource, self.app = config, store, resource, app
        self._close_task = None

    async def aclose(self):
        """Drain storage cleanup before propagating cancellation; safe to repeat."""
        if self._close_task is None:
            self._close_task = asyncio.create_task(self.store.aclose())
        cancelled = False
        while not self._close_task.done():
            try:
                await asyncio.shield(self._close_task)
            except asyncio.CancelledError:
                cancelled = True
        self._close_task.result()
        if cancelled:
            raise asyncio.CancelledError


@asynccontextmanager
async def application(config: ServiceConfig, *, store_type=None):
    """Open the selected profile, unwind failed startup and close after serving.

    An explicit store subclass can add application-owned checked-write behavior;
    it must preserve the qualified adapter's public ownership contract.
    """
    if not isinstance(config, ServiceConfig):
        raise TypeError("application() requires ServiceConfig.")
    api, adapter = _dependencies()
    if store_type is not None:
        if not isinstance(store_type, type) or not issubclass(store_type, adapter):
            raise ProfileError("Custom stores must extend the qualified Backpack adapter.")
        adapter = store_type
    store = await adapter.open(config.model, config.database, namespace=config.namespace,
                               table=config.table, type_key=config.type_key, id_field=config.id_field,
                               timeout=config.timeout, queue_limit=config.queue_limit)
    service = Service(config, store, None, None)
    try:
        app = api.App(max_body_size=config.max_body_size)
        resource = app.include(config.model, store=store, path=config.resource_path,
                               id_field=config.id_field, public=config.public, authorize=config.authorize)
        app.state["profile"] = config.profile
        service.app, service.resource = app, resource
        yield service
    finally:
        await service.aclose()
