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
assert not any(name in sys.modules for name in ("backpack_store", "enforce_type", "expose_api", "spatial_ui", "headless_spreadsheets"))
assert all(__import__("importlib.util").util.find_spec(name) is None for name in ("backpack_store", "enforce_type", "expose_api", "spatial_ui", "headless_spreadsheets"))
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
    run(python, "-I", "-W", "error::ResourceWarning", "-m", "unittest", "discover",
        "-s", work / "tests", "-p", "test_ui.py", "-k", "loopback_preview_startup", "-v", cwd=work)
    reference = json.loads(run(python, "-I", "-m", "compose_application.ui", "check", cwd=work, capture=True))
    if reference["checks"] != 15 or reference["process_restart"] is not True:
        raise RuntimeError("UI acceptance did not provide the complete restart receipt.")
    return {"packages": packages, "reference": reference}


def qualify_live(python, work):
    path = work / "live-receipt.json"
    run(python, "-I", "-W", "error::ResourceWarning", ROOT / "scripts/check_live_profile.py",
        "--tests", work / "tests", "--expected", ROOT / "docs/compatibility-v1.json",
        "--isolated", "--receipt", path, cwd=work)
    receipt = json.loads(path.read_text(encoding="utf-8"))
    if not receipt["passed"] or receipt["skipped"] or receipt["tests"] < 9:
        raise RuntimeError("Installed live acceptance did not provide complete native/process evidence.")
    return receipt


def tabular_provenance(python, work, expected, *, editing=True):
    probe = '''
import hashlib, importlib, importlib.metadata as m, json, pathlib, sys
result = {}
for name in ("expose-api", "spatial-ui", "backpack-store", "enforce-type", "headless-spreadsheets"):
    package = m.distribution(name)
    direct = json.loads(package.read_text("direct_url.json") or "{}")
    result[name] = {"version": package.version, "revision": direct.get("vcs_info", {}).get("commit_id")}
modules = {}
for module, source in (("expose_api", "tabular.py"), ("spatial_ui", "table_binding.py"),
                       ("spatial_ui", "static/runtime.js"), ("headless_spreadsheets", "sources.py")):
    root = pathlib.Path(importlib.import_module(module).__file__).parent
    assert root.is_relative_to(pathlib.Path(sys.prefix))
    modules[module + "/" + source] = hashlib.sha256(root.joinpath(source).read_bytes()).hexdigest()
if sys.argv[1] == "editing":
    from headless_spreadsheets.backpack import BackpackSource
    root = pathlib.Path(importlib.import_module("headless_spreadsheets").__file__).parent
    modules["headless_spreadsheets/backpack.py"] = hashlib.sha256(root.joinpath("backpack.py").read_bytes()).hexdigest()
composition = m.distribution("compose-application")
direct = json.loads(composition.read_text("direct_url.json") or "{}")
print(json.dumps({"packages": result, "module_sha256": modules,
    "composition": {"version":composition.version,"revision":direct.get("vcs_info",{}).get("commit_id")}}))
'''
    receipt = json.loads(run(python, "-I", "-c", probe, "editing" if editing else "read-only", cwd=work, capture=True))
    if receipt["packages"] != expected:
        raise RuntimeError("Installed tabular sources differ from the qualified profile.")
    run("uv", "pip", "check", "--python", python, cwd=work)
    return receipt


def tabular_state(python, work, database):
    probe = '''
import asyncio, hashlib, json, sys
from dataclasses import asdict
from compose_application.tabular import tabular_application
async def main():
    async with tabular_application(sys.argv[1], seed=False) as service:
        values = await service.store.list(limit=1000)
        rows = [await service.store.get_row(value.key) for value in values]
        retained = [[r.key, r.revision, asdict(r.value)] for r in rows if r.key not in {"item-055", "item-056", "item-057"}]
        print(json.dumps({"rows": len(rows), "retained_rows": len(retained),
            "sha256": hashlib.sha256(json.dumps(retained,sort_keys=True).encode()).hexdigest(),
            "prior_writer_revision": next(r.revision for r in rows if r.key == "item-095")}))
asyncio.run(main())
'''
    return json.loads(run(python, "-I", "-c", probe, database, cwd=work, capture=True))


