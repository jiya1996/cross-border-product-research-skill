from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_video_demo  # noqa: E402


class VideoDemoSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_root = run_video_demo.ROOT
        self.temp_dir = tempfile.TemporaryDirectory()
        run_video_demo.ROOT = Path(self.temp_dir.name)
        self.root = run_video_demo.ROOT
        (self.root / "references/demo-data").mkdir(parents=True)
        (self.root / "sellers/_example/decisions").mkdir(parents=True)
        (self.root / "reports/_example").mkdir(parents=True)
        (self.root / "references/demo-data/example-profile-baseline.yaml").write_text(
            'meta:\n  seller_id: "_example"\nlearned: []\n', encoding="utf-8"
        )
        (self.root / "sellers/_example/sop.md").write_text(
            "# SOP — _example\n", encoding="utf-8"
        )
        for index, name in enumerate(run_video_demo.SOURCE_REPORT_NAMES, start=1):
            (self.root / "reports/_example" / name).write_text(
                "# synthetic\n\n"
                "- seller_id: `_example`\n"
                f"- source_report_id: `reports/_example/{name}`\n"
                "- 市场: US\n\n"
                "| candidate_id | product |\n|---|---|\n"
                f"| c{index} | product |\n",
                encoding="utf-8",
            )
        for index, decision_name in enumerate(
            run_video_demo.SOURCE_DECISION_NAMES, start=1
        ):
            report_name = run_video_demo.SOURCE_REPORT_NAMES[
                (index - 1) % len(run_video_demo.SOURCE_REPORT_NAMES)
            ]
            (self.root / "sellers/_example/decisions" / decision_name).write_text(
                f"# 2026-07-0{index} | c{index}\n\n"
                f"- 决策ID: decision-{index}\n"
                f"- 候选ID: c{index}\n"
                f"- 来源报告: reports/_example/{report_name}\n"
                "- 平台/来源: TikTok\n"
                "- 市场: US\n"
                "- 用户决定: rejected\n"
                "- 归类标签ID: [same_product_density_high, differentiation_space_low]\n",
                encoding="utf-8",
            )

    def replace_with_symlink(self, path: Path) -> None:
        outside = self.root / f"outside-{path.name}"
        outside.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        path.unlink()
        try:
            path.symlink_to(outside)
        except OSError as exc:  # pragma: no cover
            self.skipTest(f"symlink creation unavailable: {exc}")

    def tearDown(self) -> None:
        run_video_demo.ROOT = self.original_root
        self.temp_dir.cleanup()

    def test_prepare_uses_unique_new_paths_and_rewrites_tenant_sources(self) -> None:
        with mock.patch.object(
            run_video_demo.uuid,
            "uuid4",
            return_value=SimpleNamespace(hex="a" * 32),
        ):
            seller_id = run_video_demo.prepare_seller()
        self.assertEqual(f"video-demo-{'a' * 32}", seller_id)
        seller = self.root / "sellers" / seller_id
        reports = self.root / "reports" / seller_id
        self.assertTrue(seller.is_dir())
        self.assertTrue(reports.is_dir())
        for decision in (seller / "decisions").glob("*.md"):
            text = decision.read_text(encoding="utf-8")
            self.assertIn(f"来源报告: reports/{seller_id}/", text)
            self.assertNotIn("reports/_example/", text)
        for name in run_video_demo.SOURCE_REPORT_NAMES:
            text = (reports / name).read_text(encoding="utf-8")
            self.assertIn(f"seller_id: `{seller_id}`", text)
            self.assertIn(f"reports/{seller_id}/{name}", text)

    def test_prepare_never_reuses_or_deletes_an_existing_path(self) -> None:
        seller_id = f"video-demo-{'b' * 32}"
        existing = self.root / "sellers" / seller_id
        existing.mkdir()
        protected = existing / "profile.yaml"
        protected.write_text("preserve me\n", encoding="utf-8")
        with mock.patch.object(
            run_video_demo.uuid,
            "uuid4",
            return_value=SimpleNamespace(hex="b" * 32),
        ):
            with self.assertRaisesRegex(SystemExit, "Refusing to reuse"):
                run_video_demo.prepare_seller()
        self.assertEqual("preserve me\n", protected.read_text(encoding="utf-8"))

    def test_prepare_rejects_symlinked_parent(self) -> None:
        real_sellers = self.root / "real-sellers"
        real_sellers.mkdir()
        (self.root / "sellers").rename(self.root / "original-sellers")
        try:
            (self.root / "sellers").symlink_to(real_sellers, target_is_directory=True)
        except OSError as exc:  # pragma: no cover
            self.skipTest(f"symlink creation unavailable: {exc}")
        with self.assertRaisesRegex(SystemExit, "parent must not be a symlink"):
            run_video_demo.prepare_seller()

    def test_prepare_rejects_symlinked_profile_source(self) -> None:
        path = self.root / run_video_demo.SOURCE_PROFILE_REL
        self.replace_with_symlink(path)
        with self.assertRaisesRegex(SystemExit, "regular non-symlink"):
            run_video_demo.prepare_seller()

    def test_prepare_rejects_symlinked_sop_source(self) -> None:
        path = self.root / run_video_demo.SOURCE_SOP_REL
        self.replace_with_symlink(path)
        with self.assertRaisesRegex(SystemExit, "regular non-symlink"):
            run_video_demo.prepare_seller()

    def test_prepare_rejects_symlinked_decision_source(self) -> None:
        path = (
            self.root
            / run_video_demo.SOURCE_DECISIONS_REL
            / run_video_demo.SOURCE_DECISION_NAMES[0]
        )
        self.replace_with_symlink(path)
        with self.assertRaisesRegex(SystemExit, "regular non-symlink"):
            run_video_demo.prepare_seller()

    def test_prepare_rejects_symlinked_report_source(self) -> None:
        path = (
            self.root
            / run_video_demo.SOURCE_REPORTS_REL
            / run_video_demo.SOURCE_REPORT_NAMES[0]
        )
        self.replace_with_symlink(path)
        with self.assertRaisesRegex(SystemExit, "regular non-symlink"):
            run_video_demo.prepare_seller()


if __name__ == "__main__":
    unittest.main()
