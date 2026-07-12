from __future__ import annotations

import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "learned_rules", ROOT / "scripts" / "learned_rules.py"
)
assert SPEC and SPEC.loader
learned_rules = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(learned_rules)


def evidence(number: int = 1, *, session_id: str | None = None) -> dict:
    return {
        "decision_path": f"decisions/2026-07-0{number}_candidate-{number}.md",
        "decision_id": f"decision-{number}",
        "session_id": session_id or f"session:session-{number}",
        "source_report_id": f"reports/demo-{number}.md",
        "candidate_id": f"candidate-{number}",
        "decided_at": f"2026-07-0{number}",
    }


def rule(
    *,
    rule_id: str = "learned_tiktok_same_density_diff_001",
    version: int = 1,
    status: str = "proposed",
    dimension: str = "competition",
    delta: int = -1,
    expires_at: str | None = None,
) -> dict:
    confirmed = status != "proposed"
    revoked = status == "revoked"
    return {
        "rule_id": rule_id,
        "version": version,
        "summary": "This prose is descriptive and never executable.",
        "status": status,
        "scope": {
            "platforms": ["tiktok"],
            "markets": ["US"],
            "categories": [],
        },
        "condition_tag_ids": [
            "same_product_density_high",
            "differentiation_space_low",
        ],
        "action": {"dimension": dimension, "delta": delta},
        "evidence": [
            evidence(1, session_id="session:session-a"),
            evidence(2, session_id="session:session-a"),
            evidence(3, session_id="session:session-b"),
        ],
        "created": "2026-07-01",
        "confirmed_by": "reviewer@example" if confirmed else None,
        "confirmed_at": "2026-07-02T09:00:00Z" if confirmed else None,
        "revoked_by": "reviewer@example" if revoked else None,
        "revoked_at": "2026-07-03T09:00:00Z" if revoked else None,
        "revoke_reason": "seller strategy changed" if revoked else None,
        "expires_at": expires_at,
        "supersedes": None,
    }