def qualify_tabular_upgrade(minimum_python, python, work, kind, minimum):
    database = work / (kind + "-tabular-upgrade.sqlite")
    seed = "import asyncio,json,sys; from compose_application.tabular import accept_phase; print(json.dumps(asyncio.run(accept_phase(sys.argv[1],'seed'))))"
    previous = json.loads(run(minimum_python, "-I", "-c", seed, database, cwd=work, capture=True))
    previous.pop("continuation")
    before = tabular_state(minimum_python, work, database)
    phases = []
    edit = "import asyncio,json,sys; from compose_application.tabular_edits import edit_phase; print(json.dumps(asyncio.run(edit_phase(sys.argv[1],sys.argv[2]))))"
    for phase in ("write", "reopen"):
        phases.append(json.loads(run(python, "-I", "-c", edit, database, phase, cwd=work, capture=True)))
    after = tabular_state(python, work, database)
    if before != after or before["rows"] != 120 or before["retained_rows"] != 117 or before["prior_writer_revision"] != "2":
        raise RuntimeError("Code/dependency upgrade changed unrelated durable rows or revisions.")
    if not previous["passed"] or any(not r["passed"] or not r["closed"] for r in phases):
        raise RuntimeError("Tabular upgrade did not provide complete process/close evidence.")
    return {"from_revision": minimum["composition_revision"], "minimum": previous, "current": phases,
            "retained": after, "process_restart": True, "passed": True}


def qualify_tabular(python, work, *, browser=False):
    expected = json.loads((ROOT / "docs/tabular-sources-v1.json").read_text())["packages"]
    receipt = tabular_provenance(python, work, expected)
    checks = '''
import json,sys,unittest
from pathlib import Path
# Only copied test support/fixtures live here; implementation imports stay installed.
sys.path.insert(0, str(Path(sys.argv[1]).parent))
suite = unittest.defaultTestLoader.discover(sys.argv[1], pattern="test_tabular*.py")
result = unittest.TextTestRunner(verbosity=2).run(suite)
assert result.wasSuccessful() and not result.skipped and result.testsRun == 9
print(json.dumps({"tests":result.testsRun,"skipped":len(result.skipped),"passed":True}))
'''
    receipt["reference"] = json.loads(run(python, "-I", "-W", "error::ResourceWarning", "-c", checks, work / "tests", cwd=work, capture=True))
    receipt.update(profile="cpython-tabular/1", reference_tests=9, read_only_http_checks=18, editable_http_checks=27,
                   headless_checks=7, process_restart=True, independent_consumers=True)
    if browser:
        requirement, = tomllib.loads((ROOT / "pyproject.toml").read_text())["dependency-groups"]["browser-tests"]
        run("uv", "pip", "install", "--python", python, requirement, cwd=work)
        browser_checks = '''
import sys,unittest
suite = unittest.defaultTestLoader.discover(sys.argv[1], pattern="browser_tabular*.py")
result = unittest.TextTestRunner(verbosity=2).run(suite)
assert result.wasSuccessful() and not result.skipped and result.testsRun == 2
'''
        run(python, "-I", "-W", "error::ResourceWarning", "-c", browser_checks, work / "tests", cwd=work)
        receipt["browser"] = {name: json.loads((work / filename).read_text()) for name, filename in (
            ("read_only", "tabular-browser-receipt.json"), ("editable", "tabular-edit-browser-receipt.json"))}
        if any(value.get("passed") is not True for value in receipt["browser"].values()):
            raise RuntimeError("Installed Chromium qualification did not pass.")
    return receipt


