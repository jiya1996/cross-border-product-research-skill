from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest import mock

from scripts import build_release
from scripts import export_product_research_evidence as evidence
from scripts import public_release_safety as safety


class EvidenceExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        (self.root / ".gitignore").write_text(
            "evals/product-research/artifacts/\n", encoding="utf-8"
        )
        subprocess.run(
            ["git", "-C", str(self.root), "add", ".gitignore"], check=True
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(self.root),
                "-c",
                "user.name=Evidence Test",
                "-c",
                "user.email=evidence@example.invalid",
                "commit",
                "-q",
                "-m",
                "fixture",
            ],
            check=True,
        )
        self.commit = subprocess.run(
            ["git", "-C", str(self.root), "rev-parse", "HEAD"],
            check=True,
            text=True,
            capture_output=True,
        ).stdout.strip()
        schema_target = (
            self.root
            / "evals"
            / "product-research"
            / "schemas"
            / "final-result.schema.json"
        )
        schema_target.parent.mkdir(parents=True)
        shutil.copy2(
            Path(__file__).resolve().parents[1]
            / "evals"
            / "product-research"
            / "schemas"
            / "final-result.schema.json",
            schema_target,
        )
        self.artifacts = self.root / "evals" / "product-research" / "artifacts"
        self.evidence_root = self.root / "evals" / "product-research" / "evidence"
        self.artifacts.mkdir(parents=True)
        self.run = self.artifacts / "run-001"
        self.run.mkdir()
        self._write_complete_run()

        self.patches = ExitStack()
        self.patches.enter_context(mock.patch.object(evidence, "ROOT", self.root))
        self.patches.enter_context(
            mock.patch.object(evidence, "ARTIFACTS_ROOT", self.artifacts)
        )
        self.patches.enter_context(
            mock.patch.object(evidence, "EVIDENCE_ROOT", self.evidence_root)
        )

    def tearDown(self) -> None:
        self.patches.close()
        self.temp.cleanup()

    @staticmethod
    def _write_json(path: Path, value: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

    def _write_complete_run(self, *, include_metadata: bool = True) -> None:
        summary = {"selected": 1, "passed": 1, "failed": 0}
        if include_metadata:
            summary.update(
                {
                    "evaluated_commit": self.commit,
                    "codex_version": "codex-cli 1.2.3",
                    "command_profile": "codex_exec_ephemeral_workspace_write_v2",
                }
            )
        self._write_json(self.run / "summary.json", summary)
        case = self.run / "E00"
        self._write_json(case / "grade.json", {"passed": True, "errors": []})
        self._write_json(
            case / "result.json",
            {
                "status": "needs_input",
                "conclusion_type": "not_applicable",
                "seller_id": None,
                "platform_adapter": "tiktok",
                "report_path": None,
                "inputs_read": {
                    "profile": None,
                    "sop": None,
                    "decisions": [],
                    "policy": None,
                    "platform_strategy": None,
                },
                "data_access": {
                    "mode": "none",
                    "sources_used": [],
                    "collectors_used": [],
                    "transformations_used": [],
                    "denied_operations": [],
                },
                "rule_effects": [],
                "recommended": [],
                "filtered": [],
                "blocked_pending_data": [],
                "manual_verification": [],
                "notes": ["seller_id is required before research"],
            },
        )
        self._write_json(
            case / "file-changes.json", {"changed": [], "unauthorized": []}
        )
        self._write_json(
            case / "tool-calls.json", {"structured_external_tool_calls": []}
        )
        self._write_json(
            case / "command-audit.json",
            {
                "command_execution": {
                    "count": 1,
                    "hashes": ["b" * 64],
                    "classifications": ["workspace_write"],
                    "violations": [],
                }
            },
        )
        # Raw traces can contain private data; the exporter must never copy or inspect them.
        (case / "events.jsonl").write_text(
            "Authorization" + ": Bearer " + "x" * 32, encoding="utf-8"
        )
        (case / "stderr.log").write_text(
            "/" + "Users/example/private", encoding="utf-8"
        )
        (case / "workspace").mkdir(exist_ok=True)
        (case / "workspace" / "raw.txt").write_text("raw", encoding="utf-8")

    def _export(self, **kwargs: object) -> Path:
        return evidence.export_run(
            self.run,
            allowed_seller_ids=list(kwargs.pop("allowed_seller_ids", [])),
            **kwargs,
        )

    def test_exports_only_allowlisted_canonical_evidence(self) -> None:
        destination = self._export()

        names = {
            path.relative_to(destination).as_posix()
            for path in destination.rglob("*")
            if path.is_file()
        }
        self.assertEqual(
            {
                "manifest.json",
                "summary.json",
                "E00/grade.json",
                "E00/result.json",
                "E00/file-changes.json",
                "E00/tool-calls.json",
                "E00/command-audit.json",
            },
            names,
        )
        manifest = json.loads((destination / "manifest.json").read_text("utf-8"))
        self.assertEqual(self.commit, manifest["evaluated_commit"])
        self.assertEqual("codex-cli 1.2.3", manifest["codex_version"])
        self.assertEqual(1, manifest["case_count"])
        self.assertEqual(
            "codex_exec_ephemeral_workspace_write_v2", manifest["command_profile"]
        )
        self.assertEqual(
            "run_metadata", manifest["metadata_sources"]["evaluated_commit"]
        )
        self.assertNotIn("events.jsonl", names)
        self.assertNotIn("stderr.log", names)
        self.assertFalse((destination / "E00" / "workspace").exists())

    def test_missing_run_metadata_requires_explicit_supplements(self) -> None:
        self._write_complete_run(include_metadata=False)
        with self.assertRaisesRegex(evidence.EvidenceExportError, "missing required"):
            self._export()

        destination = self._export(
            evaluated_commit=self.commit,
            codex_version="codex-cli test",
            command_profile="codex_exec_ephemeral_workspace_write_v2",
        )
        manifest = json.loads((destination / "manifest.json").read_text("utf-8"))
        self.assertEqual(
            "cli_supplement", manifest["metadata_sources"]["evaluated_commit"]
        )

    def test_rejects_secret_or_absolute_path_in_publishable_payload(self) -> None:
        result_path = self.run / "E00" / "result.json"
        result = json.loads(result_path.read_text("utf-8"))
        result["notes"] = ["Bearer " + "z" * 32]
        self._write_json(result_path, result)
        with self.assertRaisesRegex(evidence.EvidenceExportError, "sensitive content"):
            self._export()

        result["notes"] = ["/" + "Users/example/eval-output"]
        self._write_json(result_path, result)
        with self.assertRaisesRegex(evidence.EvidenceExportError, "sensitive content"):
            self._export()

    def test_rejects_non_allowlisted_seller_id(self) -> None:
        result_path = self.run / "E00" / "result.json"
        result = json.loads(result_path.read_text("utf-8"))
        result["seller_id"] = "real-seller"
        self._write_json(result_path, result)

        with self.assertRaisesRegex(evidence.EvidenceExportError, "non-allowlisted"):
            self._export(allowed_seller_ids=["eval-content"])

    def test_rejects_raw_command_fields_in_command_audit(self) -> None:
        audit_path = self.run / "E00" / "command-audit.json"
        audit = json.loads(audit_path.read_text("utf-8"))
        audit["command_execution"]["command"] = "harmless but raw"
        self._write_json(audit_path, audit)

        with self.assertRaisesRegex(evidence.EvidenceExportError, "raw execution field"):
            self._export()

    def test_rejects_result_that_fails_final_result_schema(self) -> None:
        result_path = self.run / "E00" / "result.json"
        result = json.loads(result_path.read_text("utf-8"))
        del result["platform_adapter"]
        self._write_json(result_path, result)
        with self.assertRaisesRegex(evidence.EvidenceExportError, "schema missing"):
            self._export()

    def test_exports_report_only_when_result_binds_same_seller_namespace(self) -> None:
        result_path = self.run / "E00" / "result.json"
        result = json.loads(result_path.read_text("utf-8"))
        result["seller_id"] = "eval-content"
        result["report_path"] = "reports/eval-content/report.md"
        self._write_json(result_path, result)
        (self.run / "E00" / "report.md").write_text(
            "# Public synthetic report\n", encoding="utf-8"
        )
        destination = self._export(allowed_seller_ids=["eval-content"])
        self.assertEqual(
            "# Public synthetic report\n",
            (destination / "E00" / "report.md").read_text("utf-8"),
        )

    def test_rejects_invalid_grade_and_summary_counts(self) -> None:
        grade_path = self.run / "E00" / "grade.json"
        self._write_json(grade_path, {"passed": "true", "errors": []})
        with self.assertRaisesRegex(evidence.EvidenceExportError, "passed must be boolean"):
            self._export()

        self._write_json(grade_path, {"passed": True, "errors": []})
        summary_path = self.run / "summary.json"
        summary = json.loads(summary_path.read_text("utf-8"))
        summary["selected"] = 2
        self._write_json(summary_path, summary)
        with self.assertRaisesRegex(evidence.EvidenceExportError, "counts disagree"):
            self._export()

    def test_grade_passed_must_equal_empty_errors(self) -> None:
        grade_path = self.run / "E00" / "grade.json"
        for grade in (
            {"passed": True, "errors": ["failure"]},
            {"passed": False, "errors": []},
        ):
            with self.subTest(grade=grade):
                self._write_json(grade_path, grade)
                with self.assertRaisesRegex(
                    evidence.EvidenceExportError, "passed/errors semantics disagree"
                ):
                    self._export()

    def test_rejects_cross_platform_path_traversal_in_file_changes(self) -> None:
        changes_path = self.run / "E00" / "file-changes.json"
        self._write_json(
            changes_path,
            {"changed": ["reports\\eval-content\\..\\secret.md"], "unauthorized": []},
        )
        with self.assertRaisesRegex(
            evidence.EvidenceExportError, "Windows separator forbidden"
        ):
            self._export(allowed_seller_ids=["eval-content"])

    def test_rejects_missing_git_commit_and_report_mismatch(self) -> None:
        summary_path = self.run / "summary.json"
        summary = json.loads(summary_path.read_text("utf-8"))
        summary["evaluated_commit"] = "f" * 40
        self._write_json(summary_path, summary)
        with self.assertRaisesRegex(evidence.EvidenceExportError, "not present in Git"):
            self._export()

        summary["evaluated_commit"] = self.commit
        self._write_json(summary_path, summary)
        result_path = self.run / "E00" / "result.json"
        result = json.loads(result_path.read_text("utf-8"))
        result["seller_id"] = "eval-content"
        result["report_path"] = "reports/eval-content/report.md"
        self._write_json(result_path, result)
        with self.assertRaisesRegex(evidence.EvidenceExportError, "report.md presence"):
            self._export(allowed_seller_ids=["eval-content"])

    def test_rejects_symlink_anywhere_in_raw_run(self) -> None:
        target = self.run / "E00" / "outside.txt"
        target.write_text("outside", encoding="utf-8")
        link = self.run / "E00" / "workspace" / "link.txt"
        try:
            os.symlink(target, link)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlink unavailable: {exc}")

        with self.assertRaisesRegex(evidence.EvidenceExportError, "symbolic link"):
            self._export()

    def test_rejects_unignored_or_non_direct_run_directory(self) -> None:
        outside = self.root / "other-run"
        outside.mkdir()
        with self.assertRaisesRegex(evidence.EvidenceExportError, "direct artifacts child"):
            evidence.export_run(outside, allowed_seller_ids=[])

        (self.root / ".gitignore").write_text("", encoding="utf-8")
        with self.assertRaisesRegex(evidence.EvidenceExportError, "not covered by Git ignore"):
            self._export()

    def test_release_contract_rejects_raw_files_under_evidence(self) -> None:
        build_release.validate_evidence_name(
            "evals/product-research/evidence/run-001/E00/grade.json"
        )
        with self.assertRaisesRegex(SystemExit, "unexpected evidence case file"):
            build_release.validate_evidence_name(
                "evals/product-research/evidence/run-001/E00/events.jsonl"
            )

    def test_release_revalidates_evidence_manifest_hashes(self) -> None:
        destination = self._export()

        def payloads() -> list[tuple[Path, bytes]]:
            return [
                (path, path.read_bytes())
                for path in destination.rglob("*")
                if path.is_file()
            ]

        with mock.patch.object(build_release, "ROOT", self.root):
            schema_payload = (
                self.root
                / "evals"
                / "product-research"
                / "schemas"
                / "final-result.schema.json"
            ).read_bytes()
            build_release.validate_sanitized_evidence_bundles(
                payloads(), result_schema_payload=schema_payload
            )
            result_path = destination / "E00" / "result.json"
            result_path.write_text('{"seller_id": null}\n', encoding="utf-8")
            with self.assertRaisesRegex(SystemExit, "hash mismatch"):
                build_release.validate_sanitized_evidence_bundles(
                    payloads(), result_schema_payload=schema_payload
                )

    def test_shared_release_scanner_detects_credentials_and_temporary_paths(self) -> None:
        slash = chr(92)
        samples = [
            ("common credential token prefix", "gh" + "p_" + "x" * 24),
            ("temporary absolute path", "/" + "tmp/private-eval"),
            ("machine-specific macOS path", "/" + "Users/example/eval"),
            ("machine-specific Linux path", "/" + "home/example/eval"),
            ("machine-specific root path", "/" + "root/private/eval"),
            ("machine-specific mounted-volume path", "/" + "Volumes/private/eval"),
            (
                "machine-specific Windows path",
                "C:" + slash + "Users" + slash + "example" + slash + "eval",
            ),
            (
                "machine-specific Windows path",
                json.dumps(
                    {
                        "path": "D:"
                        + slash
                        + "Users"
                        + slash
                        + "example"
                        + slash
                        + "eval"
                    }
                ),
            ),
            ("Windows UNC path", slash + slash + "server" + slash + "share"),
            ("credential assignment", "api_" + "key=abcdefghijklmnopqrstuvwxyz"),
            ("credential assignment", "to" + "ken=abcdefghijklmnopqrstuvwxyz"),
            ("credential assignment", "se" + "cret=abcdefghijklmnopqrstuvwxyz"),
            ("credential assignment", "pass" + "word=abcdefghijklmnopqrstuvwxyz"),
            (
                "credential assignment",
                "AWS_" + "SECRET_" + "ACCESS_KEY=abcdefghijklmnopqrstuvwxyz",
            ),
            ("Bearer " + "credential", "Bearer " + "abcdefghijklmnopqrstuvwxyz"),
            ("authenticated URL", "https://" + "user:pass@example.invalid/path"),
            (
                "credential-bearing URL",
                "https://example.invalid/?" + "to" + "ken=abcdefghijklmnopqrstuvwxyz",
            ),
            ("private key", "-----BEGIN " + "RSA PRIVATE KEY-----"),
        ]
        for expected, sample in samples:
            with self.subTest(expected=expected):
                self.assertIn(
                    expected,
                    build_release.sensitive_content_findings(sample.encode()),
                )

    def test_placeholder_matching_is_exact_not_substring(self) -> None:
        safe_value = ("api_" + "key=replace-with-local-secret").encode()
        self.assertEqual([], safety.sensitive_content_findings(safe_value))
        unsafe_value = ("api_" + "key=prefix-replace-with-local-secret-suffix").encode()
        self.assertIn(
            "credential assignment", safety.sensitive_content_findings(unsafe_value)
        )

    def test_camel_case_credentials_and_fake_os_value_are_rejected(self) -> None:
        unsafe = [
            "api" + "Key=abcdefghijklmnopqrstuvwxyz",
            "access" + "To" + "ken=abcdefghijklmnopqrstuvwxyz",
            "client" + "Sec" + "ret=abcdefghijklmnopqrstuvwxyz",
            "to" + "ken=os.production-secret-value",
        ]
        for value in unsafe:
            with self.subTest(value=value):
                self.assertIn(
                    "credential assignment",
                    safety.sensitive_content_findings(value.encode()),
                )
        safe = [
            "access" + "To" + "ken=${ACCESS_TOKEN}",
            "client" + "Sec" + "ret=$CLIENT_SECRET",
            "bearer" + "To" + "kenEnvVar=OPENAI_API_KEY",
        ]
        for value in safe:
            with self.subTest(value=value):
                self.assertEqual([], safety.sensitive_content_findings(value.encode()))

    def test_relative_path_validator_rejects_posix_windows_drive_and_unc_escape(self) -> None:
        slash = chr(92)
        unsafe = [
            "../secret",
            "reports/../secret",
            "reports" + slash + ".." + slash + "secret",
            "C:" + slash + "private" + slash + "file",
            slash + slash + "server" + slash + "share" + slash + "file",
        ]
        for value in unsafe:
            with self.subTest(value=value), self.assertRaises(safety.PublicSafetyError):
                safety.safe_posix_relative_path(value, label="test path")


if __name__ == "__main__":
    unittest.main()
