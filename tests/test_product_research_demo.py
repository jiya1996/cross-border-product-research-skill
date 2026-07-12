from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("run_demo", ROOT / "scripts" / "run_demo.py")
assert SPEC and SPEC.loader
run_demo = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(run_demo)


def base_profile() -> dict:
    return {
        "constraints": {
            "target_marketplaces": ["tiktok-us"],
            "capital_per_sku_max": 30000,
            "forbidden_categories": ["儿童安全用品"],
            "forbidden_attributes": ["易碎", "强磁"],
        },
        "capabilities": {"content_skill": 5},
        "preferences": {
            "margin_floor_pct": 35,
            "competition_tolerance": "medium",
            "product_style": ["功能改良"],
            "scoring_weights": {
                "demand": 0.25,
                "competition": 0.20,
                "margin": 0.20,
                "capability_fit": 0.20,
                "risk": 0.15,
            },
        },
    }


def candidate(**overrides) -> dict:
    row = {
        "id": "t-1",
        "product": "Reusable lint remover",
        "category": "家居清洁",
        "target_price_usd": "18.99",
        "supply_price_cny": "8",
        "moq": "100",
        "weight_g": "72",
        "volume_cm": "13x8x3",
        "content_hook": "沙发除毛前后对比",
        "demand_signal": "宠物家庭痛点强",
        "competition_signal": "同款中等",
        "risk_flags": "刀片结构待核实",
    }
    row.update(overrides)
    return row


class ProductResearchDemoTests(unittest.TestCase):
    def test_seller_id_rejects_path_traversal(self) -> None:
        with self.assertRaises(SystemExit):
            run_demo.validate_seller_id("../other-seller")

    def test_missing_signals_do_not_get_default_scores(self) -> None:
        self.assertIsNone(run_demo.demand_score(""))
        self.assertIsNone(run_demo.competition_score(""))
        self.assertIsNone(run_demo.risk_score({"risk_flags": ""}, False))

    def test_forbidden_category_and_attribute_are_filtered(self) -> None:
        profile = base_profile()
        rows = [
            candidate(id="child", category="儿童安全用品"),
            candidate(id="glass", risk_flags="易碎，包装风险"),
        ]
        scored, filtered, pending, _ = run_demo.score_candidates(
            profile, "易碎和儿童安全用品不做", rows, []
        )
        self.assertEqual([], scored)
        self.assertEqual([], pending)
        self.assertEqual({"child", "glass"}, {row["id"] for row in filtered})

    def test_known_capital_over_limit_is_filtered(self) -> None:
        profile = base_profile()
        row = candidate(id="capital", supply_price_cny="600", moq="60", weight_g="12000", volume_cm="90x70x55")
        scored, filtered, _, _ = run_demo.score_candidates(profile, "", [row], [])
        self.assertEqual([], scored)
        self.assertEqual("capital", filtered[0]["id"])
        self.assertIn("capital_per_sku_max", filtered[0]["filter_reason"])

    def test_missing_fact_moves_candidate_to_pending(self) -> None:
        profile = base_profile()
        row = candidate(id="missing", supply_price_cny="", weight_g="", volume_cm="")
        scored, filtered, pending, _ = run_demo.score_candidates(profile, "", [row], [])
        self.assertEqual([], scored)
        self.assertEqual([], filtered)
        self.assertEqual("missing", pending[0]["id"])
        self.assertIn("margin", pending[0]["missing_dimensions"])

    def test_unconfirmed_rule_does_not_change_score_confirmed_rule_does(self) -> None:
        profile = base_profile()
        row = candidate(id="red-ocean", competition_signal="同款过多", risk_flags="差异化弱")
        baseline, _, _, _ = run_demo.score_candidates(profile, "", [row], [])
        confirmed, _, _, _ = run_demo.score_candidates(
            profile,
            "",
            [row],
            ["用户连续拒绝同款过多且差异化不足，后续降低同款权重。"],
        )
        self.assertGreater(baseline[0]["total"], confirmed[0]["total"])
        self.assertEqual("-", baseline[0]["applied_profile_rules"])
        self.assertIn("competition", confirmed[0]["applied_profile_rules"])

    def test_missing_sop_stops_before_research(self) -> None:
        original_root = run_demo.ROOT
        try:
            with tempfile.TemporaryDirectory() as temp:
                run_demo.ROOT = Path(temp)
                seller = run_demo.ROOT / "sellers" / "demo"
                seller.mkdir(parents=True)
                (seller / "profile.yaml").write_text("meta:\n  seller_id: demo\n", encoding="utf-8")
                with self.assertRaises(SystemExit) as error:
                    run_demo.read_required_context("demo")
                self.assertIn("intake-interview", str(error.exception))
        finally:
            run_demo.ROOT = original_root

    def test_report_contains_per_candidate_contract(self) -> None:
        original_root = run_demo.ROOT
        try:
            with tempfile.TemporaryDirectory() as temp:
                run_demo.ROOT = Path(temp)
                profile = base_profile()
                scored, filtered, pending, weights = run_demo.score_candidates(
                    profile, "", [candidate()], []
                )
                context = {
                    "profile": profile,
                    "profile_text": "learned: []\n",
                    "recent_decisions": [],
                }
                report = run_demo.write_report(
                    "demo", 1, "test", context, scored, filtered, pending, weights
                )
                text = report.read_text(encoding="utf-8")
                for needle in [
                    "为什么适合你",
                    "为什么不适合你",
                    "主要风险",
                    "被过滤品及原因",
                    "需人工核实",
                    "profile.capabilities.content_skill",
                ]:
                    self.assertIn(needle, text)
        finally:
            run_demo.ROOT = original_root


if __name__ == "__main__":
    unittest.main()
