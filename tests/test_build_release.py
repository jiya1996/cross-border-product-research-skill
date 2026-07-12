from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import build_release


class BuildReleaseSafetyTests(unittest.TestCase):
    def init_repo(self, root: Path) -> None:
        subprocess.run(["git", "init", "-q", str(root)], check=True)

    def test_release_files_ignores_untracked_allowlisted_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.init_repo(root)
            (root / "references").mkdir()
            (root / "README.md").write_text("public\n", encoding="utf-8")
            tracked = root / "references" / "tracked.md"
            tracked.write_text("tracked\n", encoding="utf-8")
            (root / "references" / "private.csv").write_text(
                "seller,revenue\nsecret,1\n", encoding="utf-8"
            )
            subprocess.run(
                ["git", "-C", str(root), "add", "README.md", "references/tracked.md"],
                check=True,
            )

            with mock.patch.object(build_release, "ROOT", root):
                names = {
                    path.relative_to(root).as_posix()
                    for path in build_release.release_files()
                }

            self.assertEqual({"README.md", "references/tracked.md"}, names)

    def test_release_files_rejects_tracked_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory() as outside:
            root = Path(temp)
            self.init_repo(root)
            (root / "references").mkdir()
            secret = Path(outside) / "secret.txt"
            secret.write_text("outside\n", encoding="utf-8")
            link = root / "references" / "leak.txt"
            try:
                os.symlink(secret, link)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink unavailable: {exc}")
            subprocess.run(
                ["git", "-C", str(root), "add", "references/leak.txt"], check=True
            )

            with mock.patch.object(build_release, "ROOT", root):
                with self.assertRaisesRegex(SystemExit, "Symlink forbidden"):
                    build_release.release_files()


if __name__ == "__main__":
    unittest.main()
