"""Build and smoke-test independent installed wheel and source distributions."""

import argparse
import os
from pathlib import Path
import subprocess
import shutil
import tempfile
import tomllib
import venv

ROOT = Path(__file__).resolve().parents[1]


def run(*arguments, cwd):
    subprocess.run([str(value) for value in arguments], cwd=cwd, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service", action="store_true", help="qualify the optional service profile in both installed artifacts")
    args = parser.parse_args()
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    if project["dependencies"]:
        raise RuntimeError("The initial package foundation declares no runtime dependencies.")
    with tempfile.TemporaryDirectory(prefix="compose-application-distributions-") as directory:
        work = Path(directory)
        artifacts = work / "artifacts"
        run("uv", "build", "--no-sources", "--out-dir", artifacts, cwd=ROOT)
        wheels = list(artifacts.glob("*.whl"))
        sources = list(artifacts.glob("*.tar.gz"))
        if len(wheels) != 1 or len(sources) != 1:
            raise RuntimeError("Expected one wheel and one source distribution.")
        shutil.copytree(ROOT / "tests", work / "tests", ignore=shutil.ignore_patterns("__pycache__"))
        for kind, artifact in (("wheel", wheels[0]), ("source", sources[0])):
            environment = work / kind
            venv.EnvBuilder(with_pip=False).create(environment)
            python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            run("uv", "pip", "install", "--python", python, "--no-deps", artifact, cwd=work)
            probe = "\n".join((
                "import importlib.metadata as metadata, pathlib, sys, compose_application",
                f"assert metadata.version('compose-application') == {project['version']!r}",
                f"assert metadata.metadata('compose-application')['Requires-Python'] == {project['requires-python']!r}",
                "assert all('extra ==' in item for item in metadata.requires('compose-application'))",
                "location = pathlib.Path(compose_application.__file__).resolve()",
                "assert location.is_relative_to(pathlib.Path(sys.prefix).resolve())",
                "assert location.with_name('py.typed').is_file()",
                "assert not any(name in sys.modules for name in ('backpack_store', 'enforce_type', 'expose_api', 'spatial_ui'))",
            ))
            run(python, "-I", "-c", probe, cwd=work)
            if args.service:
                run("uv", "pip", "install", "--python", python, str(artifact) + "[service]", cwd=work)
                run(python, "-I", "-c", "from expose_api.backpack import BackpackStore; from compose_application import application", cwd=work)
                for suite in ("test_service.py", "test_reference.py"):
                    run(python, "-I", "-W", "error::ResourceWarning", "-m", "unittest", "discover",
                        "-s", work / "tests", "-p", suite, "-v", cwd=work)
            print(f"Installed {kind} passed: {artifact.name}", flush=True)


if __name__ == "__main__":
    main()