def qualify_validation(python, work, expected):
    probe = '''
import hashlib, importlib.metadata as metadata, json, pathlib, sys
import enforce_type
from expose_api.enforce_type import EnforceTypeSchema
packages = {}
for name in ("expose-api", "backpack-store", "enforce-type"):
    distribution = metadata.distribution(name)
    direct = json.loads(distribution.read_text("direct_url.json") or "{}")
    packages[name] = {"version": distribution.version, "revision": direct.get("vcs_info", {}).get("commit_id")}
root = pathlib.Path(enforce_type.__file__).parent
assert root.is_relative_to(pathlib.Path(sys.prefix))
digest = hashlib.sha256()
for path in sorted(root.rglob("*")):
    if path.is_file() and (path.suffix == ".py" or path.name == "py.typed"):
        digest.update(path.relative_to(root).as_posix().encode() + b"\\0" + path.read_bytes())
print(json.dumps({"packages": packages, "engine_source_sha256": digest.hexdigest()}))
'''
    receipt = json.loads(run(python, "-I", "-c", probe, cwd=work, capture=True))
    if receipt["packages"] != expected["packages"] or receipt["engine_source_sha256"] != expected["engine_source_sha256"]:
        raise RuntimeError("Installed validation packages differ from their qualified source profile.")
    run("uv", "pip", "check", "--python", python, cwd=work)
    checks = '''
import json, sys, unittest
suite = unittest.TestLoader().discover(sys.argv[1], pattern="test_validation.py")
result = unittest.TextTestRunner(verbosity=2).run(suite)
assert result.wasSuccessful() and not result.skipped and result.testsRun == 5
print(json.dumps({"tests": result.testsRun, "skipped": len(result.skipped), "passed": True}))
'''
    receipt["lifecycle"] = json.loads(run(python, "-I", "-W", "error::ResourceWarning", "-c", checks,
                                          work / "tests", cwd=work, capture=True))
    receipt["reference"] = json.loads(run(python, "-I", "-W", "error::ResourceWarning", "-m",
        "compose_application.reference", "check", "--validation", "enforce-type", cwd=work, capture=True))
    reference = receipt["reference"]
    if (reference.get("profile") != expected["profile"] or reference.get("checks") != 16
            or reference.get("process_restart") is not True
            or [phase.get("phase") for phase in reference["phases"]] != ["write", "reload"]
            or not all(phase.get("passed") is True for phase in reference["phases"])):
        raise RuntimeError("Validation reference did not provide complete checked HTTP/process acceptance.")
    return receipt


