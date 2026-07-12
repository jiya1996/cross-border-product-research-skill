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
