"""Explicit selections for application-owned reference projects."""

from dataclasses import dataclass
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
