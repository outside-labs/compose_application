"""Explicit selections for application-owned reference projects."""

from dataclasses import dataclass
import argparse
import json
import keyword
import os
from pathlib import Path
import re
import sys
from tempfile import TemporaryDirectory


REFERENCE_REVISION = "64fdd88efec0238fa5a224d490cabd5e6a49c766"
PROFILES = ("service", "ui", "live")
_RESERVED = set(sys.stdlib_module_names) | {
    "compose_application", "expose_api", "backpack_store", "enforce_type", "spatial_ui",
    "con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
}


@dataclass(frozen=True)
class ProjectSpec:
    """A finite reference selection, with no imports, I/O or implicit profile."""

    name: str
    profile: str
    source: str = REFERENCE_REVISION

    def __post_init__(self):
        if type(self.name) is not str or not 1 <= len(self.name) <= 48 or not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", self.name):
            raise ValueError("Choose a lowercase project name of 1–48 letters, digits and single hyphens.")
        if keyword.iskeyword(self.module) or self.module in _RESERVED:
            raise ValueError("Choose a project name that does not shadow a platform or Python module.")
        if type(self.profile) is not str or self.profile not in PROFILES:
            raise ValueError("Select service, ui or live explicitly.")
        if type(self.source) is not str or self.source != REFERENCE_REVISION:
            raise ValueError("Select the qualified immutable reference source.")

    @property
    def module(self):
        return self.name.replace("-", "_")

    @property
    def dependency(self):
        return f"compose-application[{self.profile}] @ git+https://github.com/outside-labs/compose_application.git@{self.source}"

    def selection(self):
        """Return detached, non-secret generation metadata, independent of data schema."""
        return {"format": "reference-project/1", "name": self.name,
                "profile": self.profile, "source": self.source}


def render_project(spec: ProjectSpec):
    """Return detached UTF-8 source files without writing or installing anything."""
    if type(spec) is not ProjectSpec:
        raise TypeError("render_project() requires ProjectSpec.")
    if spec.profile == "live":
        raise ValueError("This renderer currently supports service and ui references.")
    from .project_templates import COMMAND, HTTP_CHECKS, SERVICE_APP, SERVICE_PHASE, UI_APP, UI_PHASE
    app_source, phase_source = (SERVICE_APP, SERVICE_PHASE) if spec.profile == "service" else (UI_APP, UI_PHASE)
    metadata = f'''[project]
name = "{spec.name}"
version = "0.1.0"
requires-python = ">=3.14"
dependencies = ["{spec.dependency}"]

[project.scripts]
{spec.name} = "{spec.module}.__main__:main"

[build-system]
requires = ["uv_build>=0.12.19,<0.13.0"]
build-backend = "uv_build"
'''
    readme = f'''# {spec.name}

Application-owned `{spec.profile}` reference project for synthetic work items.
Composition source: `{spec.source}`. Python 3.14+ and uv are required.

```sh
uv sync
uv run {spec.name} check
uv run {spec.name} serve --database ./work-items.sqlite3
```

The check uses a dedicated temporary database in two independent processes.
Serving uses a loopback development listener with public synthetic data and
checked REST revisions. Choose a private persistent local SQLite path explicitly.
Application assembly and checks live in `src/{spec.module}/`; these files and
the database belong to you. The selected reference owns its fixed work-item
schema. Domain/schema changes require their own implementation and migration.
Dependencies use qualified development sources, not published release promises.
Generation installs nothing and repeating the same request never updates files.
Publication and public hosting require separate setup.
'''
    if spec.profile == "ui":
        readme += "\nThe UI opens at the printed loopback address. Browser drafts are independent;\nSave uses checked revisions. Load refreshes the baseline while retaining edits\nfor an explicit merge; Discard replaces the draft with that baseline. Shutdown\nstops the UI listener/worker before closing REST and storage.\n"
    checks = (HTTP_CHECKS + phase_source).replace("__PROJECT_MODULE__", spec.module).replace("__PROJECT_PROFILE__", spec.profile)
    return {"pyproject.toml": metadata, "README.md": readme,
            ".gitignore": ".venv/\n__pycache__/\n*.py[cod]\n*.sqlite3*\n.env\n",
            "reference-project.json": json.dumps(spec.selection(), indent=2, sort_keys=True) + "\n",
            f"src/{spec.module}/__init__.py": '"""Application-owned reference project."""\n',
            f"src/{spec.module}/app.py": app_source,
            f"src/{spec.module}/__main__.py": COMMAND,
            f"src/{spec.module}/checks.py": checks}


def _existing_selection(destination, spec):
    if destination.is_symlink():
        raise FileExistsError("Project destination must not be a symbolic link.")
    if not destination.exists():
        return False
    receipt = destination / "reference-project.json"
    try:
        if not destination.is_dir() or receipt.is_symlink() or not receipt.is_file() or receipt.stat().st_size > 4096:
            raise ValueError
        selected = json.loads(receipt.read_text(encoding="utf-8"))
        if selected != spec.selection():
            raise ValueError
    except (OSError, ValueError):
        raise FileExistsError("Destination exists without a matching project selection; no files were changed.") from None
    return True


def create_project(spec: ProjectSpec, destination):
    """Stage a new project and exclusively create its files; return True if created.

    Matching repeat requests return False without examining or changing owned
    source/data. The parent must exist. An incomplete project has no receipt.
    """
    files = render_project(spec)
    destination = Path(destination).absolute()
    if _existing_selection(destination, spec):
        return False
    # All template paths are internal, relative and validated before any write.
    for name in files:
        path = Path(name)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("Project template contains an invalid path.")
    with TemporaryDirectory(prefix=".reference-project-", dir=destination.parent) as directory:
        stage = Path(directory)
        for name, content in files.items():
            path = stage / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
        try:
            destination.mkdir()
        except FileExistsError:
            if _existing_selection(destination, spec):
                return False
            raise
        created, directories = [], []
        try:
            # Publish the receipt last, after all application files exist.
            names = [name for name in files if name != "reference-project.json"] + ["reference-project.json"]
            for name in names:
                path = destination / name
                for parent in reversed(path.relative_to(destination).parents):
                    if parent == Path("."):
                        continue
                    target = destination / parent
                    if target not in directories:
                        target.mkdir()
                        directories.append(target)
                # Same-filesystem hard links publish complete files exclusively
                # without a partial-write window or overwriting a raced file.
                os.link(stage / name, path)
                created.append(path)
        except BaseException:
            # Remove only our own unchanged files. Concurrent owner additions
            # and edits survive; nonempty directories are never removed.
            for path in reversed(created):
                try:
                    expected = files[path.relative_to(destination).as_posix()]
                    if not path.is_symlink() and path.read_text(encoding="utf-8") == expected:
                        path.unlink()
                except OSError:
                    pass
            for path in [*reversed(directories), destination]:
                try:
                    path.rmdir()
                except OSError:
                    pass
            raise
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--name", required=True)
    parser.add_argument("--profile", choices=PROFILES, required=True)
    arguments = parser.parse_args()
    try:
        spec = ProjectSpec(arguments.name, arguments.profile)
        created = create_project(spec, arguments.destination)
    except (OSError, ValueError) as error:
        parser.exit(2, f"Project creation refused: {error}\n")
    print(json.dumps({"created": created, "selection": spec.selection()}, sort_keys=True))


if __name__ == "__main__":
    main()
