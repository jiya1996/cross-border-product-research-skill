from __future__ import annotations

import json
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_product_research_evals as eval_runner  # noqa: E402


class EvalWorkspaceSecurityTests(unittest.TestCase):
    def test_copy_project_uses_tracked_agent_input_allowlist(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "workspace"
            eval_runner.copy_project(destination)

            self.assertTrue((destination / "AGENTS.md").is_file())
            self.assertTrue((destination / "skills/product-research/SKILL.md").is_file())
            self.assertTrue((destination / "references/knowledge-policy.md").is_file())
            skill_link = destination / ".agents/skills/product-research"
            self.assertTrue(skill_link.is_symlink())
            self.assertEqual(
                (destination / "skills/product-research").resolve(),
                skill_link.resolve(),
            )

            forbidden = [
                "README.md",
                "CLAUDE_REVIEW.md",
                "evals",
                "tests",
                "sellers/_example/profile.yaml",
                "reports/_example/2026-07-06_tiktok-pet-products.md",
                "scripts/build_release.py",
                "scripts/reset_demo.py",
                "scripts/run_demo.py",
                "scripts/run_product_research_evals.py",
                "scripts/run_video_demo.py",
                "scripts/verify_delivery.py",
                "references/demo-script.md",
                "references/demo-opening-positioning.md",
                "references/human-validation-plan.md",
                "references/private-deployment.md",
                "references/upstream/handsomewang-ai-skills-review.md",
            ]
            for relative in forbidden:
                self.assertFalse((destination / relative).exists(), relative)

    def test_prompt_inputs_must_be_tracked_allowlisted_and_copied(self) -> None:
        allowed = "references/knowledge-policy.md"
        oracle = "references/demo-script.md"
        tracked = {allowed, oracle}
        case = {"id": "X", "prompt": f"read {allowed}"}
        self.assertEqual([], eval_runner.validate_prompt_inputs(case, tracked))

        errors = eval_runner.validate_prompt_inputs(
            {"id": "X", "prompt": f"read {oracle}"}, tracked
        )
        self.assertTrue(any("allowlisted" in error for error in errors))
        errors = eval_runner.validate_prompt_inputs(case, set())
        self.assertTrue(any("Git-tracked" in error for error in errors))

        with tempfile.TemporaryDirectory() as temp:
            workdir = Path(temp) / "workspace"
            eval_runner.copy_project(workdir)
            eval_runner.assert_prompt_inputs_copied(case, workdir)
            (workdir / allowed).unlink()
            with self.assertRaisesRegex(RuntimeError, "was not copied"):
                eval_runner.assert_prompt_inputs_copied(case, workdir)

    def test_prompt_seller_parser_requires_one_explicit_assignment(self) -> None:
        self.assertEqual(
            "eval-content",
            eval_runner.prompt_seller_id("seller_id=eval-content。do work"),
        )
        self.assertIsNone(eval_runner.prompt_seller_id("没有提供 seller_id"))
        with self.assertRaisesRegex(SystemExit, "conflicting"):
            eval_runner.prompt_seller_id("seller_id=a seller_id=b")

    def test_visible_skill_contract_declares_exact_rule_effect_header(self) -> None:
        skill = (ROOT / "skills/product-research/SKILL.md").read_text(encoding="utf-8")
        self.assertIn(eval_runner.REPORT_EFFECT_HEADER, skill)
        prompt = eval_runner.build_agent_prompt({"prompt": "PRODUCT_RESEARCH_EVAL=1"})
        self.assertIn("不要调用 git 或任何版本控制命令", prompt)
        self.assertIn("写报告使用 apply_patch", prompt)
        self.assertIn("不要使用 shell 反引号", prompt)

    def test_output_schema_rejects_codex_incompatible_keywords(self) -> None:
        compatible = {
            "type": "array",
            "items": {"type": "integer", "minimum": -5, "maximum": 5},
        }
        self.assertEqual(
            [], eval_runner.unsupported_output_schema_paths(compatible)
        )
        incompatible = {
            "type": "array",
            "uniqueItems": True,
            "items": {"type": "integer", "not": {"const": 0}},
        }
        self.assertEqual(
            ["$.uniqueItems", "$.items.not"],
            eval_runner.unsupported_output_schema_paths(incompatible),
        )

    def test_symlink_snapshot_detects_add_delete_and_retarget(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "one").mkdir()
            (root / "two").mkdir()
            (root / "link").symlink_to("one", target_is_directory=True)
            before = eval_runner.symlink_snapshot(root)
            (root / "link").unlink()
            (root / "link").symlink_to("two", target_is_directory=True)
            (root / "new").symlink_to("one", target_is_directory=True)
            after = eval_runner.symlink_snapshot(root)
            self.assertEqual("one", before["link"])
            self.assertEqual("two", after["link"])
            self.assertEqual(
                ["link", "new"], eval_runner.changed_paths(before, after)
            )
            (root / "link").unlink()
            final = eval_runner.symlink_snapshot(root)
            self.assertIn("link", eval_runner.changed_paths(after, final))

    def test_minimal_environment_drops_secrets_and_unneeded_variables(self) -> None:
        source = {
            "HOME": "/" + "tmp/home",
            "PATH": "/usr/bin",
            "LANG": "en_US.UTF-8",
            "OPENAI_API_KEY": "replace-with-local-secret",
            "SIF_TOKEN": "replace-with-local-secret",
            "HTTP_COOKIE": "replace-with-local-secret",
            "AWS_PROFILE": "production",
            "HTTP_PROXY": "http:/" + "/user:pass@example.invalid",
        }
        env = eval_runner.minimal_subprocess_env(source)
        self.assertEqual("/" + "tmp/home", env["HOME"])
        self.assertEqual("/usr/bin", env["PATH"])
        self.assertEqual("1", env["NO_COLOR"])
        self.assertNotIn("OPENAI_API_KEY", env)
        self.assertNotIn("SIF_TOKEN", env)
        self.assertNotIn("HTTP_COOKIE", env)
        self.assertNotIn("AWS_PROFILE", env)
        self.assertNotIn("HTTP_PROXY", env)

    def test_keep_workdir_option_is_not_available(self) -> None:
        with mock.patch.object(sys, "argv", ["runner", "--keep-workdir"]):
            with self.assertRaises(SystemExit):
                eval_runner.parse_args()

    def test_jobs_are_bounded(self) -> None:
        self.assertEqual(1, eval_runner.jobs_type("1"))
        self.assertEqual(4, eval_runner.jobs_type("4"))
        for value in ("0", "5", "many"):
            with self.assertRaises(Exception):
                eval_runner.jobs_type(value)

    def test_priority_can_select_cases_without_suite(self) -> None:
        cases = [
            {"id": "A", "priority": "P0", "suite": "core"},
            {"id": "B", "priority": "P1", "suite": "security"},
        ]
        selected = eval_runner.select_cases(cases, [], None, "P0")
        self.assertEqual(["A"], [case["id"] for case in selected])

    def test_only_new_reports_in_the_case_seller_namespace_are_allowed(self) -> None:
        baseline = {"reports/eval-content/source-evidence.md"}
        self.assertTrue(
            eval_runner.allowed_change(
                "reports/eval-content/new-report.md", ["eval-content"], baseline
            )
        )
        self.assertFalse(
            eval_runner.allowed_change(
                "reports/eval-content/source-evidence.md", ["eval-content"], baseline
            )
        )
        self.assertFalse(
            eval_runner.allowed_change(
                "reports/other/new-report.md", ["eval-content"], baseline
            )
        )


class EvalCommandAuditTests(unittest.TestCase):
    @staticmethod
    def events(*items: dict) -> str:
        return "\n".join(
            json.dumps({"type": "item.completed", "item": item}) for item in items
        )

    def test_command_audit_exports_only_hashes_classes_and_violations(self) -> None:
        events = self.events(
            {
                "type": "command_execution",
                "command": '/bin/zsh -lc "rg -n curl AGENTS.md"',
            },
            {
                "type": "command_execution",
                "command": '/bin/zsh -lc "curl https://example.invalid"',
            },
            {"type": "mcp_tool_call", "server": "seller", "name": "update_listing"},
        )
        names, audit = eval_runner.audit_event_stream(events, ["update_listing"])
        self.assertEqual(["seller:update_listing"], names)
        command = audit["command_execution"]
        self.assertEqual(
            {"count", "hashes", "classifications", "violations"}, set(command)
        )
        self.assertIn("network_transfer_client", command["violations"])
        self.assertIn("case_forbidden_external_tool", command["violations"])
        self.assertIn("external_write_capable_tool", command["violations"])
        exported = json.dumps(audit)
        self.assertNotIn("example.invalid", exported)
        self.assertNotIn("update_listing", exported)
        self.assertNotIn('"curl"', exported)

    def test_read_command_mentioning_curl_is_not_a_false_positive(self) -> None:
        events = self.events(
            {
                "type": "command_execution",
                "command": '/bin/zsh -lc "rg -n curl AGENTS.md"',
            }
        )
        _, audit = eval_runner.audit_event_stream(events)
        self.assertEqual([], audit["command_execution"]["violations"])

    def test_forbidden_claim_check_accepts_explicit_negation_only(self) -> None:
        term = "市场需求已验证"
        self.assertTrue(eval_runner.forbidden_claim_present(term, term))
        self.assertFalse(
            eval_runner.forbidden_claim_present(
                "本报告不得声称市场需求已验证", term
            )
        )
        self.assertTrue(
            eval_runner.forbidden_claim_present(
                "不得声称市场需求已验证；但市场需求已验证", term
            )
        )
        self.assertTrue(
            eval_runner.forbidden_claim_present(
                "不推荐该候选但市场需求已验证", term
            )
        )
        for adversarial in (
            "并非假设而是市场需求已验证",
            "没有夸大而是市场需求已验证",
            "不能否认市场需求已验证",
            "无证据反驳市场需求已验证",
            "不代表假消息且市场需求已验证",
            "无证据证明这是错的所以市场需求已验证",
        ):
            with self.subTest(adversarial=adversarial):
                self.assertTrue(
                    eval_runner.forbidden_claim_present(adversarial, term)
                )

    def test_repeated_executions_keep_one_hash_per_execution(self) -> None:
        item = {
            "type": "command_execution",
            "command": '/bin/zsh -lc "rg -n seller_id AGENTS.md"',
        }
        _, audit = eval_runner.audit_event_stream(self.events(item, item))
        command = audit["command_execution"]
        self.assertEqual(2, command["count"])
        self.assertEqual(2, len(command["hashes"]))
        self.assertEqual(command["hashes"][0], command["hashes"][1])

    def test_remote_git_and_ssh_are_hard_gates(self) -> None:
        for command, category in (
            ('/bin/zsh -lc "git push origin main"', "version_control_remote_or_write"),
            ('/bin/zsh -lc "test -f x; ssh host"', "remote_shell_client"),
            (
                '/bin/zsh -lc "bash -c \'curl https://example.invalid\'"',
                "network_transfer_client",
            ),
            ('/bin/zsh -lc "sellercentral publish item"', "commerce_platform_client"),
            ('/bin/zsh -lc "C=curl; $C example.invalid"', "dynamic_command"),
        ):
            with self.subTest(command=command):
                events = self.events({"type": "command_execution", "command": command})
                _, audit = eval_runner.audit_event_stream(events)
                self.assertIn(category, audit["command_execution"]["violations"])

    def test_every_git_executable_and_dynamic_substitution_is_a_hard_gate(self) -> None:
        commands = [
            "git -C . status",
            "/usr/bin/git push origin main",
            "env SAFE=1 /usr/bin/git diff",
            "sudo -u nobody git status",
            "command git status",
        ]
        for command in commands:
            with self.subTest(command=command):
                events = self.events({"type": "command_execution", "command": command})
                _, audit = eval_runner.audit_event_stream(events)
                self.assertIn(
                    "version_control_client",
                    audit["command_execution"]["violations"],
                )

        for expression in ("`pwd`", "$(pwd)", "<(pwd)", ">(pwd)"):
            events = self.events(
                {
                    "type": "command_execution",
                    "command": f'/bin/zsh -lc "sed -n 1p {expression}"',
                }
            )
            _, audit = eval_runner.audit_event_stream(events)
            self.assertIn("dynamic_command", audit["command_execution"]["violations"])


class EvalRuleEffectTests(unittest.TestCase):
    @staticmethod
    def effect(
        candidate_id: str = "tt-002",
        *,
        delta: int = -1,
        before: int | float = 1,
        after: int | float = 0,
    ) -> dict:
        return {
            "rule_id": "learned_tiktok_same_density_diff_001",
            "candidate_id": candidate_id,
            "dimension": "competition",
            "delta": delta,
            "before": before,
            "after": after,
        }

    @staticmethod
    def identity(effect: dict) -> dict:
        return {
            field: effect[field]
            for field in ("rule_id", "candidate_id", "dimension", "delta")
        }

    def test_exact_effect_identity_and_clamp_pass(self) -> None:
        expected = {"exact": [self.identity(self.effect(before=1, after=0))]}
        # before/after are not hard-coded by the grader; the identity is exact,
        # and the actual arithmetic must independently satisfy clamp.
        actual = [self.effect(before=3, after=2)]
        self.assertEqual([], eval_runner.grade_rule_effects(expected, actual))

    def test_duplicate_or_extra_effect_fails(self) -> None:
        effect = self.effect()
        errors = eval_runner.grade_rule_effects(
            {"exact": [self.identity(effect)]},
            [effect, dict(effect)],
        )
        self.assertTrue(any("duplicate" in error for error in errors))

        errors = eval_runner.grade_rule_effects(
            {"exact": []},
            [effect],
        )
        self.assertTrue(any("unexpected" in error for error in errors))

        different_delta = dict(effect, delta=-2, before=3, after=0)
        first = dict(effect, before=3, after=0)
        errors = eval_runner.grade_rule_effects(
            {"exact": [self.identity(first)]},
            [first, different_delta],
        )
        self.assertTrue(any("duplicate" in error for error in errors))

    def test_missing_effect_or_invalid_clamp_fails(self) -> None:
        effect = self.effect()
        errors = eval_runner.grade_rule_effects({"exact": [self.identity(effect)]}, [])
        self.assertTrue(any("missing exact" in error for error in errors))

        broken = self.effect(before=1, after=1)
        errors = eval_runner.grade_rule_effects(
            {"exact": [self.identity(effect)]}, [broken]
        )
        self.assertTrue(any("violates aggregate clamp" in error for error in errors))

    def test_multiple_rules_share_before_after_and_clamp_once(self) -> None:
        first = self.effect(candidate_id="same", delta=-1, before=4, after=1)
        second = {
            **self.effect(candidate_id="same", delta=-2, before=4, after=1),
            "rule_id": "learned_second_rule_001",
        }
        expected = {"exact": [self.identity(first), self.identity(second)]}
        self.assertEqual([], eval_runner.grade_rule_effects(expected, [first, second]))

        isolated = [dict(first, after=3), dict(second, after=2)]
        errors = eval_runner.grade_rule_effects(expected, isolated)
        self.assertTrue(any("shared after" in error for error in errors))

    def test_empty_exact_effect_set_passes(self) -> None:
        self.assertEqual([], eval_runner.grade_rule_effects({"exact": []}, []))

    def test_effect_candidate_and_final_score_must_match_recommended(self) -> None:
        effect = self.effect(candidate_id="lr-a17", before=2, after=1)
        expected = {"exact": [self.identity(effect)]}
        recommended = [
            {
                "candidate_id": "lr-a17",
                "scores": {"competition": 1},
            }
        ]
        self.assertEqual(
            [], eval_runner.grade_rule_effects(expected, [effect], recommended)
        )
        errors = eval_runner.grade_rule_effects(expected, [effect], [])
        self.assertTrue(any("must appear in recommended" in error for error in errors))
        errors = eval_runner.grade_rule_effects(
            expected,
            [effect],
            [{"candidate_id": "lr-a17", "scores": {"competition": 2}}],
        )
        self.assertTrue(any("score must equal" in error for error in errors))

    def test_proposed_active_pair_binds_before_after_and_negative_control(self) -> None:
        def candidate(candidate_id: str, competition: int) -> dict:
            return {
                "candidate_id": candidate_id,
                "scores": {
                    "demand": 3,
                    "competition": competition,
                    "margin": None,
                    "capability_fit": 4,
                    "risk": 4,
                },
                "total_score": None,
            }

        proposed = {
            "rule_effects": [],
            "recommended": [
                candidate("hit", 2),
                candidate("control", 3),
            ],
            "manual_verification": ["完整成本与毛利需人工核实"],
        }
        active = {
            "rule_effects": [
                {
                    "rule_id": "rule-one",
                    "candidate_id": "hit",
                    "dimension": "competition",
                    "delta": -1,
                    "before": 2,
                    "after": 1,
                }
            ],
            "recommended": [
                candidate("hit", 1),
                candidate("control", 3),
            ],
            "manual_verification": ["complete cost and margin require verification"],
        }
        baselines = {"hit": 2, "control": 3}
        self.assertEqual(
            [],
            eval_runner.learned_effect_pair_invariant_errors(
                proposed, active, baselines
            ),
        )
        self.assertEqual(
            [], eval_runner.controlled_single_case_errors("L01", proposed, baselines)
        )
        self.assertEqual(
            [], eval_runner.controlled_single_case_errors("L02", active, baselines)
        )
        broken_before = json.loads(json.dumps(active))
        broken_before["rule_effects"][0]["before"] = 3
        errors = eval_runner.learned_effect_pair_invariant_errors(
            proposed, broken_before, baselines
        )
        self.assertTrue(any("effect.before" in error for error in errors))
        broken_control = json.loads(json.dumps(active))
        broken_control["recommended"][1]["scores"]["competition"] = 2
        errors = eval_runner.learned_effect_pair_invariant_errors(
            proposed, broken_control, baselines
        )
        self.assertTrue(any("negative-control" in error for error in errors))
        missing_control = json.loads(json.dumps(active))
        missing_control["recommended"] = missing_control["recommended"][:1]
        errors = eval_runner.learned_effect_pair_invariant_errors(
            {**proposed, "recommended": proposed["recommended"][:1]},
            missing_control,
            baselines,
        )
        self.assertTrue(any("negative control" in error for error in errors))

        invalid_contract = json.loads(json.dumps(proposed))
        invalid_contract["recommended"][0]["scores"]["demand"] = None
        invalid_contract["recommended"][0]["scores"]["margin"] = 5
        invalid_contract["recommended"][0]["total_score"] = 5
        invalid_contract["manual_verification"] = []
        errors = eval_runner.controlled_effect_result_errors(
            "L01", invalid_contract, set(baselines)
        )
        self.assertTrue(any("demand" in error for error in errors))
        self.assertTrue(any("margin must remain null" in error for error in errors))
        self.assertTrue(any("total_score must remain null" in error for error in errors))
        self.assertTrue(any("manual_verification" in error for error in errors))

        fixture = (
            ROOT / "references/demo-data/eval-learned-transfer-candidates.md"
        ).read_text(encoding="utf-8")
        self.assertEqual(
            {"lr-a17": 2.0, "lr-b42": 2.0, "lr-c63": 2.0, "lr-d88": 3.0},
            eval_runner.parse_controlled_competition_baselines(fixture),
        )
        self.assertEqual(
            {
                "lr-a17": {
                    "investment_cny": 5200.0,
                    "cash_cycle_days": 30.0,
                    "status": "pass_synthetic",
                },
                "lr-b42": {
                    "investment_cny": 5600.0,
                    "cash_cycle_days": 35.0,
                    "status": "pass_synthetic",
                },
                "lr-c63": {
                    "investment_cny": 5000.0,
                    "cash_cycle_days": 30.0,
                    "status": "pass_synthetic",
                },
                "lr-d88": {
                    "investment_cny": 6500.0,
                    "cash_cycle_days": 35.0,
                    "status": "pass_synthetic",
                },
            },
            eval_runner.parse_controlled_hard_constraints(fixture),
        )

    def test_controlled_platform_route_binds_candidates_top_rank_and_unknown_margin(self) -> None:
        def candidate(candidate_id: str, rank: int) -> dict:
            return {
                "candidate_id": candidate_id,
                "rank": rank,
                "scores": {
                    "demand": 4,
                    "competition": 3,
                    "margin": None,
                    "capability_fit": 4,
                    "risk": 4,
                },
                "total_score": None,
            }

        result = {
            "recommended": [
                candidate("platform-search", 1),
                candidate("platform-visual", 2),
            ],
            "filtered": [],
            "blocked_pending_data": [],
            "manual_verification": ["完整成本与毛利需人工核实"],
            "data_access": {
                "mode": "synthetic_demo",
                "sources_used": [
                    {
                        "provider": "repository_fixture",
                        "provider_variant": "eval_platform_comparison",
                        "source_role": "direct_market_data",
                        "read_operations": [
                            "read references/demo-data/eval-platform-comparison.md"
                        ],
                    }
                ],
                "collectors_used": [],
            },
        }
        candidate_ids = {"platform-search", "platform-visual"}
        self.assertEqual(
            [],
            eval_runner.controlled_platform_result_errors(
                "P01A", result, candidate_ids, "platform-search"
            ),
        )
        wrong_top = json.loads(json.dumps(result))
        wrong_top["recommended"][0]["rank"] = 2
        wrong_top["recommended"][1]["rank"] = 1
        errors = eval_runner.controlled_platform_result_errors(
            "P01A", wrong_top, candidate_ids, "platform-search"
        )
        self.assertTrue(any("top candidate" in error for error in errors))
        malformed_rank = json.loads(json.dumps(result))
        malformed_rank["recommended"][0]["rank"] = None
        errors = eval_runner.controlled_platform_result_errors(
            "P01A", malformed_rank, candidate_ids, "platform-search"
        )
        self.assertTrue(any("ranks" in error for error in errors))
        pending = json.loads(json.dumps(result))
        pending["blocked_pending_data"] = [
            {"candidate_id": "platform-search", "missing_fields": ["真实成本"]}
        ]
        errors = eval_runner.controlled_platform_result_errors(
            "P01A", pending, candidate_ids, "platform-search"
        )
        self.assertTrue(any("blocked_pending_data" in error for error in errors))
        fake_live = json.loads(json.dumps(result))
        fake_live["data_access"]["mode"] = "live_mcp"
        fake_live["data_access"]["sources_used"] = []
        errors = eval_runner.controlled_platform_result_errors(
            "P01A", fake_live, candidate_ids, "platform-search"
        )
        self.assertTrue(any("synthetic_demo" in error for error in errors))
        self.assertTrue(any("provenance" in error for error in errors))
        extra_source = json.loads(json.dumps(result))
        extra_source["data_access"]["sources_used"].append(
            {
                "provider": "live_market",
                "provider_variant": "other",
                "source_role": "direct_market_data",
                "read_operations": ["read live source"],
            }
        )
        errors = eval_runner.controlled_platform_result_errors(
            "P01A", extra_source, candidate_ids, "platform-search"
        )
        self.assertTrue(any("provenance" in error for error in errors))
        denied_read = json.loads(json.dumps(result))
        denied_read["data_access"]["sources_used"][0]["provider"] = "live_market"
        denied_read["data_access"]["sources_used"][0]["read_operations"] = [
            "did NOT read references/demo-data/eval-platform-comparison.md"
        ]
        errors = eval_runner.controlled_platform_result_errors(
            "P01A", denied_read, candidate_ids, "platform-search"
        )
        self.assertTrue(any("provenance" in error for error in errors))

        report = (
            "# 合成假设 hypothesis-only\n\n"
            "- data_access.mode: synthetic_demo\n"
            "- controlled_source: references/demo-data/eval-platform-comparison.md\n"
            "- live_market_data_verified: false\n\n"
            "真实市场数据链路未验证。\n\n"
            "| candidate_id | rank | demand | competition | margin | capability_fit | risk | total_score |\n"
            "|---|---:|---:|---:|---:|---:|---:|---:|\n"
            "| platform-search | 1 | 4 | 3 | N/A | 4 | 4 | N/A |\n"
            "| platform-visual | 2 | 4 | 3 | N/A | 4 | 4 | N/A |\n"
        )
        self.assertEqual(
            [],
            eval_runner.controlled_platform_report_errors(
                report, result["recommended"]
            ),
        )
        n_a_with_candidate_count = report + "\n两个候选的 total_score 均为 N/A。\n"
        self.assertEqual(
            [],
            eval_runner.controlled_platform_report_errors(
                n_a_with_candidate_count, result["recommended"]
            ),
        )
        malicious_report = report + "\n实际毛利为 20%，total_score=5。\n"
        errors = eval_runner.controlled_platform_report_errors(
            malicious_report, result["recommended"]
        )
        self.assertTrue(any("numeric margin" in error for error in errors))
        for claim in (
            "实际毛利率是20%",
            "实际毛利率约20%",
            "实际测算毛利率为20%",
            "total_score：5",
            "最终总分约5",
            "完整商业总分为5",
            "预估毛利率达到20%",
        ):
            errors = eval_runner.controlled_platform_report_errors(
                report + "\n" + claim, result["recommended"]
            )
            self.assertTrue(any("numeric margin" in error for error in errors), claim)
        negated_report = report + "\n没有证据支持实际毛利率为20%。\n"
        errors = eval_runner.controlled_platform_report_errors(
            negated_report, result["recommended"]
        )
        self.assertTrue(any("numeric margin" in error for error in errors))
        post_negated_report = report + "\n所谓实际毛利率为20%并未验证。\n"
        errors = eval_runner.controlled_platform_report_errors(
            post_negated_report, result["recommended"]
        )
        self.assertTrue(any("numeric margin" in error for error in errors))
        source_denial = report + "\n未使用 references/demo-data/eval-platform-comparison.md。\n"
        errors = eval_runner.controlled_platform_report_errors(
            source_denial, result["recommended"]
        )
        self.assertTrue(any("contradicts" in error for error in errors))
        hidden_report = (
            "<!--\n"
            + report
            + "\n-->\n\n# 对外结论\n\nlive_mcp，真实链路已验证，实际毛利率是20%。\n"
        )
        errors = eval_runner.controlled_platform_report_errors(
            hidden_report, result["recommended"]
        )
        self.assertTrue(any("candidate table" in error for error in errors))
        self.assertTrue(any("disclosure" in error for error in errors))
        self.assertTrue(any("numeric margin" in error for error in errors))
        fenced_report = "```markdown\n" + report + "\n```\n"
        errors = eval_runner.controlled_platform_report_errors(
            fenced_report, result["recommended"]
        )
        self.assertTrue(any("candidate table" in error for error in errors))
        invalid_close = "```markdown\n```not-a-close\n" + report + "\n```\n"
        errors = eval_runner.controlled_platform_report_errors(
            invalid_close, result["recommended"]
        )
        self.assertTrue(any("candidate table" in error for error in errors))
        indented_report = "\n".join("    " + line for line in report.splitlines())
        errors = eval_runner.controlled_platform_report_errors(
            indented_report, result["recommended"]
        )
        self.assertTrue(any("candidate table" in error for error in errors))
        missing_separator = report.replace(
            "|---|---:|---:|---:|---:|---:|---:|---:|\n", ""
        )
        errors = eval_runner.controlled_platform_report_errors(
            missing_separator, result["recommended"]
        )
        self.assertTrue(any("separator" in error for error in errors))
        divergent_report = report.replace(
            "| platform-search | 1 | 4 | 3 | N/A | 4 | 4 | N/A |",
            "| platform-search | 1 | 4 | 3 | 2 | 4 | 4 | 4 |",
        )
        errors = eval_runner.controlled_platform_report_errors(
            divergent_report, result["recommended"]
        )
        self.assertTrue(any("exactly match" in error for error in errors))

        case = {
            "id": "P01A",
            "prompt": "PRODUCT_RESEARCH_EVAL=1 seller_id=eval-content",
            "expected": {
                "statuses": ["completed"],
                "platform_adapter": "amazon",
                "report_required": True,
                "recommended_include": ["platform-search"],
                "recommended_exclude": [],
                "filtered_include": [],
                "pending_include": [],
                "required_terms": [],
                "forbidden_terms": [],
                "rule_effects": {"exact": []},
            },
        }
        bound_result = {
            **result,
            "status": "completed",
            "seller_id": "eval-content",
            "platform_adapter": "amazon",
            "report_path": "reports/eval-content/platform.md",
            "rule_effects": [],
        }
        with tempfile.TemporaryDirectory() as temp:
            workdir = Path(temp)
            report_path = workdir / "reports/eval-content/platform.md"
            report_path.parent.mkdir(parents=True)
            report_path.write_text(report, encoding="utf-8")
            passed, errors, _ = eval_runner.grade_case(
                case, bound_result, workdir, [], []
            )
            self.assertTrue(passed, errors)
            report_path.write_text(malicious_report, encoding="utf-8")
            passed, errors, _ = eval_runner.grade_case(
                case, bound_result, workdir, [], []
            )
            self.assertFalse(passed)
            self.assertTrue(any("numeric margin" in error for error in errors))

        fixture = (
            ROOT / "references/demo-data/eval-platform-comparison.md"
        ).read_text(encoding="utf-8")
        self.assertEqual(
            {
                "platform-search": {
                    "investment_cny": 6200.0,
                    "cash_cycle_days": 35.0,
                    "status": "pass_synthetic",
                },
                "platform-visual": {
                    "investment_cny": 5800.0,
                    "cash_cycle_days": 30.0,
                    "status": "pass_synthetic",
                },
            },
            eval_runner.parse_controlled_hard_constraints(
                fixture, id_field="candidate_id"
            ),
        )


class EvalGradeBindingTests(unittest.TestCase):
    def case(self) -> dict:
        return {
            "id": "BIND",
            "prompt": "PRODUCT_RESEARCH_EVAL=1 seller_id=eval-content",
            "expected": {
                "statuses": ["completed"],
                "platform_adapter": "tiktok",
                "report_required": True,
                "recommended_include": [],
                "recommended_exclude": [],
                "filtered_include": [],
                "pending_include": [],
                "required_terms": [],
                "forbidden_terms": [],
                "rule_effects": {
                    "exact": [
                        {
                            "rule_id": "rule-one",
                            "candidate_id": "candidate-one",
                            "dimension": "competition",
                            "delta": -1,
                        }
                    ]
                },
            },
        }

    def result(self) -> dict:
        return {
            "status": "completed",
            "seller_id": "eval-content",
            "platform_adapter": "tiktok",
            "report_path": "reports/eval-content/result.md",
            "recommended": [
                {
                    "candidate_id": "candidate-one",
                    "scores": {"competition": 1},
                }
            ],
            "filtered": [],
            "blocked_pending_data": [],
            "rule_effects": [
                {
                    "rule_id": "rule-one",
                    "candidate_id": "candidate-one",
                    "dimension": "competition",
                    "delta": -1,
                    "before": 2,
                    "after": 1,
                }
            ],
        }

    def test_candidate_state_buckets_are_disjoint_and_unique(self) -> None:
        clean = {
            "recommended": [{"candidate_id": "a"}],
            "filtered": [{"candidate_id": "b"}],
            "blocked_pending_data": [{"candidate_id": "c"}],
        }
        self.assertEqual([], eval_runner.grade_candidate_partitions(clean))
        overlapping = {
            **clean,
            "blocked_pending_data": [
                {"candidate_id": "a"},
                {"candidate_id": "c"},
                {"candidate_id": "c"},
            ],
        }
        errors = eval_runner.grade_candidate_partitions(overlapping)
        self.assertTrue(any("overlap" in error for error in errors))
        self.assertTrue(any("duplicate" in error for error in errors))

    def test_result_seller_report_namespace_and_report_effect_trace_are_bound(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            workdir = Path(temp)
            report = workdir / "reports/eval-content/result.md"
            report.parent.mkdir(parents=True)
            report.write_text(
                "| rule_id | candidate_id | dimension | delta | before | after |\n"
                "|---|---|---|---:|---:|---:|\n"
                "| `rule-one` | `candidate-one` | `competition` | -1 | 2 | 1 |\n",
                encoding="utf-8",
            )
            passed, errors, _ = eval_runner.grade_case(
                self.case(), self.result(), workdir, [], []
            )
            self.assertTrue(passed, errors)

            wrong_seller = self.result()
            wrong_seller["seller_id"] = "other"
            passed, errors, _ = eval_runner.grade_case(
                self.case(), wrong_seller, workdir, [], []
            )
            self.assertFalse(passed)
            self.assertTrue(any("expected prompt seller" in error for error in errors))

            wrong_report = self.result()
            wrong_report["report_path"] = "reports/other/result.md"
            passed, errors, _ = eval_runner.grade_case(
                self.case(), wrong_report, workdir, [], []
            )
            self.assertFalse(passed)
            self.assertTrue(any("prompt_seller_id" in error for error in errors))

            report.write_text(
                "| rule_id | candidate_id | dimension | delta | before | after |\n"
                "|---|---|---|---:|---:|---:|\n"
                "| `rule-one` | `candidate-one` | `competition` | -1 | 1 | 0 |\n",
                encoding="utf-8",
            )
            passed, errors, _ = eval_runner.grade_case(
                self.case(), self.result(), workdir, [], []
            )
            self.assertFalse(passed)
            self.assertTrue(any("must exactly match" in error for error in errors))

    def test_conclusion_type_is_bound_to_json_and_visible_report(self) -> None:
        case = self.case()
        case["expected"]["conclusion_type"] = "demand_hypothesis_only"
        result = self.result()
        result["conclusion_type"] = "demand_hypothesis_only"
        with tempfile.TemporaryDirectory() as temp:
            workdir = Path(temp)
            report = workdir / "reports/eval-content/result.md"
            report.parent.mkdir(parents=True)
            effect_table = (
                "| rule_id | candidate_id | dimension | delta | before | after |\n"
                "|---|---|---|---:|---:|---:|\n"
                "| rule-one | candidate-one | competition | -1 | 2 | 1 |\n"
            )
            report.write_text(
                "- conclusion_type: demand_hypothesis_only\n\n" + effect_table,
                encoding="utf-8",
            )
            passed, errors, _ = eval_runner.grade_case(
                case, result, workdir, [], []
            )
            self.assertTrue(passed, errors)

            report.write_text(
                "<!-- - conclusion_type: demand_hypothesis_only -->\n\n"
                + effect_table,
                encoding="utf-8",
            )
            passed, errors, _ = eval_runner.grade_case(
                case, result, workdir, [], []
            )
            self.assertFalse(passed)
            self.assertTrue(any("conclusion line" in error for error in errors))


class EvalInfrastructureTests(unittest.TestCase):
    @staticmethod
    def case(case_id: str = "INFRA") -> dict:
        return {
            "id": case_id,
            "title": "infra",
            "priority": "P0",
            "suite": "core",
        }

    def test_case_infrastructure_exception_becomes_a_failure_artifact(self) -> None:
        args = Namespace(model=None, timeout=1, jobs=1)
        with tempfile.TemporaryDirectory() as temp:
            run_root = Path(temp)
            with mock.patch.object(
                eval_runner, "_run_agent_case", side_effect=RuntimeError("private path")
            ):
                result = eval_runner.run_agent_case(self.case(), args, run_root)
            self.assertFalse(result["passed"])
            self.assertEqual(
                ["infrastructure failure: RuntimeError"], result["errors"]
            )
            for name in (
                "grade.json",
                "file-changes.json",
                "command-audit.json",
                "tool-calls.json",
            ):
                self.assertTrue((run_root / "INFRA" / name).is_file())

    def test_parallel_future_exception_becomes_a_case_failure(self) -> None:
        args = Namespace(model=None, timeout=1, jobs=2)
        cases = [self.case("A"), self.case("B")]
        with tempfile.TemporaryDirectory() as temp:
            run_root = Path(temp)
            with mock.patch.object(
                eval_runner, "run_agent_case", side_effect=RuntimeError("boom")
            ):
                results = eval_runner.execute_case_batch(cases, args, run_root)
            self.assertEqual(["A", "B"], [item["case_id"] for item in results])
            self.assertTrue(all(not item["passed"] for item in results))

    def test_dirty_agent_preflight_always_writes_summary(self) -> None:
        case = self.case()
        start = "a" * 40
        with tempfile.TemporaryDirectory() as temp:
            artifacts = Path(temp) / "artifacts"
            with (
                mock.patch.object(eval_runner, "ROOT", Path(temp)),
                mock.patch.object(eval_runner, "ARTIFACTS", artifacts),
                mock.patch.object(eval_runner, "load_cases", return_value=[case]),
                mock.patch.object(eval_runner, "repository_state", return_value=(start, False)),
                mock.patch.object(eval_runner, "static_validate") as static_validate,
                mock.patch.object(eval_runner, "codex_version", return_value="codex-test"),
                mock.patch.object(
                    sys,
                    "argv",
                    ["runner", "--mode", "agent", "--case", "INFRA"],
                ),
            ):
                with self.assertRaises(SystemExit):
                    eval_runner.main()
            static_validate.assert_not_called()
            run_dirs = list(artifacts.iterdir())
            self.assertEqual(1, len(run_dirs))
            summary = json.loads(
                (run_dirs[0] / "summary.json").read_text(encoding="utf-8")
            )
            self.assertEqual(start, summary["evaluated_commit"])
            self.assertEqual(1, summary["failed"])

    def test_head_change_marks_completed_case_failed_in_summary_and_grade(self) -> None:
        case = self.case()
        start = "a" * 40
        end = "b" * 40

        def fake_execute(selected, args, run_root):
            case_dir = run_root / "INFRA"
            case_dir.mkdir()
            eval_runner._write_json(
                case_dir / "grade.json", {"passed": True, "errors": []}
            )
            return [
                {
                    "case_id": "INFRA",
                    "title": "infra",
                    "passed": True,
                    "errors": [],
                    "duration_seconds": 0.1,
                }
            ]

        with tempfile.TemporaryDirectory() as temp:
            artifacts = Path(temp) / "artifacts"
            with (
                mock.patch.object(eval_runner, "ROOT", Path(temp)),
                mock.patch.object(eval_runner, "ARTIFACTS", artifacts),
                mock.patch.object(eval_runner, "load_cases", return_value=[case]),
                mock.patch.object(
                    eval_runner,
                    "repository_state",
                    side_effect=[(start, True), (end, True)],
                ),
                mock.patch.object(eval_runner, "static_validate"),
                mock.patch.object(eval_runner, "execute_case_batch", side_effect=fake_execute),
                mock.patch.object(eval_runner, "codex_version", return_value="codex-test"),
                mock.patch.object(
                    sys,
                    "argv",
                    ["runner", "--mode", "agent", "--case", "INFRA"],
                ),
            ):
                with self.assertRaises(SystemExit):
                    eval_runner.main()
            run_dir = next(artifacts.iterdir())
            summary = json.loads(
                (run_dir / "summary.json").read_text(encoding="utf-8")
            )
            self.assertEqual(start, summary["evaluated_commit"])
            self.assertEqual(1, summary["failed"])
            grade = json.loads(
                (run_dir / "INFRA/grade.json").read_text(encoding="utf-8")
            )
            self.assertIn("head_changed_during_run", grade["errors"][0])

    def test_postflight_checks_both_cleanliness_and_head(self) -> None:
        start = "a" * 40
        self.assertEqual(
            [], eval_runner.repository_integrity_categories(start, start, True)
        )
        self.assertEqual(
            ["worktree_changed_during_run"],
            eval_runner.repository_integrity_categories(start, start, False),
        )
        self.assertEqual(
            ["head_changed_during_run"],
            eval_runner.repository_integrity_categories(start, "b" * 40, True),
        )


if __name__ == "__main__":
    unittest.main()
