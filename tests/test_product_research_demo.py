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
        "risk_flags": "刀片结构已核实为低风险",
        "rule_tag_ids": [],
    }
    row.update(overrides)
    return row


def learned_evidence() -> list[dict]:
    return [
        {
            "decision_path": f"decisions/{name}.md",
            "decision_id": f"decision-{name}",
            "session_id": f"session:{session}",
            "source_report_id": f"reports/demo/{session}.md",
            "candidate_id": f"candidate-{name}",
            "decided_at": date,
        }
        for name, session, date in [
            ("a", "one", "2026-07-10"),
            ("b", "one", "2026-07-10"),
            ("c", "two", "2026-07-11"),
        ]
    ]


def structured_rule(
    *, status: str = "proposed", expires_at: str | None = None
) -> dict:
    confirmed = status != "proposed"
    return {
        "rule_id": "learned_tiktok_same_density_diff_001",
        "version": 1,
        "summary": "自由文本只用于展示，不能驱动动作。",
        "status": status,
        "scope": {"platforms": ["tiktok"], "markets": ["US"], "categories": []},
        "condition_tag_ids": [
            "same_product_density_high",
            "differentiation_space_low",
        ],
        "action": {"dimension": "competition", "delta": -1},
        "evidence": learned_evidence(),
        "created": "2026-07-12",
        "confirmed_by": "seller-owner" if confirmed else None,
        "confirmed_at": "2026-07-12T00:00:00+00:00" if confirmed else None,
        "revoked_by": None,
        "revoked_at": None,
        "revoke_reason": None,
        "expires_at": expires_at,
        "supersedes": None,
    }


