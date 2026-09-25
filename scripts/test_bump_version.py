"""Version bumps used by the release workflow."""

import tempfile
import unittest
from pathlib import Path

from bump_version import bump_file, next_version


class BumpVersionTest(unittest.TestCase):
    def test_minor_and_major_from_the_current_package(self):
        self.assertEqual(next_version("0.1.0", "minor"), "0.2.0")
        self.assertEqual(next_version("0.1.0", "major"), "1.0.0")
        self.assertEqual(next_version("1.4.2", "minor"), "1.5.0")
        self.assertEqual(next_version("1.4.2", "major"), "2.0.0")

    def test_rewrites_only_the_version_field(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pyproject.toml"
            path.write_text('name = "ai-momentum-analyzer"\nversion = "0.1.0"\n', encoding="utf-8")
            self.assertEqual(bump_file(path, "minor"), "0.2.0")
            self.assertEqual(path.read_text(encoding="utf-8"), 'name = "ai-momentum-analyzer"\nversion = "0.2.0"\n')


if __name__ == "__main__":
    unittest.main()