def qualify_projects(generator, work, kind, manifest, stage):
    """Install the emitted projects normally, including their immutable dependencies."""
    receipts = []
    for profile, count in (("service", 9), ("ui", 15), ("live", 15)):
        name = "reference-" + profile
        module = name.replace("-", "_")
        destination = work / (kind + "-" + name)
        stage(kind + "/generated-" + profile)
        command = (generator, "-I", "-m", "compose_application.projects", destination,
                   "--name", name, "--profile", profile)
        creation = json.loads(run(*command, cwd=work, capture=True))
        if creation["created"] is not True:
            raise RuntimeError("Installed generator did not create the selected project.")
        selection = creation["selection"]
        project = tomllib.loads((destination / "pyproject.toml").read_text(encoding="utf-8"))["project"]
        expected_dependency = f"compose-application[{profile}] @ git+https://github.com/wispsy/compose_application.git@{selection['source']}"
        if project["dependencies"] != [expected_dependency]:
            raise RuntimeError("Generated project selected unexpected dependencies.")
        digest = package_digest(destination / "src" / module)
        python = environment(work / (kind + "-" + profile + "-environment"))
        # Resolve the generated dependency declaration without overrides/no-deps.
        run("uv", "pip", "install", "--python", python, destination, cwd=work)
        run("uv", "pip", "check", "--python", python, cwd=work)
        probe = f'''
import hashlib, importlib.metadata as metadata, importlib.util, json, pathlib, sys
import {module} as application
assert not any(name in sys.modules for name in ("expose_api", "spatial_ui", "backpack_store", "enforce_type"))
path = pathlib.Path(application.__file__).resolve().parent
assert path.is_relative_to(pathlib.Path(sys.prefix).resolve())
digest = hashlib.sha256()
for source in sorted(path.rglob("*")):
    if source.is_file() and source.suffix == ".py":
        digest.update(source.relative_to(path).as_posix().encode() + b"\\0" + source.read_bytes())
packages = {{}}
for name in ("compose-application", "expose-api", "backpack-store", "enforce-type", "spatial-ui"):
    try:
        distribution = metadata.distribution(name)
    except metadata.PackageNotFoundError:
        assert name == "spatial-ui" and {profile!r} == "service"
        continue
    direct = json.loads(distribution.read_text("direct_url.json") or "{{}}")
    packages[name] = {{"version": distribution.version, "revision": direct.get("vcs_info", {{}}).get("commit_id")}}
print(json.dumps({{"packages": packages, "source_sha256": digest.hexdigest(), "import_isolated": True}}))
'''
        installed = json.loads(run(python, "-I", "-c", probe, cwd=work, capture=True))
        expected = {**manifest["current"]["packages"], "compose-application": {
            "version": "0.1.0.dev0", "revision": selection["source"]}}
        if profile != "service":
            expected.update(manifest["ui"]["packages"])
        if installed["packages"] != expected or installed["source_sha256"] != digest:
            raise RuntimeError("Generated project dependency/source provenance differs from its selection.")
        entry = python.parent / (name + (".exe" if os.name == "nt" else ""))
        accepted = json.loads(run(entry, "check", cwd=work, capture=True))
        if (accepted.get("passed") is not True or accepted.get("checks") != count
                or accepted.get("profile") != profile or accepted.get("process_restart") is not True
                or [phase.get("phase") for phase in accepted["phases"]] != ["write", "reload"]
                or not all(phase.get("closed") is True for phase in accepted["phases"])):
            raise RuntimeError("Generated command did not provide complete process/lifecycle acceptance.")
        # A normal repeat after source edits and an existing data file must leave
        # both bytes and modification times untouched; it is not a refresh mode.
        source = destination / "src" / module / "app.py"
        source.write_text(source.read_text(encoding="utf-8") + "\n# Application-owned change.\n", encoding="utf-8")
        (destination / "owner.sqlite3").write_bytes(b"synthetic preservation fixture")
        before = {path.relative_to(destination): (path.read_bytes(), path.stat().st_mtime_ns)
                  for path in destination.rglob("*") if path.is_file()}
        repeated = json.loads(run(*command, cwd=work, capture=True))
        after = {path.relative_to(destination): (path.read_bytes(), path.stat().st_mtime_ns)
                 for path in destination.rglob("*") if path.is_file()}
        if repeated["created"] is not False or repeated["selection"] != selection or before != after:
            raise RuntimeError("Repeated generation changed application-owned files or data.")
        receipts.append({"selection": selection, **installed, "acceptance": accepted,
                         "repeat_preserved": True, "command": "installed-console-script",
                         "dependency_resolution": "declared-immutable-sources"})
    return receipts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service", action="store_true", help="qualify the optional service profile in both installed artifacts")
    parser.add_argument("--matrix", action="store_true", help="qualify the finite minimum/current matrix and code upgrades")
    parser.add_argument("--ui", action="store_true", help="qualify the optional typed UI in both installed artifacts")
    parser.add_argument("--live", action="store_true", help="qualify protected native/process live checks in both artifacts")
    parser.add_argument("--projects", action="store_true", help="install and check generated service/ui/live projects from both artifacts")
    parser.add_argument("--validation", action="store_true", help="qualify the separate compiled validation service profile in both artifacts")
    parser.add_argument("--tabular", action="store_true", help="qualify read-only/editable/headless table profiles and retained-data upgrades")
    parser.add_argument("--tabular-browser", action="store_true", help="run actual Chromium from each isolated tabular artifact installation")
    parser.add_argument("--report", type=Path, help="write a machine-readable receipt, including failure phase")
    args = parser.parse_args()
    if args.tabular_browser and not args.tabular:
        parser.error("--tabular-browser requires --tabular")
    if args.tabular and (sys.implementation.name != "cpython" or sys.version_info[:2] != (3, 14)
                        or platform.system() not in ("Linux", "Darwin", "Windows")):
        parser.error("The tabular profile qualifies CPython 3.14 on Linux, macOS and Windows.")
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    if project["dependencies"]:
        raise RuntimeError("The initial package foundation declares no runtime dependencies.")
    manifest = json.loads((ROOT / "docs/compatibility-v1.json").read_text()) if args.matrix or args.ui or args.live or args.projects or args.validation else None
    if args.matrix and (sys.implementation.name != "cpython" or sys.version_info[:2] != (3, 14)
                        or platform.system() not in manifest["operating_systems"]):
        parser.error("This finite matrix qualifies CPython 3.14 on Linux, macOS and Windows.")
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    changes = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT, capture_output=True, text=True)
    report = {"format": "composition-compatibility/1", "python": platform.python_version(), "machine": platform.machine(),
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
            tabular_minimum_python = None
            if args.tabular:
                (work / "scripts").mkdir()
                for name in ("check_contracts.py", "check_tabular.py"):
                    shutil.copy2(ROOT / "scripts" / name, work / "scripts" / name)
                (work / "docs" / "contracts").mkdir(parents=True)
                shutil.copy2(ROOT / "docs/contracts/tabular-v1.json", work / "docs/contracts/tabular-v1.json")
                tabular_manifest = json.loads((ROOT / "docs/tabular-compatibility-v1.json").read_text())
                minimum = tabular_manifest["minimum"]
                stage("tabular-minimum/install")
                tabular_minimum_python = environment(work / "tabular-minimum")
                source = "compose-application[tabular] @ git+https://github.com/wispsy/compose_application.git@" + minimum["composition_revision"]
                run("uv", "pip", "install", "--python", tabular_minimum_python, source, cwd=work)
                report["tabular_minimum"] = tabular_provenance(tabular_minimum_python, work, minimum["packages"], editing=False)
                if report["tabular_minimum"]["composition"] != {"version": minimum["composition_version"], "revision": minimum["composition_revision"]}:
                    raise RuntimeError("The tabular minimum differs from its immutable composition source.")
            if args.matrix:
                minimum = manifest["minimum"]
                minimum_python = environment(work / "minimum")
                source = "git+https://github.com/wispsy/compose_application.git@" + minimum["composition_revision"]
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
                if args.live:
                    stage(kind + "/live-install")
                    run("uv", "pip", "install", "--python", python, str(artifact) + "[live]", cwd=work)
                    stage(kind + "/live-native-process")
                    receipt["live"] = qualify_live(python, work)
                if minimum_python is not None:
                    stage(kind + "/minimum-to-current-upgrade")
                    database = work / ("upgrade-" + kind + ".sqlite3")
                    receipt["upgrade"] = [upgrade_phase(minimum_python, work, database, "write"),
                                           upgrade_phase(python, work, database, "reload")]
                if args.projects:
                    receipt["projects"] = qualify_projects(python, work, kind, manifest, stage)
                if args.validation:
                    stage(kind + "/validation-install")
                    validation_python = environment(work / (kind + "-validation"))
                    run("uv", "pip", "install", "--python", validation_python, str(artifact) + "[validation]", cwd=work)
                    stage(kind + "/validation-reference")
                    receipt["validation"] = qualify_validation(validation_python, work, manifest["validation"])
                if args.tabular:
                    stage(kind + "/tabular-install")
                    tabular_python = environment(work / (kind + "-tabular"))
                    run("uv", "pip", "install", "--python", tabular_python, str(artifact) + "[tabular]", cwd=work)
                    stage(kind + "/tabular-reference")
                    receipt["tabular"] = qualify_tabular(tabular_python, work, browser=args.tabular_browser)
                    stage(kind + "/tabular-retained-upgrade")
                    receipt["tabular"]["upgrade"] = qualify_tabular_upgrade(tabular_minimum_python, tabular_python, work, kind, minimum=tabular_manifest["minimum"])
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
