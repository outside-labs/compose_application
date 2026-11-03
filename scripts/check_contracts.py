"""Check the finite version-one composition fixtures; no integration imports."""

import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
KEY = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z", re.ASCII)
REVISION = re.compile(r"[1-9][0-9]{0,18}\Z", re.ASCII)


def check_json(value, depth=0):
    if value is None or type(value) in (bool, str):
        return
    if type(value) is int and abs(value) <= 9007199254740991:
        return
    if type(value) is float and math.isfinite(value):
        return
    if type(value) not in (dict, list) or depth >= 16:
        raise ValueError("Unsupported JSON value or nesting.")
    if isinstance(value, dict) and any(type(key) is not str for key in value):
        raise ValueError("JSON object keys must be strings.")
    for child in value.values() if isinstance(value, dict) else value:
        check_json(child, depth + 1)


def check_revision(value):
    if not isinstance(value, str) or not REVISION.fullmatch(value) or int(value) > 9223372036854775807:
        raise ValueError("Invalid domain revision.")


def check_resource(value, *, deleted=False):
    if not KEY.fullmatch(value["key"]) or value["collection"] != "work_items":
        raise ValueError("Invalid pilot resource identity.")
    check_revision(value["revision"])
    if deleted:
        if "value" in value:
            raise ValueError("Deleted events cannot expose a value.")
    else:
        fields = value["value"]
        if set(fields) != {"title", "done"} or type(fields["title"]) is not str or type(fields["done"]) is not bool:
            raise ValueError("Invalid pilot resource fields.")


def main():
    raw = (ROOT / "docs/contracts/v1.json").read_bytes()
    if len(raw) > 65536:
        raise ValueError("Fixture exceeds the envelope bound.")
    fixture = json.loads(raw)
    check_json(fixture)
    if fixture["contract_version"] != 1 or fixture["profiles"] != [
        "cpython-service/1", "track-b-local/1", "connected-browser/1"
    ]:
        raise ValueError("Unknown contract/profile version.")
    for resource in fixture["resources"]:
        check_resource(resource)
    for revision in fixture["revisions"].values():
        check_revision(revision)
    for event in fixture["proposed_events"]:
        if event["contract_version"] != 1 or event["kind"] not in ("replaced", "deleted"):
            raise ValueError("Unknown proposed event version/kind.")
        check_resource(event, deleted=event["kind"] == "deleted")
    for error in fixture["errors"]:
        if error["code"] not in ("validation_error", "revision_conflict") or not isinstance(error["message"], str):
            raise ValueError("Unknown fixture error.")
        for issue in error["issues"]:
            if set(issue) != {"path", "code"} or any(type(part) not in (str, int) or (type(part) is int and part < 0) for part in issue["path"]):
                raise ValueError("Invalid public error path.")
    print("Version 1 profiles, resources, errors, revisions and proposed events passed.")


if __name__ == "__main__":
    main()
