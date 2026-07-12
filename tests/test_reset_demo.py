from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import reset_demo  # noqa: E402


class ResetDemoSafetyTests(unittest.TestCase):
    def build_fixture(self, root: Path) -> tuple[Path, Path]:
        source = root / "references/demo-data/example-profile-baseline.yaml"
        target = root / "sellers/_example/profile.yaml"
        source.parent.mkdir(parents=True)
        (target.parent / "decisions").mkdir(parents=True)
        source.write_text(
            'meta:\n  seller_id: "_example"\nlearned: []\n', encoding="utf-8"
        )
        target.write_text(
            'meta:\n  seller_id: "_example"\nlearned: []\npreferences:\n  note: old\n',
            encoding="utf-8",
        )
        return source, target

    def test_reset_uses_safe_atomic_exact_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, target = self.build_fixture(root)
            reset_demo.reset_profile(root, source, target)
            self.assertEqual(
                source.read_text(encoding="utf-8"), target.read_text(encoding="utf-8")
            )

    def test_reset_rejects_symlinked_source_or_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, target = self.build_fixture(root)
            real_source = root / "real-source.yaml"
            real_source.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            source.unlink()
            try:
                source.symlink_to(real_source)
            except OSError as exc:  # pragma: no cover
                self.skipTest(f"symlink creation unavailable: {exc}")
            with self.assertRaisesRegex(SystemExit, "baseline must be a real"):
                reset_demo.reset_profile(root, source, target)

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, target = self.build_fixture(root)
            victim = root / "victim-profile.yaml"
            victim.write_text(target.read_text(encoding="utf-8"), encoding="utf-8")
            target.unlink()
            target.symlink_to(victim)
            with self.assertRaisesRegex(SystemExit, "profile must not be a symlink"):
                reset_demo.reset_profile(root, source, target)


if __name__ == "__main__":
    unittest.main()
