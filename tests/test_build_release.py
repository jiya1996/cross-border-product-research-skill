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

    def write_manifest(self, root: Path, *entries: str) -> None:
        manifest = root / "config" / "public-release-files.txt"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(
            "\n".join(["config/public-release-files.txt", *entries]) + "\n",
            encoding="utf-8",
        )

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
            self.write_manifest(root, "README.md", "references/tracked.md")
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(root),
                    "add",
                    "README.md",
                    "references/tracked.md",
                    "config/public-release-files.txt",
                ],
                check=True,
            )

            with mock.patch.object(build_release, "ROOT", root):
                names = {
                    path.relative_to(root).as_posix()
                    for path in build_release.release_files()
                }

            self.assertEqual(
                {
                    "README.md",
                    "references/tracked.md",
                    "config/public-release-files.txt",
                },
                names,
            )

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
            self.write_manifest(root, "references/leak.txt")
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(root),
                    "add",
                    "references/leak.txt",
                    "config/public-release-files.txt",
                ],
                check=True,
            )

            with mock.patch.object(build_release, "ROOT", root):
                with self.assertRaisesRegex(SystemExit, "Symlink forbidden"):
                    build_release.release_files()

    def test_release_files_excludes_tracked_unlisted_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.init_repo(root)
            (root / "references").mkdir()
            (root / "references" / "private-seller.csv").write_text(
                "seller,revenue\nprivate,1\n", encoding="utf-8"
            )
            self.write_manifest(root)
            subprocess.run(
                ["git", "-C", str(root), "add", "."], check=True
            )
            with mock.patch.object(build_release, "ROOT", root):
                names = {
                    path.relative_to(root).as_posix()
                    for path in build_release.release_files()
                }
            self.assertEqual({"config/public-release-files.txt"}, names)

    def test_release_files_globally_rejects_raw_artifact_paths(self) -> None:
        for relative in (
            "events.jsonl",
            "logs/stderr.log",
            "workspace/file.txt",
            "raw/file.txt",
            "raw-run/file.txt",
            "evals/product-research/artifacts/run/summary.json",
        ):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                self.init_repo(root)
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("raw\n", encoding="utf-8")
                self.write_manifest(root)
                subprocess.run(["git", "-C", str(root), "add", "."], check=True)
                with mock.patch.object(build_release, "ROOT", root):
                    with self.assertRaisesRegex(SystemExit, "Forbidden tracked path"):
                        build_release.release_files()

    def test_release_rejects_worktree_content_that_differs_from_index(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.init_repo(root)
            readme = root / "README.md"
            readme.write_text("public\n", encoding="utf-8")
            self.write_manifest(root, "README.md")
            subprocess.run(["git", "-C", str(root), "add", "."], check=True)
            readme.write_text("unstaged private content\n", encoding="utf-8")
            with mock.patch.object(build_release, "ROOT", root):
                with self.assertRaisesRegex(SystemExit, "differs from the Git index"):
                    build_release.release_files()

    def test_build_rejects_output_aliasing_an_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "README.md"
            source.write_text("public\n", encoding="utf-8")
            with (
                mock.patch.object(build_release, "ROOT", root),
                mock.patch.object(
                    build_release,
                    "release_payloads",
                    return_value=[(source, b"public\n")],
                ),
            ):
                with self.assertRaisesRegex(SystemExit, "aliases an input"):
                    build_release.build_release(source)

    def test_failed_zip_verification_preserves_existing_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "README.md"
            source.write_text("public\n", encoding="utf-8")
            output = root / "release.zip"
            output.write_bytes(b"old-package")
            with (
                mock.patch.object(build_release, "ROOT", root),
                mock.patch.object(
                    build_release,
                    "release_payloads",
                    return_value=[(source, b"public\n")],
                ),
                mock.patch.object(
                    build_release,
                    "_verify_zip",
                    side_effect=SystemExit("synthetic verification failure"),
                ),
            ):
                with self.assertRaisesRegex(SystemExit, "synthetic verification failure"):
                    build_release.build_release(output)
            self.assertEqual(b"old-package", output.read_bytes())
            self.assertEqual([], list(root.glob(".release.zip.*.tmp")))

    def test_build_zip_uses_index_blob_not_changed_worktree_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.init_repo(root)
            readme = root / "README.md"
            readme.write_text("staged-public\n", encoding="utf-8")
            self.write_manifest(root, "README.md")
            subprocess.run(["git", "-C", str(root), "add", "."], check=True)
            readme.write_text("unstaged-private\n", encoding="utf-8")
            output = root / "release.zip"
            with mock.patch.object(build_release, "ROOT", root):
                build_release.build_release(output)
            import zipfile

            with zipfile.ZipFile(output) as archive:
                self.assertEqual(b"staged-public\n", archive.read("README.md"))


if __name__ == "__main__":
    unittest.main()
