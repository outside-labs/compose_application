"""Original-source work-item workload for finite runtime prerequisite probes."""

from dataclasses import dataclass, fields
import json
from typing import get_type_hints


@dataclass(frozen=True)
class WorkItem:
    key: str
    title: str
    done: bool = False


def check_item(item):
    if type(item) is not WorkItem:
        raise ValueError("Invalid work item.")
    key = item.key
    if type(key) is not str or not 1 <= len(key) <= 128 or not key.isascii():
        raise ValueError("Invalid work item key.")
    if not key[0].isalnum() or any(not (char.isalnum() or char in "._-") for char in key):
        raise ValueError("Invalid work item key.")
    if type(item.title) is not str or not 1 <= len(item.title) <= 200 or type(item.done) is not bool:
        raise ValueError("Invalid work item fields.")
    try:
        item.title.encode("utf-8")
    except UnicodeError:
        raise ValueError("Invalid work item fields.") from None
    # The actual view binder needs both field order and resolved annotations.
    if tuple(field.name for field in fields(WorkItem)) != ("key", "title", "done"):
        raise ValueError("Invalid work item schema.")
    if get_type_hints(WorkItem) != {"key": str, "title": str, "done": bool}:
        raise ValueError("Invalid work item annotations.")
    return item


def check_revision(revision):
    if type(revision) is not str or not revision.isascii() or not revision.isdecimal():
        raise ValueError("Invalid work item revision.")
    if len(revision) > 19 or revision.startswith("0") or not 1 <= int(revision) <= 9223372036854775807:
        raise ValueError("Invalid work item revision.")


def dump_item(item, revision):
    check_item(item)
    check_revision(revision)
    return json.dumps({"schema_version": 1, "key": item.key, "revision": revision,
                       "value": {"title": item.title, "done": item.done}},
                      ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))


def load_item(raw):
    if type(raw) is not str:
        raise ValueError("Invalid saved work item.")
    try:
        size = len(raw.encode("utf-8"))
    except UnicodeError:
        raise ValueError("Invalid saved work item.") from None
    if size > 65536:
        raise ValueError("Invalid saved work item.")
    data = json.loads(raw)
    if type(data) is not dict or set(data) != {"schema_version", "key", "revision", "value"}:
        raise ValueError("Invalid saved work item.")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise ValueError("Unsupported saved work item version.")
    value = data["value"]
    if type(value) is not dict or set(value) != {"title", "done"}:
        raise ValueError("Invalid saved work item fields.")
    check_revision(data["revision"])
    return check_item(WorkItem(data["key"], value["title"], value["done"])), data["revision"]


def render_item(item):
    check_item(item)
    template = t"{item.title}: {item.done}"
    # A host renders text segments, never evaluates Python or compiles HTML.
    return {"kind": "text", "strings": list(template.strings),
            "values": [str(part.value) for part in template.interpolations]}


async def save_item(host, item, revision, generation):
    """Host save receipt is required; cancellation after dispatch needs reload."""
    payload = dump_item(item, revision)
    return await host.save(item.key, payload, generation)


async def reload_item(host, key, generation):
    raw = await host.load(key, generation)
    item, revision = load_item(raw)
    if item.key != key:
        raise ValueError("Saved work item key changed.")
    return item, revision
