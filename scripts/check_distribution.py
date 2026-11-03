"""Build and smoke-test independent installed wheel and source distributions."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import shutil
import sys
import tempfile
import tomllib
import venv

ROOT = Path(__file__).resolve().parents[1]


def run(*arguments, cwd, capture=False):
    result = subprocess.run([str(value) for value in arguments], cwd=cwd,
                            capture_output=capture, text=capture)
    if result.returncode and capture and result.stderr:
        print(result.stderr[-12000:], file=sys.stderr)
    result.check_returncode()
    return result.stdout if capture else None


def environment(path):
    venv.EnvBuilder(with_pip=False).create(path)
    return path / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def package_digest(directory):
    digest = hashlib.sha256()
    for path in sorted(directory.rglob("*")):
        if path.is_file() and (path.suffix == ".py" or path.name == "py.typed"):
            digest.update(path.relative_to(directory).as_posix().encode() + b"\0" + path.read_bytes())
    return digest.hexdigest()


def base_probe(python, work, version):
    probe = f'''
import hashlib, importlib.metadata as metadata, json, pathlib, sys, compose_application
assert metadata.version("compose-application") == {version!r}
assert metadata.metadata("compose-application")["Requires-Python"] == ">=3.14"
assert all("extra ==" in item for item in metadata.requires("compose-application") or [])
location = pathlib.Path(compose_application.__file__).resolve()
assert location.is_relative_to(pathlib.Path(sys.prefix).resolve())
assert location.with_name("py.typed").is_file()
assert not any(name in sys.modules for name in ("backpack_store", "enforce_type", "expose_api", "spatial_ui"))
assert all(__import__("importlib.util").util.find_spec(name) is None for name in ("backpack_store", "enforce_type", "expose_api", "spatial_ui"))
digest = hashlib.sha256()
for path in sorted(location.parent.rglob("*")):
    if path.is_file() and (path.suffix == ".py" or path.name == "py.typed"):
        digest.update(path.relative_to(location.parent).as_posix().encode() + b"\\0" + path.read_bytes())
print(json.dumps({{"base_isolated": True, "package_sha256": digest.hexdigest()}}))
'''
    return json.loads(run(python, "-I", "-c", probe, cwd=work, capture=True))


def qualify_profile(python, work, expected, stage):
    stage("dependency-provenance")
    probe = '''
import importlib.metadata as metadata, json
from expose_api import App
from expose_api.backpack import BackpackStore
result = {}
for name in ("compose-application", "expose-api", "backpack-store", "enforce-type"):
    distribution = metadata.distribution(name)
    direct = json.loads(distribution.read_text("direct_url.json") or "{}")
    result[name] = {"version": distribution.version, "revision": direct.get("vcs_info", {}).get("commit_id")}
available = callable(getattr(App, "openapi", None))
if available:
    assert App().openapi()["openapi"] == "3.1.0"
print(json.dumps({"packages": result, "openapi": available}))
'''
    receipt = json.loads(run(python, "-I", "-c", probe, cwd=work, capture=True))
    if expected is not None:
        for name, package in expected["packages"].items():
            if receipt["packages"].get(name) != package:
                raise RuntimeError(f"Installed {name} does not match its qualified source/version profile.")
        if receipt["openapi"] is not expected["openapi"]:
            raise RuntimeError("The API capability probe does not match the selected profile.")
        if "composition_revision" in expected and receipt["packages"]["compose-application"] != {
                "version": expected["compose_version"], "revision": expected["composition_revision"]}:
            raise RuntimeError("The minimum composition installation does not match its immutable revision.")
    stage("dependency-consistency")
    run("uv", "pip", "check", "--python", python, cwd=work)
    stage("lifecycle")
    run(python, "-I", "-W", "error::ResourceWarning", "-m", "unittest", "discover",
        "-s", work / "tests", "-p", "test_service.py", "-v", cwd=work)
    stage("concurrent-checked-http")
    run(python, "-I", "-W", "error::ResourceWarning", "-m", "unittest", "discover",
        "-s", work / "tests", "-p", "test_reference.py", "-k", "concurrent_checked", "-v", cwd=work)
    stage("reference-process-restart")
    receipt["reference"] = json.loads(run(python, "-I", "-m", "compose_application.reference", "check", cwd=work, capture=True))
    if receipt["reference"]["checks"] != 16 or receipt["reference"]["process_restart"] is not True:
        raise RuntimeError("Reference acceptance did not provide the complete restart receipt.")
    return receipt


def upgrade_phase(python, work, database, phase):
    code = "import asyncio,json,sys; from compose_application.reference import _accept_phase; print(json.dumps(asyncio.run(_accept_phase(sys.argv[1],sys.argv[2]))))"
    return json.loads(run(python, "-I", "-c", code, database, phase, cwd=work, capture=True))


def qualify_ui(python, work, expected):
    probe = '''
import importlib.metadata as metadata, json
distribution = metadata.distribution("spatial-ui")
direct = json.loads(distribution.read_text("direct_url.json") or "{}")
print(json.dumps({"spatial-ui": {"version": distribution.version, "revision": direct.get("vcs_info", {}).get("commit_id")}}))
'''
    packages = json.loads(run(python, "-I", "-c", probe, cwd=work, capture=True))
    if packages != expected["packages"]:
        raise RuntimeError("Installed UI packages do not match their qualified source profile.")
    reference = json.loads(run(python, "-I", "-m", "compose_application.ui", "check", cwd=work, capture=True))
    if reference["checks"] != 15 or reference["process_restart"] is not True:
        raise RuntimeError("UI acceptance did not provide the complete restart receipt.")
    return {"packages": packages, "reference": reference}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service", action="store_true", help="qualify the optional service profile in both installed artifacts")
    parser.add_argument("--matrix", action="store_true", help="qualify the finite minimum/current matrix and code upgrades")
    parser.add_argument("--ui", action="store_true", help="qualify the optional typed UI in both installed artifacts")
    parser.add_argument("--report", type=Path, help="write a machine-readable receipt, including failure phase")
    args = parser.parse_args()
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    if project["dependencies"]:
        raise RuntimeError("The initial package foundation declares no runtime dependencies.")
    manifest = json.loads((ROOT / "docs/compatibility-v1.json").read_text()) if args.matrix or args.ui else None
    if args.matrix and (sys.implementation.name != "cpython" or sys.version_info[:2] != (3, 14)
                        or platform.system() not in manifest["operating_systems"]):
        parser.error("This finite matrix qualifies CPython 3.14 on Linux, macOS and Windows.")
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    changes = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT, capture_output=True, text=True)
    report = {"format": "composition-compatibility/1", "python": platform.python_version(),
              "os": platform.system(), "source_revision": revision.stdout.strip() if revision.returncode == 0 else None,
              "source_clean": changes.returncode == 0 and not changes.stdout.strip(), "passed": False, "profiles": []}
    def stage(name):
        report["phase"] = name
    try:
        with tempfile.TemporaryDirectory(prefix="compose-application-distributions-") as directory:
            work, minimum_python = Path(directory), None
            stage("build")
            artifacts = work / "artifacts"
            run("uv", "build", "--no-sources", "--out-dir", artifacts, cwd=ROOT)
            wheels, sources = list(artifacts.glob("*.whl")), list(artifacts.glob("*.tar.gz"))
            if len(wheels) != 1 or len(sources) != 1:
                raise RuntimeError("Expected one wheel and one source distribution.")
            shutil.copytree(ROOT / "tests", work / "tests", ignore=shutil.ignore_patterns("__pycache__"))
            if args.matrix:
                minimum = manifest["minimum"]
                minimum_python = environment(work / "minimum")
                source = "git+https://github.com/outside-labs/compose_application.git@" + minimum["composition_revision"]
                stage("minimum/base-install")
                run("uv", "pip", "install", "--python", minimum_python, "--no-deps", "compose-application @ " + source, cwd=work)
                receipt = {"name": "minimum", **base_probe(minimum_python, work, minimum["compose_version"])}
                report["profiles"].append(receipt)
                stage("minimum/optional-install")
                run("uv", "pip", "install", "--python", minimum_python, "compose-application[service] @ " + source, cwd=work)
                receipt.update(qualify_profile(minimum_python, work, minimum, lambda name: stage("minimum/" + name)))
            for kind, artifact in (("wheel", wheels[0]), ("source", sources[0])):
                python = environment(work / kind)
                stage(kind + "/base-install")
                run("uv", "pip", "install", "--python", python, "--no-deps", artifact, cwd=work)
                receipt = {"name": "current-" + kind, "artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                           **base_probe(python, work, project["version"])}
                report["profiles"].append(receipt)
                if receipt["package_sha256"] != package_digest(ROOT / "src/compose_application"):
                    raise RuntimeError("Installed package bytes differ from the candidate source.")
                if args.service or args.matrix or args.ui:
                    stage(kind + "/optional-install")
                    run("uv", "pip", "install", "--python", python, str(artifact) + "[service]", cwd=work)
                    receipt.update(qualify_profile(python, work, manifest["current"] if manifest else None,
                                                  lambda name: stage(kind + "/" + name)))
                if args.ui:
                    stage(kind + "/ui-install")
                    run("uv", "pip", "install", "--python", python, str(artifact) + "[ui]", cwd=work)
                    stage(kind + "/ui-reference")
                    receipt["ui"] = qualify_ui(python, work, manifest["ui"])
                if minimum_python is not None:
                    stage(kind + "/minimum-to-current-upgrade")
                    database = work / ("upgrade-" + kind + ".sqlite3")
                    receipt["upgrade"] = [upgrade_phase(minimum_python, work, database, "write"),
                                           upgrade_phase(python, work, database, "reload")]
                print(f"Installed {kind} passed: {artifact.name}", flush=True)
        report["passed"], report["phase"] = True, "complete"
    except Exception as error:
        report["failure_type"] = type(error).__name__
        raise
    finally:
        if args.report:
            args.report.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")


if __name__ == "__main__":
    main()
