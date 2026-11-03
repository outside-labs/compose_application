"""Explicit in-process Headless Spreadsheets/Backpack table assembly."""

import argparse
from contextlib import contextmanager
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from .tabular import TableItem


@contextmanager
def headless_application(database):
    """The application owns registration, initialization and connection close."""
    from backpack_store import ApplicationStore, DataclassCodec
    from headless_spreadsheets import SourceColumn
    from headless_spreadsheets.backpack import BackpackSource
    with ApplicationStore.open(database) as store:
        model = store.register(DataclassCodec(TableItem, type_key="reference.table_item"), namespace="tabular",
            table="app_tabular_items", primary_key="key", columns={name: name for name in TableItem.__dataclass_fields__})
        store.initialize("tabular")
        source = BackpackSource(model, model_type=TableItem, key_field="key", table_id="work_items", schema_version="1", columns=[
            SourceColumn("key", "Key", "text", False),
            SourceColumn("title", "Title", "text", False, searchable=True, writable=True),
            SourceColumn("done", "Done", "boolean", False, writable=True),
            SourceColumn("rank", "Rank", "integer", True, writable=True),
            SourceColumn("score", "Score", "number", False, writable=True)])
        try:
            yield source, model
        finally:
            source.close()


def accept_headless():
    from backpack_store import RevisionConflictError, TransactionError
    checks = 0
    def check(condition):
        nonlocal checks
        if not condition:
            raise RuntimeError("Headless persistence acceptance failed.")
        checks += 1
    with TemporaryDirectory(prefix="headless-table-") as directory:
        path = Path(directory) / "items.sqlite"
        with headless_application(path) as (source, model):
            model.create(TableItem("a", "Zulu", "alice", rank=2))
            model.create(TableItem("b", "Alpha", "alice", rank=1))
            row = source.query(columns=["title", "key"], order=[("title", False)], search=dict(fields=["title"], term="Alpha")).rows[0]
            check((row.key, row.revision, row.source_addresses) == ("b", "1", ("title", "key")))
            result = source.edit(row.key, "title", "Headless saved", expected_revision=row.revision)
            check((result.key, result.revision) == ("b", "2"))
            check(model.get("a").value.title == "Zulu" and model.get("b").value.owner == "alice")
            with headless_application(path) as (other, _):
                try:
                    other.edit("b", "done", True, expected_revision="1")
                except RevisionConflictError:
                    check(True)
                else:
                    check(False)
                check(other.get("b") == result)
            try:
                source.edit("b", "title", "", expected_revision="2")
            except TransactionError:
                check(source.get("b") == result)
            else:
                check(False)
        with headless_application(path) as (reopened, _):
            check(reopened.get("b") == result)
    return dict(profile="cpython-tabular/1", consumer="headless-backpack", checks=checks, independent_reopen=True, passed=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check",))
    parser.parse_args()
    print(json.dumps(accept_headless(), sort_keys=True))


if __name__ == "__main__":
    main()
