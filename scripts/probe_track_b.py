"""Run original workload prerequisites on CPython and an explicitly selected engine."""

import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
WORKLOAD = ROOT / "examples/track_b_work_items.py"


def probes():
    return [
        {"id": "domain-values", "imports": [], "source": "item={'key':'item-001','title':'Garden','done':False}\nitem['done']=True\nprint(item['key'],item['done'])\n"},
        {"id": "t-string-view", "imports": [], "source": "title='Garden'\nview=t'{title}'\nprint(view.strings,view.interpolations[0].value)\n"},
        {"id": "dataclass-fields", "imports": ["dataclasses"], "source": "from dataclasses import dataclass,fields\n@dataclass\nclass Item:\n title: str\nprint(fields(Item)[0].name,Item('Garden').title)\n"},
        {"id": "typing-reflection", "imports": ["typing"], "source": "from typing import get_type_hints\nclass Item:\n title: str\nprint(get_type_hints(Item)['title'] is str)\n"},
        {"id": "json-round-trip", "imports": ["json"], "source": "import json\nprint(json.loads(json.dumps({'done':True},allow_nan=False))['done'])\n"},
        {"id": "native-await", "imports": [], "source": "async def save(host):\n return await host.save('item-001','{}',1)\nprint('coroutine-defined')\n"},
        {"id": "original-workload", "imports": ["dataclasses", "json", "typing"], "source": WORKLOAD.read_text(encoding="utf-8") + "\nprint(dump_item(WorkItem('item-001','Garden'),'1'))\n"},
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, help="Explicit pocket-python checkout; never downloaded automatically")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    cases = probes()
    results = []
    for case in cases:
        result = subprocess.run([sys.executable, "-I", "-S", "-c", case["source"]],
                                capture_output=True, text=True, encoding="utf-8", timeout=10, check=True)
        results.append({"id": case["id"], "source_sha256": hashlib.sha256(case["source"].encode()).hexdigest(),
                        "cpython_stdout": result.stdout})
    receipt = {"schema_version": 1, "workload": "work-items/1", "source_kind": "original",
               "workload_sha256": hashlib.sha256(WORKLOAD.read_bytes()).hexdigest(),
               "cpython": platform.python_version(), "os": sys.platform, "machine": platform.machine(),
               "probes": results, "browser_acceptance": "not-run", "reduced_source": "not-qualified"}
    if args.runtime:
        runtime = args.runtime.resolve()
        revision = subprocess.check_output(["git", "-C", str(runtime), "rev-parse", "HEAD"], text=True).strip()
        if subprocess.check_output(["git", "-C", str(runtime), "status", "--porcelain", "--untracked-files=no"], text=True).strip():
            raise RuntimeError("Runtime checkout has tracked changes; use an immutable clean revision.")
        result = subprocess.run(["node", str(ROOT / "scripts/probe_track_b.mjs"), str(runtime)],
                                input=json.dumps(cases), capture_output=True, text=True, timeout=30, check=True)
        engine = json.loads(result.stdout)
        engine["revision"] = revision
        if [row["id"] for row in engine["results"]] != [case["id"] for case in cases]:
            raise RuntimeError("Engine probe receipt does not match the requested cases.")
        for expected, actual in zip(results, engine["results"], strict=True):
            if actual["id"] == "domain-values" and actual["status"] != "supported":
                raise RuntimeError("The accepted domain-values prerequisite regressed.")
            if actual["status"] == "supported" and actual["stdout"] != expected["cpython_stdout"]:
                raise RuntimeError("Supported runtime probe differs from CPython: " + actual["id"])
        receipt["engine"] = engine
    rendered = json.dumps(receipt, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    print(f"Checked {len(cases)} CPython prerequisites; browser acceptance remains gated.", file=sys.stderr)


if __name__ == "__main__":
    main()
