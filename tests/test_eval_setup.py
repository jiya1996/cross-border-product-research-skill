from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import learned_rules  # noqa: E402
import run_product_research_evals as eval_runner  # noqa: E402


class EvalSellerSetupTests(unittest.TestCase):
    def case(self, status: str) -> dict:
        return {
            "id": "L02" if status == "active" else "L01",
            "setup": {
                "sellers": [
                    {
                        "seller_id": "eval-content",
                        "fixture": "evals/product-research/fixtures/sellers/eval-content",
                        "include": ["profile.yaml", "sop.md", "decisions"],
                        "rule_id": learned_rules.DEMO_RULE_ID,
                        "status": status,
                    }
                ],
                "source_reports": [
                    {
                        "seller_id": "eval-content",
                        "fixture": "evals/product-research/fixtures/reports/eval-content",
                    }
                ],
            },
        }

    def test_setup_updates_exact_rule_structurally(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workdir = Path(temp)
            (workdir / "sellers").mkdir()
            (workdir / "reports").mkdir()
            eval_runner.setup_sellers(workdir, self.case("active"))
            profile = workdir / "sellers/eval-content/profile.yaml"
            active = learned_rules.find_rule(
                learned_rules.load_rules(profile), learned_rules.DEMO_RULE_ID
            )
            self.assertEqual("active", active["status"])
            self.assertEqual("eval-fixture", active["confirmed_by"])

            # A second isolated setup must restore proposed without replacing
            # arbitrary strings elsewhere in the profile.
            eval_runner.setup_sellers(workdir, self.case("proposed"))
            proposed = learned_rules.find_rule(
                learned_rules.load_rules(profile), learned_rules.DEMO_RULE_ID
            )
            self.assertEqual("proposed", proposed["status"])
            self.assertIsNone(proposed["confirmed_by"])
            self.assertIsNone(proposed["confirmed_at"])
            self.assertFalse((workdir / "reports/eval-content").exists())

    def test_proposed_setup_does_not_require_or_copy_source_reports(self) -> None:
        case = self.case("proposed")
        case["setup"]["source_reports"][0]["fixture"] = (
            "evals/product-research/fixtures/reports/does-not-exist"
        )
        with tempfile.TemporaryDirectory() as temp:
            workdir = Path(temp)
            (workdir / "sellers").mkdir()
            (workdir / "reports").mkdir()
            eval_runner.setup_sellers(workdir, case)
            self.assertFalse((workdir / "reports/eval-content").exists())

    def test_setup_fails_when_rule_id_is_unknown(self) -> None:
        case = self.case("active")
        case["setup"]["sellers"][0]["rule_id"] = "missing_rule_id"
        with tempfile.TemporaryDirectory() as temp:
            workdir = Path(temp)
            (workdir / "sellers").mkdir()
            (workdir / "reports").mkdir()
            with self.assertRaisesRegex(SystemExit, "no learned rule_id"):
                eval_runner.setup_sellers(workdir, case)

    def test_setup_rejects_legacy_confirmed_and_invalid_status(self) -> None:
        legacy = self.case("active")
        legacy_spec = legacy["setup"]["sellers"][0]
        legacy_spec["confirmed"] = True
        with tempfile.TemporaryDirectory() as temp:
            workdir = Path(temp)
            (workdir / "sellers").mkdir()
            (workdir / "reports").mkdir()
            with self.assertRaisesRegex(SystemExit, "legacy confirmed"):
                eval_runner.setup_sellers(workdir, legacy)

        invalid = self.case("active")
        invalid["setup"]["sellers"][0]["status"] = "revoked"
        with tempfile.TemporaryDirectory() as temp:
            workdir = Path(temp)
            (workdir / "sellers").mkdir()
            (workdir / "reports").mkdir()
            with self.assertRaisesRegex(SystemExit, "proposed or active"):
                eval_runner.setup_sellers(workdir, invalid)

    def test_setup_requires_rule_id_and_status_as_a_pair(self) -> None:
        case = self.case("active")
        del case["setup"]["sellers"][0]["rule_id"]
        with tempfile.TemporaryDirectory() as temp:
            workdir = Path(temp)
            (workdir / "sellers").mkdir()
            (workdir / "reports").mkdir()
            with self.assertRaisesRegex(SystemExit, "requires both rule_id and status"):
                eval_runner.setup_sellers(workdir, case)

    def test_setup_copies_evidence_reports_inside_seller_namespace(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workdir = Path(temp)
            (workdir / "sellers").mkdir()
            (workdir / "reports").mkdir()
            eval_runner.setup_sellers(workdir, self.case("active"))
            profile = workdir / "sellers/eval-content/profile.yaml"
            rule = learned_rules.find_rule(
                learned_rules.load_rules(profile), learned_rules.DEMO_RULE_ID
            )
            for evidence in rule["evidence"]:
                report_id = evidence["source_report_id"]
                self.assertTrue(report_id.startswith("reports/eval-content/"))
                self.assertTrue((workdir / report_id).is_file())
            decision_text = "\n".join(
                path.read_text(encoding="utf-8")
                for path in (workdir / "sellers/eval-content/decisions").glob("*.md")
            )
            self.assertNotIn("reports/_example/", decision_text)


if __name__ == "__main__":
    unittest.main()
