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
    def case(self, confirmed: bool) -> dict:
        return {
            "id": "L02" if confirmed else "L01",
            "setup": {
                "sellers": [
                    {
                        "seller_id": "eval-content",
                        "fixture": "evals/product-research/fixtures/sellers/eval-content",
                        "include": ["profile.yaml", "sop.md", "decisions"],
                        "confirmed": confirmed,
                        "rule_id": learned_rules.DEMO_RULE_ID,
                    }
                ]
            },
        }

    def test_setup_updates_exact_rule_structurally(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workdir = Path(temp)
            (workdir / "sellers").mkdir()
            eval_runner.setup_sellers(workdir, self.case(True))
            profile = workdir / "sellers/eval-content/profile.yaml"
            active = learned_rules.find_rule(
                learned_rules.load_rules(profile), learned_rules.DEMO_RULE_ID
            )
            self.assertEqual("active", active["status"])
            self.assertEqual("eval-fixture", active["confirmed_by"])

            # A second isolated setup must restore proposed without replacing
            # arbitrary strings elsewhere in the profile.
            eval_runner.setup_sellers(workdir, self.case(False))
            proposed = learned_rules.find_rule(
                learned_rules.load_rules(profile), learned_rules.DEMO_RULE_ID
            )
            self.assertEqual("proposed", proposed["status"])
            self.assertIsNone(proposed["confirmed_by"])
            self.assertIsNone(proposed["confirmed_at"])

    def test_setup_fails_when_rule_id_is_unknown(self) -> None:
        case = self.case(True)
        case["setup"]["sellers"][0]["rule_id"] = "missing_rule_id"
        with tempfile.TemporaryDirectory() as temp:
            workdir = Path(temp)
            (workdir / "sellers").mkdir()
            with self.assertRaisesRegex(SystemExit, "no learned rule_id"):
                eval_runner.setup_sellers(workdir, case)


if __name__ == "__main__":
    unittest.main()
