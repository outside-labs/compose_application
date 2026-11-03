import asyncio
import importlib.util
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import tomllib
import unittest

from compose_application.projects import PROFILES, ProjectSpec, REFERENCE_REVISION, render_project


class SelectionTests(unittest.TestCase):
    def test_explicit_profiles_and_immutable_dependencies(self):
        for profile in PROFILES:
            spec = ProjectSpec("garden-board", profile)
            self.assertEqual(spec.module, "garden_board")
            self.assertIn(f"[{profile}]", spec.dependency)
            self.assertTrue(spec.dependency.endswith("@" + REFERENCE_REVISION))
            selection = spec.selection()
            selection["name"] = "changed"
            self.assertEqual(spec.selection()["name"], "garden-board")

    def test_refuse_unsafe_names(self):
        for name in ("", "Garden", "../garden", "garden/board", "garden_board", "garden--board",
                     "a" * 49, "class", "json", "con", "com1", "compose-application", "spatial-ui", 1):
            with self.subTest(name=name), self.assertRaises(ValueError):
                ProjectSpec(name, "service")

    def test_refuse_unknown_profile_or_source(self):
        for profile in (None, "", "all", "track-b", []):
            with self.subTest(profile=profile), self.assertRaises(ValueError):
                ProjectSpec("garden", profile)
        for source in (None, "main", "a" * 40):
            with self.subTest(source=source), self.assertRaises(ValueError):
                ProjectSpec("garden", "service", source)


class RenderTests(unittest.TestCase):
    def test_service_is_installable_selected_source(self):
        spec = ProjectSpec("garden-board", "service")
        files = render_project(spec)
        project = tomllib.loads(files["pyproject.toml"])["project"]
        self.assertEqual(project["dependencies"], [spec.dependency])
        self.assertEqual(project["scripts"], {"garden-board": "garden_board.__main__:main"})
        self.assertIn("--database", files["README.md"])
        for path, source in files.items():
            self.assertFalse(Path(path).is_absolute())
            if path.endswith(".py"):
                compile(source, path, "exec")
        files.clear()
        self.assertTrue(render_project(spec))

    @unittest.skipUnless(importlib.util.find_spec("expose_api"), "optional service profile not installed")
    def test_generated_service_assembly_over_real_http_and_reopen(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for path, source in render_project(ProjectSpec("garden-board", "service")).items():
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(source, encoding="utf-8")
            sys.path.insert(0, str(root / "src"))
            try:
                from garden_board.checks import phase
                database = root / "check.sqlite3"
                self.assertEqual(asyncio.run(phase(database, "write"))["checks"], 5)
                self.assertEqual(asyncio.run(phase(database, "reload"))["checks"], 4)
            finally:
                sys.path.pop(0)
                for name in tuple(sys.modules):
                    if name == "garden_board" or name.startswith("garden_board."):
                        del sys.modules[name]


if __name__ == "__main__":
    unittest.main()
