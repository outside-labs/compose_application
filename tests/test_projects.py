import unittest

from compose_application.projects import PROFILES, ProjectSpec, REFERENCE_REVISION


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


if __name__ == "__main__":
    unittest.main()
