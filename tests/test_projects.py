import asyncio
import importlib.util
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import tomllib
import unittest
from unittest.mock import patch

from compose_application.projects import PROFILES, ProjectSpec, REFERENCE_REVISION, create_project, render_project


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
    def test_live_factory_has_no_ambient_configuration_or_listener_command(self):
        spec = ProjectSpec("garden-live", "live")
        files = render_project(spec)
        for path, source in files.items():
            if path.endswith(".py"):
                compile(source, path, "exec")
        self.assertEqual(tomllib.loads(files["pyproject.toml"])["project"]["dependencies"], [spec.dependency])
        self.assertNotIn("serve", files["src/garden_live/__main__.py"])
        self.assertNotIn("getenv", files["src/garden_live/app.py"])
        self.assertIn("required keyword", files["README.md"])

    @unittest.skipUnless(importlib.util.find_spec("spatial_ui") and importlib.util.find_spec("expose_api"),
                         "optional live profile not installed")
    def test_generated_live_access_snapshots_reopen_and_cleanup(self):
        with TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            create_project(ProjectSpec("garden-live", "live"), root)
            sys.path.insert(0, str(root / "src"))
            try:
                from garden_live.checks import phase
                database = root / "check.sqlite3"
                self.assertEqual(asyncio.run(phase(database, "write"))["checks"], 10)
                self.assertEqual(asyncio.run(phase(database, "reload"))["checks"], 5)
            finally:
                sys.path.pop(0)
                for name in tuple(sys.modules):
                    if name == "garden_live" or name.startswith("garden_live."):
                        del sys.modules[name]

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

    def test_ui_selects_only_its_qualified_extra(self):
        spec = ProjectSpec("garden-ui", "ui")
        files = render_project(spec)
        self.assertEqual(tomllib.loads(files["pyproject.toml"])["project"]["dependencies"], [spec.dependency])
        for path, source in files.items():
            if path.endswith(".py"):
                compile(source, path, "exec")
        self.assertIn("Discard", files["README.md"])

    @unittest.skipUnless(importlib.util.find_spec("spatial_ui"), "optional UI profile not installed")
    def test_generated_ui_opens_real_page_and_preserves_form_drafts(self):
        with TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            spec = ProjectSpec("garden-ui", "ui")
            self.assertTrue(create_project(spec, root))
            sys.path.insert(0, str(root / "src"))
            try:
                from garden_ui.checks import phase
                database = root / "check.sqlite3"
                self.assertEqual(asyncio.run(phase(database, "write"))["checks"], 10)
                self.assertEqual(asyncio.run(phase(database, "reload"))["checks"], 5)
                self.assertFalse(create_project(spec, root))
            finally:
                sys.path.pop(0)
                for name in tuple(sys.modules):
                    if name == "garden_ui" or name.startswith("garden_ui."):
                        del sys.modules[name]

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


class CreationTests(unittest.TestCase):
    def test_repeat_preserves_owned_edits_data_and_removed_files(self):
        with TemporaryDirectory() as directory:
            root = Path(directory) / "garden"
            spec = ProjectSpec("garden-board", "service")
            self.assertTrue(create_project(spec, root))
            (root / "README.md").write_text("Owner's changes", encoding="utf-8")
            (root / "work-items.sqlite3").write_bytes(b"existing application data")
            (root / "src/garden_board/app.py").unlink()
            before = {path.relative_to(root): (path.read_bytes(), path.stat().st_mtime_ns)
                      for path in root.rglob("*") if path.is_file()}
            self.assertFalse(create_project(spec, root))
            after = {path.relative_to(root): (path.read_bytes(), path.stat().st_mtime_ns)
                     for path in root.rglob("*") if path.is_file()}
            self.assertEqual(after, before)
            with self.assertRaises(FileExistsError):
                create_project(ProjectSpec("other-board", "service"), root)

    def test_refuses_existing_directory_file_and_malformed_receipt(self):
        with TemporaryDirectory() as directory:
            root = Path(directory) / "garden"
            root.mkdir()
            spec = ProjectSpec("garden-board", "service")
            for content in (None, "{}", "not JSON"):
                if content is not None:
                    (root / "reference-project.json").write_text(content, encoding="utf-8")
                with self.assertRaises(FileExistsError):
                    create_project(spec, root)
            file = Path(directory) / "file"
            file.write_text("owner", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                create_project(spec, file)
            self.assertEqual(file.read_text(), "owner")

    def test_failed_creation_cleans_own_files_but_retains_owner_additions(self):
        with TemporaryDirectory() as directory:
            root = Path(directory) / "garden"
            original = os.link
            def fail(source, path):
                if path.name == "README.md":
                    (root / "owner.txt").write_text("keep", encoding="utf-8")
                    raise OSError("simulated write failure")
                return original(source, path)
            with patch("compose_application.projects.os.link", fail), self.assertRaises(OSError):
                create_project(ProjectSpec("garden-board", "service"), root)
            self.assertEqual([path.name for path in root.iterdir()], ["owner.txt"])
            self.assertEqual(sorted(path.name for path in Path(directory).iterdir()), ["garden"])

    def test_symlink_destinations_are_refused(self):
        with TemporaryDirectory() as directory:
            root, link = Path(directory) / "real", Path(directory) / "link"
            root.mkdir()
            try:
                link.symlink_to(root, target_is_directory=True)
            except OSError:
                self.skipTest("platform does not grant symlink creation")
            with self.assertRaises(FileExistsError):
                create_project(ProjectSpec("garden-board", "service"), link)
            self.assertEqual(list(root.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