class LearnedYamlTests(unittest.TestCase):
    def test_round_trip_replaces_only_learned_subtree(self) -> None:
        profile = (
            "meta:\n"
            "  seller_id: demo\n"
            "learned: []\n"
            "preferences:\n"
            "  risk_appetite: balanced\n"
        )
        rendered = learned_rules.replace_rules(profile, [rule()])
        loaded = learned_rules.load_rules(rendered)
        self.assertEqual([rule()], loaded)
        self.assertTrue(rendered.startswith("meta:\n  seller_id: demo\nlearned:\n"))
        self.assertTrue(rendered.endswith("preferences:\n  risk_appetite: balanced\n"))

    def test_save_and_find_return_mutable_rule(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            profile_path = Path(temp) / "profile.yaml"
            profile_path.write_text("meta:\n  seller_id: demo\nlearned: []\n", encoding="utf-8")
            learned_rules.save_rules(profile_path, [rule()])
            rules = learned_rules.load_rules(profile_path)
            found = learned_rules.find_rule(rules, "learned_tiktok_same_density_diff_001")
            self.assertIs(found, rules[0])
            with self.assertRaises(KeyError):
                learned_rules.find_rule(rules, "missing_rule")

    def test_save_uses_exclusive_temp_and_does_not_follow_fixed_tmp_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            profile_path = directory / "profile.yaml"
            profile_path.write_text(
                "meta:\n  seller_id: demo\nlearned: []\n", encoding="utf-8"
            )
            victim = directory / "victim.txt"
            victim.write_text("do not overwrite\n", encoding="utf-8")
            planted = directory / ".profile.yaml.learned.tmp"
            try:
                planted.symlink_to(victim)
            except OSError as exc:  # pragma: no cover
                self.skipTest(f"symlink creation unavailable: {exc}")

            learned_rules.save_rules(profile_path, [rule()])
            self.assertEqual("do not overwrite\n", victim.read_text(encoding="utf-8"))
            self.assertTrue(planted.is_symlink())
            self.assertEqual(1, len(learned_rules.load_rules(profile_path)))

    def test_save_cas_rejects_external_change_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            profile_path = Path(temp) / "profile.yaml"
            original = "meta:\n  seller_id: demo\nlearned: []\n"
            profile_path.write_text(original, encoding="utf-8")
            token = learned_rules.profile_content_hash(original)
            externally_edited = original + "preferences:\n  note: human-edit\n"
            profile_path.write_text(externally_edited, encoding="utf-8")

            with self.assertRaisesRegex(
                learned_rules.RuleValidationError, "concurrent edits"
            ):
                learned_rules.save_rules(
                    profile_path, [rule()], expected_hash=token
                )
            self.assertEqual(externally_edited, profile_path.read_text(encoding="utf-8"))

    def test_seller_context_rejects_alias_and_profile_id_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            seller = repo / "sellers/demo"
            (seller / "decisions").mkdir(parents=True)
            (seller / "profile.yaml").write_text(
                "meta:\n  seller_id: other\nlearned: []\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(
                learned_rules.RuleValidationError, "seller_id mismatch"
            ):
                learned_rules.validate_seller_context(repo, "demo")

            (seller / "profile.yaml").write_text(
                "meta:\n  seller_id: demo\nlearned: []\n", encoding="utf-8"
            )
            alias = repo / "sellers/alias"
            try:
                alias.symlink_to(seller, target_is_directory=True)
            except OSError as exc:  # pragma: no cover
                self.skipTest(f"symlink creation unavailable: {exc}")
            with self.assertRaisesRegex(
                learned_rules.RuleValidationError, "seller root must not be a symlink"
            ):
                learned_rules.validate_seller_context(repo, "alias")

    def test_strict_schema_rejects_text_action_and_zero_delta(self) -> None:
        invalid = rule()
        invalid["action"] = {"dimension": "competition", "delta": 0}
        with self.assertRaises(learned_rules.RuleValidationError):
            learned_rules.validate_rule(invalid)
        invalid = rule()
        invalid["action"]["prompt"] = "infer action from summary"
        with self.assertRaises(learned_rules.RuleValidationError):
            learned_rules.validate_rule(invalid)
        invalid = rule()
        invalid["evidence"][0]["source_report_id"] = "README.md"
        with self.assertRaises(learned_rules.RuleValidationError):
            learned_rules.validate_rule(invalid)
        invalid = rule()
        invalid["evidence"][0]["decision_path"] = "archive/a.md"
        with self.assertRaises(learned_rules.RuleValidationError):
            learned_rules.validate_rule(invalid)
        invalid = rule()
        invalid["evidence"] = invalid["evidence"][:1]
        with self.assertRaises(learned_rules.RuleValidationError):
            learned_rules.validate_rule(invalid)

    def test_active_rule_cannot_trust_nonexistent_evidence_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo_root = Path(temp)
            seller_root = repo_root / "sellers/demo"
            seller_root.mkdir(parents=True)
            with self.assertRaisesRegex(
                learned_rules.RuleValidationError, "Missing evidence file"
            ):
                learned_rules.validate_rule_evidence_files(
                    rule(status="active"), seller_root, repo_root
                )

    def test_proposed_successor_keeps_active_predecessor_effective(self) -> None:
        predecessor = rule(rule_id="learned_revision_001", status="active")
        successor = rule(
            rule_id="learned_revision_002", version=2, status="proposed"
        )
        successor["supersedes"] = predecessor["rule_id"]

        normalized = learned_rules.validate_rules([predecessor, successor])
        self.assertEqual(["active", "proposed"], [item["status"] for item in normalized])
        self.assertEqual(
            [predecessor["rule_id"]],
            [item["rule_id"] for item in learned_rules.active_rules(normalized)],
        )

    def test_supersedes_requires_newer_version_and_consistent_states(self) -> None:
        predecessor = rule(rule_id="learned_revision_001", status="active")
        successor = rule(rule_id="learned_revision_002", status="proposed")
        successor["supersedes"] = predecessor["rule_id"]
        with self.assertRaisesRegex(
            learned_rules.RuleValidationError, "version must be greater"
        ):
            learned_rules.validate_rules([predecessor, successor])

        successor["version"] = 2
        successor["status"] = "active"
        successor["confirmed_by"] = "reviewer@example"
        successor["confirmed_at"] = "2026-07-02T09:00:00Z"
        with self.assertRaisesRegex(
            learned_rules.RuleValidationError, "not superseded"
        ):
            learned_rules.validate_rules([predecessor, successor])

        predecessor["status"] = "superseded"
        successor["status"] = "proposed"
        successor["confirmed_by"] = None
        successor["confirmed_at"] = None
        with self.assertRaisesRegex(
            learned_rules.RuleValidationError, "active predecessor"
        ):
            learned_rules.validate_rules([predecessor, successor])

    def test_supersedes_graph_rejects_cycles(self) -> None:
        first = rule(rule_id="learned_cycle_001", version=1, status="superseded")
        second = rule(rule_id="learned_cycle_002", version=2, status="superseded")
        first["supersedes"] = second["rule_id"]
        second["supersedes"] = first["rule_id"]
        with self.assertRaisesRegex(learned_rules.RuleValidationError, "cycle"):
            learned_rules.validate_rules([first, second])

    def test_evidence_symlink_cannot_escape_decisions_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo_root = Path(temp)
            seller_root = repo_root / "sellers/demo"
            decisions_root = seller_root / "decisions"
            archive_root = seller_root / "archive"
            decisions_root.mkdir(parents=True)
            archive_root.mkdir()
            target = archive_root / "outside.md"
            target.write_text("# outside\n", encoding="utf-8")
            link = decisions_root / "link.md"
            try:
                link.symlink_to(target)
            except OSError as exc:  # pragma: no cover - platform permission fallback
                self.skipTest(f"symlink creation unavailable: {exc}")

            active = rule(status="active")
            active["evidence"][0]["decision_path"] = "decisions/link.md"
            with self.assertRaisesRegex(
                learned_rules.RuleValidationError, "escapes its allowed root"
            ):
                learned_rules.validate_rule_evidence_files(
                    active, seller_root, repo_root
                )


class RuleApplicationTests(unittest.TestCase):
    def apply(self, rules: list[dict], tags: list[str], score: int = 3) -> dict:
        return learned_rules.apply_rules(
            {"id": "candidate-1", "rule_tag_ids": tags},
            {"competition": score, "demand": 4, "margin": 3, "capability_fit": 4, "risk": 3},
            rules,
            platform="TikTok",
            market="us",
            category="pet",
            now="2026-07-12",
        )

    def test_proposed_rule_is_inactive_and_does_not_change_score(self) -> None:
        result = self.apply([rule(status="proposed")], list(learned_rules.DEMO_CONDITION_TAG_ORDER))
        self.assertEqual(3, result["scores"]["competition"])
        self.assertEqual([], result["effects"])
        self.assertEqual("proposed", result["inactive"][0]["status"])

    def test_active_rule_applies_only_when_all_tag_ids_match(self) -> None:
        active = rule(status="active")
        matching = self.apply([active], list(learned_rules.DEMO_CONDITION_TAG_ORDER))
        self.assertEqual(2, matching["scores"]["competition"])
        self.assertEqual(
            {
                "rule_id": "learned_tiktok_same_density_diff_001",
                "candidate_id": "candidate-1",
                "dimension": "competition",
                "delta": -1,
                "before": 3,
                "after": 2,
                "effect_kind": "isolated_contribution",
                "condition_tag_ids": list(learned_rules.DEMO_CONDITION_TAG_ORDER),
            },
            matching["effects"][0],
        )

        # A shoe crease protector may be crowded but still visually distinct.
        # The old summary/keyword matcher misapplied this rule; subset matching
        # must leave it unchanged when differentiation_space_low is absent.
        shoe = self.apply([active], ["same_product_density_high"])
        self.assertEqual(3, shoe["scores"]["competition"])
        self.assertEqual([], shoe["effects"])
        self.assertEqual("condition_not_met", shoe["skipped"][0]["reason"])

    def test_delta_clamps_to_zero_and_five(self) -> None:
        down = rule(status="active", delta=-5)
        result = self.apply([down], list(learned_rules.DEMO_CONDITION_TAG_ORDER), score=2)
        self.assertEqual(0, result["scores"]["competition"])
        self.assertEqual(0, result["effects"][0]["after"])

        up = rule(
            rule_id="learned_tiktok_margin_bonus_001",
            status="active",
            dimension="margin",
            delta=5,
        )
        result = self.apply([up], list(learned_rules.DEMO_CONDITION_TAG_ORDER))
        self.assertEqual(5, result["scores"]["margin"])
        self.assertEqual(5, result["effects"][0]["after"])

    def test_multiple_rule_deltas_clamp_once_and_ignore_yaml_order(self) -> None:
        bonus = rule(
            rule_id="learned_competition_bonus_001",
            status="active",
            delta=5,
        )
        penalty = rule(
            rule_id="learned_competition_penalty_001",
            status="active",
            delta=-5,
        )
        tags = list(learned_rules.DEMO_CONDITION_TAG_ORDER)
        forward = self.apply([bonus, penalty], tags, score=3)
        reverse = self.apply([penalty, bonus], tags, score=3)

        self.assertEqual(forward["scores"], reverse["scores"])
        self.assertEqual(forward["effects"], reverse["effects"])
        self.assertEqual(forward["aggregates"], reverse["aggregates"])
        self.assertEqual(3, forward["scores"]["competition"])
        self.assertEqual(
            {
                "dimension": "competition",
                "rule_ids": [
                    "learned_competition_bonus_001",
                    "learned_competition_penalty_001",
                ],
                "total_delta": 0,
                "before": 3,
                "after": 3,
            },
            forward["aggregates"][0],
        )

    def test_expired_revoked_and_superseded_rules_are_reported_inactive(self) -> None:
        expired = rule(
            rule_id="learned_expired_001",
            status="active",
            expires_at="2026-07-01",
        )
        revoked = rule(rule_id="learned_revoked_001", status="revoked")
        superseded = rule(rule_id="learned_superseded_001", status="superseded")
        replacement = rule(
            rule_id="learned_replacement_001", version=2, status="active"
        )
        replacement["supersedes"] = superseded["rule_id"]
        replacement["scope"]["platforms"] = ["amazon"]
        result = self.apply(
            [expired, revoked, superseded, replacement],
            list(learned_rules.DEMO_CONDITION_TAG_ORDER),
        )
        self.assertEqual(3, result["scores"]["competition"])
        self.assertEqual([], result["effects"])
        self.assertEqual(
            {"expired", "revoked", "superseded"},
            {item["status"] for item in result["inactive"]},
        )

    def test_summary_text_never_triggers_a_rule(self) -> None:
        active = rule(status="active")
        active["summary"] = "same_product_density_high differentiation_space_low competition -5"
        result = self.apply([active], [])
        self.assertEqual(3, result["scores"]["competition"])
        self.assertEqual([], result["effects"])


class DecisionAggregationTests(unittest.TestCase):
    @staticmethod
    def write_decision(
        directory: Path,
        number: int,
        *,
        date: str,
        report: str = "reports/_example/demo.md",
        explicit: bool = True,
        platform: str = "TikTok",
        market: str = "US",
        category: str | None = None,
    ) -> Path:
        structured = (
            f"- 决策ID: decision-{number}\n"
            f"- 候选ID: candidate-{number}\n"
            "- 归类标签ID: [same_product_density_high, differentiation_space_low]\n"
            if explicit
            else ""
        )
        path = directory / f"{date}_candidate-{number}.md"
        category_line = f"- 类目: {category}\n" if category is not None else ""
        path.write_text(
            f"# {date} | candidate-{number}\n\n"
            f"{structured}"
            f"- 来源报告: {report}\n"
            f"- 平台/来源: {platform}\n"
            f"- 市场: {market}\n"
            f"{category_line}"
            "- 用户决定: rejected\n"
            "- 归类标签: [同款过多, 差异化不足]\n",
            encoding="utf-8",
        )
        return path

    def test_parse_normalizes_none_and_session_falls_back_to_date(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_decision(Path(temp), 1, date="2026-07-01", report="无")
            text = path.read_text(encoding="utf-8")
            path.write_text(
                text.replace(
                    "- 平台/来源: TikTok",
                    "- 来源类型: historical_retrospective\n- 平台/来源: TikTok",
                ),
                encoding="utf-8",
            )
            parsed = learned_rules.parse_decision(path)
            self.assertIsNone(parsed["source_report_id"])
            self.assertEqual("tiktok", parsed["platform_id"])
            self.assertEqual("date:2026-07-01", learned_rules.independent_session_key(parsed))
            projected = learned_rules.evidence_from_decision(parsed)
            self.assertEqual("date:2026-07-01", projected["session_id"])
            self.assertEqual(
                "date:2026-07-01", learned_rules.independent_session_key(projected)
            )

    def test_aggregate_requires_three_unique_rejects_across_two_sessions(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            paths = [
                self.write_decision(directory, 1, date="2026-07-01"),
                self.write_decision(directory, 2, date="2026-07-01"),
                self.write_decision(directory, 3, date="2026-07-02"),
            ]
            aggregated = learned_rules.aggregate_demo_rule(paths, created="2026-07-12")
            assert aggregated is not None
            self.assertEqual("proposed", aggregated["status"])
            self.assertEqual(list(learned_rules.DEMO_CONDITION_TAG_ORDER), aggregated["condition_tag_ids"])
            self.assertEqual(3, len(aggregated["evidence"]))
            self.assertEqual(
                {"report-date:reports/_example/demo.md|2026-07-01", "report-date:reports/_example/demo.md|2026-07-02"},
                {item["session_id"] for item in aggregated["evidence"]},
            )

            # Repeating one file cannot manufacture three independent records.
            self.assertIsNone(
                learned_rules.aggregate_demo_rule([paths[0], paths[0], paths[0]], created="2026-07-12")
            )

    def test_aggregate_binds_normalized_evidence_platform_to_rule_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            tiktok_paths = [
                self.write_decision(
                    directory,
                    number,
                    date=f"2026-07-0{number}",
                    platform="TikTok US",
                )
                for number in range(1, 4)
            ]
            self.assertIsNotNone(
                learned_rules.aggregate_demo_rule(tiktok_paths, created="2026-07-12")
            )

        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            amazon_paths = [
                self.write_decision(
                    directory,
                    number,
                    date=f"2026-07-0{number}",
                    platform="Amazon US",
                )
                for number in range(1, 4)
            ]
            self.assertIsNone(
                learned_rules.aggregate_demo_rule(amazon_paths, created="2026-07-12")
            )

        for market in ("UK", "unknown"):
            with self.subTest(market=market), tempfile.TemporaryDirectory() as temp:
                directory = Path(temp)
                paths = [
                    self.write_decision(
                        directory,
                        number,
                        date=f"2026-07-0{number}",
                        market=market,
                    )
                    for number in range(1, 4)
                ]
                self.assertIsNone(
                    learned_rules.aggregate_demo_rule(
                        paths, created="2026-07-12", market="US"
                    )
                )

    def test_aggregate_requires_category_when_rule_scope_has_categories(self) -> None:
        scope = {
            "platforms": ["tiktok"],
            "markets": ["US"],
            "categories": ["home-goods"],
        }
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            missing = [
                self.write_decision(
                    directory, number, date=f"2026-07-0{number}"
                )
                for number in range(1, 4)
            ]
            self.assertIsNone(
                learned_rules.aggregate_demo_rule(
                    missing, created="2026-07-12", scope=scope
                )
            )

        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            matching = [
                self.write_decision(
                    directory,
                    number,
                    date=f"2026-07-0{number}",
                    category="Home Goods",
                )
                for number in range(1, 4)
            ]
            self.assertIsNotNone(
                learned_rules.aggregate_demo_rule(
                    matching, created="2026-07-12", scope=scope
                )
            )

    def test_aggregate_rejects_legacy_logs_without_explicit_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            paths = [
                self.write_decision(directory, number, date=f"2026-07-0{number}", explicit=False)
                for number in range(1, 4)
            ]
            self.assertIsNone(learned_rules.aggregate_demo_rule(paths, created="2026-07-12"))

    def test_legacy_labels_cannot_fill_missing_explicit_condition_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            paths = []
            for number in range(1, 4):
                path = self.write_decision(
                    directory,
                    number,
                    date=f"2026-07-0{number}",
                    explicit=True,
                )
                text = path.read_text(encoding="utf-8").replace(
                    "[same_product_density_high, differentiation_space_low]",
                    "[red_ocean_competition]",
                )
                path.write_text(text, encoding="utf-8")
                paths.append(path)
            self.assertIsNone(
                learned_rules.aggregate_demo_rule(paths, created="2026-07-12")
            )


if __name__ == "__main__":
    unittest.main()
