"""Explicit selections for application-owned reference projects."""

from dataclasses import dataclass
import json
import keyword
import re
import sys


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
    if spec.profile != "service":
        raise ValueError("This renderer currently supports the service reference.")
    from .project_templates import COMMAND, HTTP_CHECKS, SERVICE_APP, SERVICE_PHASE
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

Application-owned `service` reference project for synthetic work items.
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
    checks = (HTTP_CHECKS + SERVICE_PHASE).replace("__PROJECT_MODULE__", spec.module).replace("__PROJECT_PROFILE__", spec.profile)
    return {"pyproject.toml": metadata, "README.md": readme,
            ".gitignore": ".venv/\n__pycache__/\n*.py[cod]\n*.sqlite3*\n.env\n",
            "reference-project.json": json.dumps(spec.selection(), indent=2, sort_keys=True) + "\n",
            f"src/{spec.module}/__init__.py": '"""Application-owned reference project."""\n',
            f"src/{spec.module}/app.py": SERVICE_APP,
            f"src/{spec.module}/__main__.py": COMMAND,
            f"src/{spec.module}/checks.py": checks}
