"""Qualify the selected live sources and required checks without publishing."""

import argparse
import hashlib
from importlib import metadata
import json
from pathlib import Path
import platform
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tests", type=Path, default=ROOT / "tests")
    parser.add_argument("--expected", type=Path, default=ROOT / "docs/compatibility-v1.json")
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--isolated", action="store_true")
    args = parser.parse_args()
    import compose_application
    from compose_application.live import _dependencies
    _dependencies()
    if args.isolated:
        assert Path(compose_application.__file__).is_relative_to(Path(sys.prefix))
    expected = json.loads(args.expected.read_text(encoding="utf-8"))["live"]
    packages = {}
    for name in expected["packages"]:
        package = metadata.distribution(name)
        direct = json.loads(package.read_text("direct_url.json") or "{}")
        packages[name] = {"version": package.version, "revision": direct.get("vcs_info", {}).get("commit_id")}
    assert packages == expected["packages"], "Installed live sources differ from the selected profile."
    suite = unittest.defaultTestLoader.discover(str(args.tests), pattern="test_live*.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    package = Path(compose_application.__file__).parent
    receipt = {"profile": "cpython-live/1", "python": platform.python_version(), "os": platform.system(),
        "passed": result.wasSuccessful() and not result.skipped and result.testsRun >= 9,
        "tests": result.testsRun, "skipped": len(result.skipped), "failures": len(result.failures), "errors": len(result.errors),
        "packages": packages, "modules_sha256": {name: hashlib.sha256((package / name).read_bytes()).hexdigest()
            for name in ("live.py", "ui.py", "reference.py")}}
    if args.receipt:
        args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    assert receipt["passed"], "Required live acceptance failed or skipped."
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