class ProductResearchDemoTests(unittest.TestCase):
    def test_seller_id_rejects_path_traversal(self) -> None:
        with self.assertRaises(SystemExit):
            run_demo.validate_seller_id("../other-seller")

    def test_report_output_dir_rejects_repository_escape(self) -> None:
        with self.assertRaises(SystemExit):
            run_demo.report_output_dir("demo", Path("../../outside"))

    def test_report_output_dir_rejects_cross_seller_and_symlink_alias(self) -> None:
        original_root = run_demo.ROOT
        try:
            with tempfile.TemporaryDirectory() as temp:
                run_demo.ROOT = Path(temp)
                (run_demo.ROOT / "reports/other").mkdir(parents=True)
                with self.assertRaisesRegex(SystemExit, "must be reports/demo"):
                    run_demo.report_output_dir("demo", Path("reports/other"))
                alias = run_demo.ROOT / "reports/demo"
                try:
                    alias.symlink_to(
                        run_demo.ROOT / "reports/other", target_is_directory=True
                    )
                except OSError as exc:  # pragma: no cover
                    self.skipTest(f"symlink creation unavailable: {exc}")
                with self.assertRaisesRegex(SystemExit, "must not contain symlinks"):
                    run_demo.report_output_dir("demo", Path("reports/demo"))
        finally:
            run_demo.ROOT = original_root

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

    def test_unknown_compliance_risk_moves_candidate_to_pending(self) -> None:
        row = candidate(id="unknown-risk", risk_flags="认证待核实")
        scored, filtered, pending, _ = run_demo.score_candidates(
            base_profile(), "", [row], []
        )
        self.assertEqual([], scored)
        self.assertEqual([], filtered)
        self.assertEqual("unknown-risk", pending[0]["id"])
        self.assertIn("risk", pending[0]["missing_dimensions"])

    def test_non_finite_and_non_positive_candidate_numbers_are_blocked(self) -> None:
        for field, value in [
            ("target_price_usd", "NaN"),
            ("supply_price_cny", "Inf"),
            ("weight_g", "-1"),
            ("moq", "0"),
        ]:
            with self.subTest(field=field, value=value):
                row = candidate(id=f"bad-{field}", **{field: value})
                scored, filtered, pending, _ = run_demo.score_candidates(
                    base_profile(), "", [row], []
                )
                self.assertEqual([], scored)
                self.assertEqual([], filtered)
                self.assertEqual(row["id"], pending[0]["id"])
                self.assertIn(f"data.{field}", pending[0]["missing_dimensions"])
        row = candidate(id="bad-volume", volume_cm="-1x8x3")
        scored, filtered, pending, _ = run_demo.score_candidates(
            base_profile(), "", [row], []
        )
        self.assertEqual([], scored)
        self.assertEqual([], filtered)
        self.assertIn("data.volume_cm", pending[0]["missing_dimensions"])

    def test_profile_numbers_reject_nan_inf_and_negative_weights(self) -> None:
        for raw in ("NaN", "Inf", "-Inf"):
            with self.subTest(raw=raw), self.assertRaisesRegex(SystemExit, "finite"):
                run_demo.parse_scalar(raw)
        profile = base_profile()
        profile["preferences"]["scoring_weights"] = {
            "demand": -0.1,
            "competition": 0.2,
            "margin": 0.2,
            "capability_fit": 0.2,
            "risk": 0.5,
        }
        with self.assertRaisesRegex(SystemExit, "finite values from 0 to 1"):
            run_demo.score_candidates(profile, "", [candidate()], [])

    def test_proposed_rule_does_not_change_score_active_rule_does(self) -> None:
        profile = base_profile()
        row = candidate(
            id="red-ocean",
            competition_signal="同款过多",
            risk_flags="差异化弱",
            rule_tag_ids=["same_product_density_high", "differentiation_space_low"],
        )
        rule = structured_rule()
        proposed, _, _, _ = run_demo.score_candidates(profile, "", [row], [rule])
        active_rule = structured_rule(status="active")
        active, _, _, _ = run_demo.score_candidates(profile, "", [row], [active_rule])
        self.assertGreater(proposed[0]["total"], active[0]["total"])
        self.assertEqual("-", proposed[0]["applied_profile_rules"])
        self.assertIn("learned_tiktok_same_density_diff_001", active[0]["applied_profile_rules"])

    def test_rule_requires_all_tag_ids_and_does_not_infer_from_prose(self) -> None:
        profile = base_profile()
        shoe = candidate(
            id="shoe",
            product="Shoe crease protector",
            competition_signal="同款中高",
            risk_flags="尺码适配/退货",
            rule_tag_ids=["same_product_density_high"],
        )
        rule = structured_rule(status="active")
        rule["summary"] = "即使摘要写了同款和差异化，也不能越过结构化条件。"
        scored, _, _, _ = run_demo.score_candidates(profile, "", [shoe], [rule])
        self.assertEqual("-", scored[0]["applied_profile_rules"])
        self.assertEqual([], scored[0]["rule_effects"])

    def test_scoring_and_report_share_the_same_expiry_clock(self) -> None:
        original_root = run_demo.ROOT
        try:
            with tempfile.TemporaryDirectory() as temp:
                run_demo.ROOT = Path(temp)
                profile = base_profile()
                row = candidate(
                    id="clocked",
                    rule_tag_ids=[
                        "same_product_density_high",
                        "differentiation_space_low",
                    ],
                )
                rule = structured_rule(
                    status="active", expires_at="2026-07-12T12:00:00+00:00"
                )
                before_at = "2026-07-12T11:00:00+00:00"
                before, filtered, pending, weights = run_demo.score_candidates(
                    profile, "", [row], [rule], run_at=before_at
                )
                self.assertTrue(before[0]["rule_effects"])
                context = {
                    "profile": profile,
                    "profile_text": run_demo.learned_rules.dump_rules([rule]),
                    "learned_rules": [rule],
                    "recent_decisions": [],
                }
                before_report = run_demo.write_report(
                    "demo",
                    1,
                    "clock-before",
                    context,
                    before,
                    filtered,
                    pending,
                    weights,
                    run_at=before_at,
                ).read_text(encoding="utf-8")
                self.assertIn("active learned 规则数: 1", before_report)

                after_at = "2026-07-12T13:00:00+00:00"
                after, filtered, pending, weights = run_demo.score_candidates(
                    profile, "", [row], [rule], run_at=after_at
                )
                self.assertEqual([], after[0]["rule_effects"])
                after_report = run_demo.write_report(
                    "demo",
                    1,
                    "clock-after",
                    context,
                    after,
                    filtered,
                    pending,
                    weights,
                    run_at=after_at,
                ).read_text(encoding="utf-8")
                self.assertIn("active learned 规则数: 0", after_report)
                self.assertIn(
                    "| learned_tiktok_same_density_diff_001 | expired |",
                    after_report,
                )
        finally:
            run_demo.ROOT = original_root

    def test_report_names_the_rule_that_superseded_an_inactive_rule(self) -> None:
        original_root = run_demo.ROOT
        try:
            with tempfile.TemporaryDirectory() as temp:
                run_demo.ROOT = Path(temp)
                old_rule = structured_rule(status="active")
                old_rule["rule_id"] = "learned_tiktok_old_001"
                old_rule["status"] = "superseded"
                replacement = structured_rule(status="active")
                replacement["rule_id"] = "learned_tiktok_replacement_002"
                replacement["version"] = 2
                replacement["supersedes"] = old_rule["rule_id"]
                replacement["confirmed_at"] = "2026-07-13T08:30:00+00:00"
                rules = [old_rule, replacement]
                profile = base_profile()
                scored, filtered, pending, weights = run_demo.score_candidates(
                    profile, "", [candidate()], []
                )
                context = {
                    "profile": profile,
                    "profile_text": run_demo.learned_rules.dump_rules(rules),
                    "learned_rules": rules,
                    "recent_decisions": [],
                }
                report = run_demo.write_report(
                    "demo", 1, "superseded", context, scored, filtered, pending, weights
                ).read_text(encoding="utf-8")
                self.assertIn(
                    "superseded_by=learned_tiktok_replacement_002", report
                )
                self.assertRegex(
                    report,
                    r"\| learned_tiktok_old_001 \| superseded \| [^|]+ "
                    r"\| 2026-07-13T08:30:00\+00:00 \|",
                )
        finally:
            run_demo.ROOT = original_root

    def test_report_exposes_aggregate_rule_delta_and_all_rule_ids(self) -> None:
        original_root = run_demo.ROOT
        try:
            with tempfile.TemporaryDirectory() as temp:
                run_demo.ROOT = Path(temp)
                bonus = structured_rule(status="active")
                bonus["rule_id"] = "learned_bonus_001"
                bonus["action"]["delta"] = 5
                penalty = structured_rule(status="active")
                penalty["rule_id"] = "learned_penalty_001"
                penalty["action"]["delta"] = -5
                row = candidate(
                    id="aggregate",
                    rule_tag_ids=[
                        "same_product_density_high",
                        "differentiation_space_low",
                    ],
                )
                scored, filtered, pending, weights = run_demo.score_candidates(
                    base_profile(), "", [row], [penalty, bonus]
                )
                self.assertEqual(3, scored[0]["competition"])
                context = {
                    "profile": base_profile(),
                    "profile_text": run_demo.learned_rules.dump_rules([penalty, bonus]),
                    "learned_rules": [penalty, bonus],
                    "recent_decisions": [],
                }
                report = run_demo.write_report(
                    "demo", 1, "aggregate", context, scored, filtered, pending, weights
                ).read_text(encoding="utf-8")
                self.assertIn("learned_bonus_001,learned_penalty_001", report)
                self.assertIn("competition aggregate_delta=0 3->3", report)
        finally:
            run_demo.ROOT = original_root

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

    def test_run_demo_rejects_profile_id_and_seller_memory_symlink_aliases(self) -> None:
        original_root = run_demo.ROOT
        try:
            with tempfile.TemporaryDirectory() as temp:
                run_demo.ROOT = Path(temp)
                seller_a = run_demo.ROOT / "sellers/a"
                seller_b = run_demo.ROOT / "sellers/b"
                (seller_a / "decisions").mkdir(parents=True)
                (seller_b / "decisions").mkdir(parents=True)
                (seller_a / "profile.yaml").write_text(
                    "meta:\n  seller_id: wrong\nlearned: []\n", encoding="utf-8"
                )
                (seller_a / "sop.md").write_text("# A\n", encoding="utf-8")
                with self.assertRaisesRegex(SystemExit, "seller_id mismatch"):
                    run_demo.read_required_context("a")

                (seller_a / "profile.yaml").write_text(
                    "meta:\n  seller_id: a\nlearned: []\n", encoding="utf-8"
                )
                (seller_b / "sop.md").write_text("# B\n", encoding="utf-8")
                (seller_a / "sop.md").unlink()
                try:
                    (seller_a / "sop.md").symlink_to(seller_b / "sop.md")
                except OSError as exc:  # pragma: no cover
                    self.skipTest(f"symlink creation unavailable: {exc}")
                with self.assertRaisesRegex(SystemExit, "seller SOP must be a real"):
                    run_demo.read_required_context("a")

                (seller_a / "sop.md").unlink()
                (seller_a / "sop.md").write_text("# A\n", encoding="utf-8")
                outside_decision = seller_b / "decisions/outside.md"
                outside_decision.write_text("# outside\n", encoding="utf-8")
                (seller_a / "decisions/link.md").symlink_to(outside_decision)
                with self.assertRaisesRegex(SystemExit, "decision file must be a real"):
                    run_demo.read_required_context("a")
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
