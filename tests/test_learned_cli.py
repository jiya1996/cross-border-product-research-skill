from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import confirm_learned  # noqa: E402
import learned_rules  # noqa: E402
import propose_learned  # noqa: E402
import revoke_learned  # noqa: E402


RULE_ID = propose_learned.DEMO_RULE_ID
TAG_IDS = ["same_product_density_high", "differentiation_space_low"]


class LearnedCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.seller_root = self.root / "sellers" / "demo"
        self.decisions = self.seller_root / "decisions"
        self.decisions.mkdir(parents=True)
        self.profile = self.seller_root / "profile.yaml"
        self.profile.write_text(
            'meta:\n  seller_id: "demo"\n  updated: "2026-07-12"\nlearned: []\n',
            encoding="utf-8",
        )
        self.original_confirm_root = confirm_learned.ROOT
        confirm_learned.ROOT = self.root

    def tearDown(self) -> None:
        confirm_learned.ROOT = self.original_confirm_root
        self.temp_dir.cleanup()

    def write_report(self, report_id: str, candidate_ids: list[str]) -> None:
        path = self.root / report_id
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = "\n".join(f"| {candidate_id} | product |" for candidate_id in candidate_ids)
        path.write_text(
            f"- 市场: US\n\n| candidate_id | product |\n|---|---|\n{rows}\n",
            encoding="utf-8",
        )

    def write_decision(
        self,
        name: str,
        *,
        candidate_id: str,
        report_id: str | None,
        decided_at: str,
        session_id: str | None = None,
        decision: str = "rejected",
        tag_ids: list[str] | None = None,
        record_type: str = "recommendation_review",
        market: str = "US",
    ) -> Path:
        path = self.decisions / f"{name}.md"
        fields = [
            f"# {decided_at} | {name}",
            "",
            f"- 决策ID: decision_{name}",
            f"- 候选ID: {candidate_id}",
            f"- 决策发生日期: {decided_at}",
            f"- 来源类型: {record_type}",
            f"- 来源报告: {report_id or '无'}",
            "- 平台/来源: TikTok",
            f"- 市场: {market}",
            f"- 用户决定: {decision}",
            f"- 归类标签ID: [{', '.join(tag_ids if tag_ids is not None else TAG_IDS)}]",
        ]
        if session_id is not None:
            fields.insert(4, f"- 决策会话ID: {session_id}")
        path.write_text("\n".join(fields) + "\n", encoding="utf-8")
        return path

    def seed_valid_decisions(self) -> None:
        self.write_report("reports/demo/r1.md", ["c1", "c2"])
        self.write_report("reports/demo/r2.md", ["c3"])
        self.write_decision(
            "one", candidate_id="c1", report_id="reports/demo/r1.md", decided_at="2026-07-10"
        )
        self.write_decision(
            "two", candidate_id="c2", report_id="reports/demo/r1.md", decided_at="2026-07-10"
        )
        self.write_decision(
            "three", candidate_id="c3", report_id="reports/demo/r2.md", decided_at="2026-07-11"
        )

    def propose_valid_rule(self) -> dict:
        self.seed_valid_decisions()
        rule, changed = propose_learned.propose_rule(
            self.profile, self.decisions, created="2026-07-12"
        )
        self.assertTrue(changed)
        return rule

    def test_propose_requires_three_rejections_from_two_sessions(self) -> None:
        self.write_report("reports/demo/one.md", ["c1", "c2", "c3"])
        for index in range(1, 4):
            self.write_decision(
                f"same-{index}",
                candidate_id=f"c{index}",
                report_id="reports/demo/one.md",
                decided_at="2026-07-10",
            )

        self.assertIsNone(
            propose_learned.aggregate_candidate_rule(self.decisions, created="2026-07-12")
        )
        with self.assertRaisesRegex(SystemExit, ">=2 independent sessions"):
            propose_learned.propose_rule(self.profile, self.decisions, created="2026-07-12")

    def test_propose_persists_structured_rule_with_fixed_id(self) -> None:
        proposed = self.propose_valid_rule()
        self.assertEqual(RULE_ID, proposed["rule_id"])
        self.assertEqual("proposed", proposed["status"])
        self.assertEqual(TAG_IDS, proposed["condition_tag_ids"])
        self.assertEqual({"dimension": "competition", "delta": -1}, proposed["action"])
        self.assertEqual(["tiktok"], proposed["scope"]["platforms"])
        self.assertEqual(["US"], proposed["scope"]["markets"])
        persisted = learned_rules.find_rule(learned_rules.load_rules(self.profile), RULE_ID)
        self.assertEqual(proposed, persisted)

    def test_normal_feedback_treats_a_different_report_date_as_a_new_session(self) -> None:
        self.write_report("reports/demo/one.md", ["c1", "c2", "c3"])
        for name, candidate_id, decided_at in [
            ("one", "c1", "2026-07-10"),
            ("two", "c2", "2026-07-10"),
            ("three", "c3", "2026-07-11"),
        ]:
            self.write_decision(
                name,
                candidate_id=candidate_id,
                report_id="reports/demo/one.md",
                decided_at=decided_at,
            )
        proposed = propose_learned.aggregate_candidate_rule(
            self.decisions, created="2026-07-12"
        )
        self.assertIsNotNone(proposed)
        assert proposed is not None
        self.assertEqual(
            2,
            len(
                {
                    learned_rules.independent_session_key(item)
                    for item in proposed["evidence"]
                }
            ),
        )

    def test_normal_feedback_cannot_split_one_report_date_with_session_ids(self) -> None:
        self.write_report("reports/demo/one.md", ["c1", "c2", "c3"])
        for name, candidate_id, session_id in [
            ("one", "c1", "session:a"),
            ("two", "c2", "session:a"),
            ("three", "c3", "session:b"),
        ]:
            self.write_decision(
                name,
                candidate_id=candidate_id,
                report_id="reports/demo/one.md",
                decided_at="2026-07-10",
                session_id=session_id,
            )
        self.assertIsNone(
            propose_learned.aggregate_candidate_rule(
                self.decisions, created="2026-07-12"
            )
        )

    def test_historical_retrospective_can_use_explicit_sessions(self) -> None:
        for name, candidate_id, session_id in [
            ("one", "h1", "retrospective-a"),
            ("two", "h2", "retrospective-a"),
            ("three", "h3", "retrospective-b"),
        ]:
            path = self.write_decision(
                name,
                candidate_id=candidate_id,
                report_id=None,
                decided_at="unknown",
                session_id=session_id,
                record_type="historical_retrospective",
            )
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    "来源报告: 无", "来源报告: 无（历史复盘）"
                ),
                encoding="utf-8",
            )
        proposed = propose_learned.aggregate_candidate_rule(
            self.decisions, created="2026-07-12"
        )
        self.assertIsNotNone(proposed)
        assert proposed is not None
        self.assertEqual(
            {"session:retrospective-a", "session:retrospective-b"},
            {item["session_id"] for item in proposed["evidence"]},
        )
        persisted, changed = propose_learned.propose_rule(
            self.profile, self.decisions, created="2026-07-12"
        )
        self.assertTrue(changed)
        self.assertTrue(all(item["decided_at"] is None for item in persisted["evidence"]))
        active = confirm_learned.confirm_rule(
            self.profile,
            self.seller_root,
            RULE_ID,
            "owner@example",
            confirmed_at="2026-07-12T00:00:00+00:00",
        )
        self.assertEqual("active", active["status"])

    def test_historical_retrospective_can_use_event_dates_without_reports(self) -> None:
        self.write_decision(
            "history-one",
            candidate_id="h1",
            report_id=None,
            decided_at="2026-06-01",
            record_type="historical_retrospective",
        )
        self.write_decision(
            "history-two",
            candidate_id="h2",
            report_id=None,
            decided_at="2026-06-01",
            record_type="historical_retrospective",
        )
        self.write_decision(
            "history-three",
            candidate_id="h3",
            report_id=None,
            decided_at="2026-06-05",
            record_type="historical_retrospective",
        )

        proposed, changed = propose_learned.propose_rule(
            self.profile, self.decisions, created="2026-07-12"
        )
        self.assertTrue(changed)
        self.assertEqual(
            2,
            len(
                {
                    learned_rules.independent_session_key(item)
                    for item in proposed["evidence"]
                }
            ),
        )
        active = confirm_learned.confirm_rule(
            self.profile,
            self.seller_root,
            RULE_ID,
            "owner@example",
            confirmed_at="2026-07-12T00:00:00+00:00",
        )
        self.assertEqual("active", active["status"])

    def test_confirm_cli_has_no_default_index_or_all_mode(self) -> None:
        with redirect_stderr(StringIO()):
            with mock.patch.object(
                sys, "argv", ["confirm_learned.py", "demo", "--confirmed-by", "owner"]
            ):
                with self.assertRaises(SystemExit):
                    confirm_learned.parse_args()
            with mock.patch.object(
                sys,
                "argv",
                [
                    "confirm_learned.py",
                    "demo",
                    "--rule-id",
                    RULE_ID,
                    "--confirmed-by",
                    "owner",
                    "--all",
                ],
            ):
                with self.assertRaises(SystemExit):
                    confirm_learned.parse_args()

    def test_confirm_revalidates_rejected_state_and_does_not_mutate_on_failure(self) -> None:
        self.propose_valid_rule()
        path = self.decisions / "three.md"
        path.write_text(
            path.read_text(encoding="utf-8").replace("用户决定: rejected", "用户决定: watchlist"),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(SystemExit, "must be rejected"):
            confirm_learned.confirm_rule(self.profile, self.seller_root, RULE_ID, "owner")
        rule = learned_rules.find_rule(learned_rules.load_rules(self.profile), RULE_ID)
        self.assertEqual("proposed", rule["status"])

    def test_confirm_revalidates_condition_tags(self) -> None:
        self.propose_valid_rule()
        path = self.decisions / "three.md"
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "same_product_density_high, differentiation_space_low",
                "same_product_density_high",
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(SystemExit, "missing condition tag IDs"):
            confirm_learned.confirm_rule(self.profile, self.seller_root, RULE_ID, "owner")

    def test_confirm_revalidates_evidence_platform_against_rule_scope(self) -> None:
        self.propose_valid_rule()
        path = self.decisions / "three.md"
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "平台/来源: TikTok", "平台/来源: Amazon US"
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(SystemExit, "outside rule scope"):
            confirm_learned.confirm_rule(
                self.profile, self.seller_root, RULE_ID, "owner"
            )

    def test_confirm_revalidates_evidence_market_against_rule_scope(self) -> None:
        self.propose_valid_rule()
        path = self.decisions / "three.md"
        original = path.read_text(encoding="utf-8")
        for market in ("UK", "unknown"):
            with self.subTest(market=market):
                path.write_text(
                    original.replace("市场: US", f"市场: {market}"),
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(SystemExit, "outside rule scope"):
                    confirm_learned.confirm_rule(
                        self.profile, self.seller_root, RULE_ID, "owner"
                    )
        path.write_text(original, encoding="utf-8")

    def test_confirm_rejects_cross_seller_source_report_namespace(self) -> None:
        self.propose_valid_rule()
        self.write_report("reports/other/r2.md", ["c3"])
        path = self.decisions / "three.md"
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "reports/demo/r2.md", "reports/other/r2.md"
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(SystemExit, "inside reports/demo/"):
            confirm_learned.confirm_rule(
                self.profile, self.seller_root, RULE_ID, "owner"
            )

    def test_confirm_checks_candidate_is_in_source_report(self) -> None:
        self.propose_valid_rule()
        self.write_report("reports/demo/r2.md", ["different-candidate"])
        report = self.root / "reports/demo/r2.md"
        report.write_text(
            report.read_text(encoding="utf-8")
            + "\n备注：c3 曾被讨论，但没有进入本报告候选表。\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(SystemExit, "absent from source report"):
            confirm_learned.confirm_rule(self.profile, self.seller_root, RULE_ID, "owner")

    def test_confirm_activates_exact_rule_and_records_actor(self) -> None:
        self.propose_valid_rule()
        activated = confirm_learned.confirm_rule(
            self.profile,
            self.seller_root,
            RULE_ID,
            "seller-owner",
            confirmed_at="2026-07-12T00:00:00+00:00",
        )
        self.assertEqual("active", activated["status"])
        self.assertEqual("seller-owner", activated["confirmed_by"])
        self.assertEqual("2026-07-12T00:00:00+00:00", activated["confirmed_at"])
        with self.assertRaisesRegex(SystemExit, "only proposed"):
            confirm_learned.confirm_rule(
                self.profile, self.seller_root, RULE_ID, "seller-owner"
            )
        with self.assertRaisesRegex(SystemExit, "Unknown learned rule_id"):
            confirm_learned.confirm_rule(
                self.profile, self.seller_root, "missing-rule", "seller-owner"
            )

    def test_confirm_successor_atomically_supersedes_active_predecessor(self) -> None:
        proposed = self.propose_valid_rule()
        predecessor = copy.deepcopy(proposed)
        predecessor["rule_id"] = "learned_tiktok_same_density_diff_000"
        predecessor["status"] = "active"
        predecessor["confirmed_by"] = "seller-owner"
        predecessor["confirmed_at"] = "2026-07-11T00:00:00+00:00"

        successor = copy.deepcopy(proposed)
        successor["version"] = 2
        successor["supersedes"] = predecessor["rule_id"]
        learned_rules.save_rules(self.profile, [predecessor, successor])

        with mock.patch.object(
            learned_rules, "save_rules", wraps=learned_rules.save_rules
        ) as save_rules:
            activated = confirm_learned.confirm_rule(
                self.profile,
                self.seller_root,
                RULE_ID,
                "seller-owner",
                confirmed_at="2026-07-12T00:00:00+00:00",
            )
        self.assertEqual(1, save_rules.call_count)
        self.assertEqual("active", activated["status"])

        persisted = {
            item["rule_id"]: item for item in learned_rules.load_rules(self.profile)
        }
        self.assertEqual("active", persisted[RULE_ID]["status"])
        self.assertEqual(
            "superseded", persisted[predecessor["rule_id"]]["status"]
        )
        self.assertEqual(
            [RULE_ID],
            [
                item["rule_id"]
                for item in learned_rules.active_rules(list(persisted.values()))
            ],
        )

    def test_expired_successor_cannot_confirm_or_supersede_predecessor(self) -> None:
        proposed = self.propose_valid_rule()
        predecessor = copy.deepcopy(proposed)
        predecessor["rule_id"] = "learned_tiktok_same_density_diff_000"
        predecessor["status"] = "active"
        predecessor["confirmed_by"] = "seller-owner"
        predecessor["confirmed_at"] = "2026-07-10T00:00:00+00:00"

        successor = copy.deepcopy(proposed)
        successor["version"] = 2
        successor["supersedes"] = predecessor["rule_id"]
        successor["expires_at"] = "2026-07-11T00:00:00+00:00"
        learned_rules.save_rules(self.profile, [predecessor, successor])

        with self.assertRaisesRegex(SystemExit, "expired"):
            confirm_learned.confirm_rule(
                self.profile,
                self.seller_root,
                RULE_ID,
                "seller-owner",
                confirmed_at="2026-07-12T00:00:00+00:00",
            )
        persisted = {
            item["rule_id"]: item for item in learned_rules.load_rules(self.profile)
        }
        self.assertEqual("active", persisted[predecessor["rule_id"]]["status"])
        self.assertEqual("proposed", persisted[RULE_ID]["status"])

    def test_all_learned_write_entries_reject_profile_seller_id_mismatch(self) -> None:
        self.seed_valid_decisions()
        self.profile.write_text(
            self.profile.read_text(encoding="utf-8").replace(
                'seller_id: "demo"', 'seller_id: "other"'
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(SystemExit, "seller_id mismatch"):
            propose_learned.propose_rule(
                self.profile, self.decisions, created="2026-07-12"
            )
        with self.assertRaisesRegex(SystemExit, "seller_id mismatch"):
            confirm_learned.confirm_rule(
                self.profile, self.seller_root, RULE_ID, "owner"
            )
        with self.assertRaisesRegex(SystemExit, "seller_id mismatch"):
            revoke_learned.revoke_rule(
                self.profile, RULE_ID, "owner", "test mismatch"
            )

    def test_revoke_requires_active_rule_and_retains_audit_fields(self) -> None:
        self.propose_valid_rule()
        with self.assertRaisesRegex(SystemExit, "only active"):
            revoke_learned.revoke_rule(self.profile, RULE_ID, "seller-owner", "not useful")
        confirm_learned.confirm_rule(
            self.profile,
            self.seller_root,
            RULE_ID,
            "seller-owner",
            confirmed_at="2026-07-12T00:00:00+00:00",
        )
        revoked = revoke_learned.revoke_rule(
            self.profile,
            RULE_ID,
            "seller-owner",
            "New evidence disproved it",
            revoked_at="2026-07-13T00:00:00+00:00",
        )
        self.assertEqual("revoked", revoked["status"])
        self.assertEqual("seller-owner", revoked["confirmed_by"])
        self.assertEqual("seller-owner", revoked["revoked_by"])
        self.assertEqual("New evidence disproved it", revoked["revoke_reason"])
        self.assertEqual("2026-07-13T00:00:00+00:00", revoked["revoked_at"])


if __name__ == "__main__":
    unittest.main()
