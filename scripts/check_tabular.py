"""Validate finite tabular/1 contract fixtures without integration imports."""

import json
from pathlib import Path

from scripts.check_contracts import KEY, check_json, check_revision


def check_schema(schema):
    if schema["contract"] != "tabular/1" or not KEY.fullmatch(schema["table_id"]):
        raise ValueError("Invalid table contract.")
    if type(schema["schema_version"]) is not str or not schema["schema_version"]:
        raise ValueError("Invalid schema version.")
    columns = schema["columns"]
    if not 1 <= len(columns) <= 128 or len({c["id"] for c in columns}) != len(columns):
        raise ValueError("Invalid columns.")
    for column in columns:
        if not KEY.fullmatch(column["id"]) or type(column["label"]) is not str:
            raise ValueError("Invalid column identity.")
        if column["type"] not in ("text", "boolean", "integer", "number"):
            raise ValueError("Unsupported persisted type.")
        if any(type(column[k]) is not bool for k in ("nullable", "visible", "sortable", "searchable", "writable")):
            raise ValueError("Invalid capability.")
        if (column["searchable"] and column["type"] != "text"
                or not column["visible"] and any(column[k] for k in ("sortable", "searchable", "writable"))):
            raise ValueError("Invalid capability combination.")


def check_fixture(fixture):
    check_json(fixture)
    check_schema(fixture["schema"])
    columns = {c["id"]: c for c in fixture["schema"]["columns"]}
    for page in fixture["pages"]:
        if type(page["generation"]) is not int or page["generation"] < 0:
            raise ValueError("Invalid query generation.")
        for row in page["rows"]:
            if not KEY.fullmatch(row["key"]):
                raise ValueError("Invalid row key.")
            check_revision(row["revision"])
            for name, value in row["values"].items():
                column = columns[name]
                expected = {"text": str, "boolean": bool, "integer": int, "number": float}[column["type"]]
                if not column["visible"] or (value is None and not column["nullable"]) or (value is not None and type(value) is not expected):
                    raise ValueError("Invalid projected value.")
    for edit in fixture["edits"]:
        check_revision(edit["request"]["expected_revision"])
        if edit["request"]["column_id"] not in columns:
            raise ValueError("Invalid edit column.")
        if edit["outcome"] not in ("saved", "validation_error", "revision_conflict", "read_only", "uncertain"):
            raise ValueError("Invalid edit outcome.")


def main():
    path = Path(__file__).resolve().parents[1] / "docs/contracts/tabular-v1.json"
    if path.stat().st_size > 65536:
        raise ValueError("Fixture exceeds envelope bound.")
    check_fixture(json.loads(path.read_text()))
    print("Tabular version 1 fixtures passed.")


if __name__ == "__main__":
    main()
