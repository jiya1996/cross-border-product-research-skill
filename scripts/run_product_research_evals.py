#!/usr/bin/env python3
"""Validate and optionally execute black-box product-research evaluation cases."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import learned_rules


ROOT = Path(__file__).resolve().parents[1]
EVAL_ROOT = ROOT / "evals" / "product-research"
MANIFEST = EVAL_ROOT / "cases.json"
RESULT_SCHEMA = EVAL_ROOT / "schemas" / "final-result.schema.json"
RUBRIC = EVAL_ROOT / "rubric.json"
ARTIFACTS = EVAL_ROOT / "artifacts"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run product-research static or black-box evals.")
    parser.add_argument("--mode", choices=["static", "agent"], default="static")
    parser.add_argument("--case", action="append", default=[], help="Case ID; repeatable.")
    parser.add_argument(
        "--suite",
        choices=["core", "platform", "security", "all"],
        help="Run all cases in a suite. Agent mode requires --case or --suite.",
    )
    parser.add_argument("--list", action="store_true", help="List cases and exit.")
    parser.add_argument("--model", help="Optional Codex model override.")
    parser.add_argument("--timeout", type=int, default=360, help="Seconds per agent case.")
    parser.add_argument(
        "--keep-workdir",
        action="store_true",
        help="Copy the isolated post-run workspace into artifacts for inspection.",
    )
    return parser.parse_args()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_cases() -> list[dict]:
    return load_json(MANIFEST)["cases"]


def list_cases(cases: list[dict]) -> None:
    for case in cases:
        print(f"{case['id']:5} {case['priority']:2} {case['suite']:8} {case['title']}")


def static_validate(cases: list[dict]) -> None:
    required = [
        MANIFEST,
        RESULT_SCHEMA,
        RUBRIC,
        ROOT / "skills" / "product-research" / "SKILL.md",
        ROOT / "references" / "schemas" / "candidate-batch.schema.json",
        ROOT / "references" / "data-sources" / "adapter-contract.md",
        ROOT / "references" / "data-sources" / "ecosystem-tool-role-map.md",
        ROOT / "references" / "data-sources" / "tool-role-registry.json",
        ROOT / "references" / "data-sources" / "lingxing-readonly-plan.md",
        ROOT / "references" / "data-sources" / "hubu-collector-boundary.md",
        ROOT / "references" / "data-sources" / "1688-supply-validation.md",
        ROOT / "references" / "demo-data" / "eval-tool-role-boundaries.json",
        ROOT / "scripts" / "check_data_access.py",
        ROOT / "scripts" / "reset_demo.py",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    if missing:
        raise SystemExit("Static eval missing files: " + ", ".join(missing))

    ids = [case["id"] for case in cases]
    if len(ids) != len(set(ids)):
        raise SystemExit("Duplicate eval case IDs")
    required_ids = {
        "E00", "E01", "E02", "T01", "C01", "D01", "D02", "L01", "L02",
        "S01", "P01A", "P01B", "X01", "I01", "W01", "P04", "P05", "J01",
        "DS01", "DS02", "DS03", "DS04", "DS05", "DS06", "DS07", "W02",
    }
    absent = sorted(required_ids - set(ids))
    if absent:
        raise SystemExit("Missing required eval cases: " + ", ".join(absent))

    for case in cases:
        expected = case.get("expected", {})
        for key in [
            "statuses", "platform_adapter", "report_required", "recommended_include",
            "recommended_exclude", "filtered_include", "pending_include",
            "required_terms", "forbidden_terms",
        ]:
            if key not in expected:
                raise SystemExit(f"Case {case['id']} missing expected.{key}")
        if "forbidden_tool_calls" in expected and not isinstance(expected["forbidden_tool_calls"], list):
            raise SystemExit(f"Case {case['id']} expected.forbidden_tool_calls must be a list")
        data_access = expected.get("data_access")
        if data_access is not None:
            if not isinstance(data_access, dict):
                raise SystemExit(f"Case {case['id']} expected.data_access must be an object")
            for key in [
                "providers_include", "providers_exclude", "source_roles_include",
                "collectors_include", "transformations_include", "denied_operations_include",
            ]:
                if key in data_access and not isinstance(data_access[key], list):
                    raise SystemExit(f"Case {case['id']} expected.data_access.{key} must be a list")
        for seller in case.get("setup", {}).get("sellers", []):
            fixture = ROOT / seller["fixture"]
            if not fixture.is_dir():
                raise SystemExit(f"Case {case['id']} missing fixture {seller['fixture']}")
            for name in seller.get("include", []):
                if not (fixture / name).exists():
                    raise SystemExit(f"Case {case['id']} fixture missing {name}")

    skill = (ROOT / "skills" / "product-research" / "SKILL.md").read_text(encoding="utf-8")
    for needle in [
        "完整读取",
        "blocked_pending_data",
        "status: proposed",
        "只有 `active`",
        "为什么适合你",
        "为什么不适合你",
        "忠实执行段",
        "压力测试段",
        "PRODUCT_RESEARCH_EVAL=1",
        "1688 数据只证明",
        "工具角色门禁",
        "forbidden_write",
    ]:
        if needle not in skill:
            raise SystemExit(f"product-research Skill missing contract phrase: {needle}")

    schema = load_json(RESULT_SCHEMA)
    rubric = load_json(RUBRIC)
    if schema.get("type") != "object" or schema.get("additionalProperties") is not False:
        raise SystemExit("Final result schema must be a closed object")
    if sum(item["points"] for item in rubric["dimensions"]) != 100:
        raise SystemExit("Rubric dimensions must sum to 100")

    registry = load_json(ROOT / "references" / "data-sources" / "tool-role-registry.json")
    provider_ids = {item["provider_id"] for item in registry.get("providers", [])}
    for provider_id in [
        "sellersprite", "ziniao", "sif", "amz123", "lingxing", "zhiwubuyan",
        "amazon_ads", "google_translate", "hubu_rpa", "linkfox",
    ]:
        if provider_id not in provider_ids:
            raise SystemExit(f"Tool-role registry missing provider: {provider_id}")

    boundary_fixture = load_json(ROOT / "references" / "demo-data" / "eval-tool-role-boundaries.json")
    if boundary_fixture.get("schema_version") != "1.1":
        raise SystemExit("Tool-role boundary fixture must use candidate-batch schema 1.1")
    for source in boundary_fixture.get("sources", []):
        for key in ["source_role", "allowed_dimensions", "read_only", "measurement_kind"]:
            if key not in source:
                raise SystemExit(f"Tool-role boundary source {source.get('source_id')} missing {key}")
    sources = {item.get("source_id"): item for item in boundary_fixture.get("sources", [])}
    hubu_source = sources.get("hubu-collector", {})
    if hubu_source.get("provider") != "amazon_ads":
        raise SystemExit("Hubu collector fixture must preserve amazon_ads provider")
    if hubu_source.get("source_role") != "seller_first_party_data":
        raise SystemExit("Hubu collector fixture must preserve seller_first_party_data role")
    if hubu_source.get("collector") != "hubu_rpa":
        raise SystemExit("Hubu collector fixture must record hubu_rpa as collector")

    print(f"OK: static product-research eval contract ({len(cases)} cases, 100-point rubric)")


def select_cases(cases: list[dict], requested: list[str], suite: Optional[str]) -> list[dict]:
    by_id = {case["id"]: case for case in cases}
    if requested:
        unknown = [case_id for case_id in requested if case_id not in by_id]
        if unknown:
            raise SystemExit("Unknown case IDs: " + ", ".join(unknown))
        return [by_id[case_id] for case_id in requested]
    if suite:
        return cases if suite == "all" else [case for case in cases if case["suite"] == suite]
    raise SystemExit("Agent mode requires --case ID or --suite NAME")


def copy_project(destination: Path) -> None:
    def ignore(path: str, names: list[str]) -> set[str]:
        ignored = {name for name in names if name in {".git", "__pycache__", ".DS_Store"}}
        if Path(path).name == "product-research" and "artifacts" in names:
            ignored.add("artifacts")
        return ignored

    shutil.copytree(ROOT, destination, symlinks=True, ignore=ignore)


def setup_sellers(workdir: Path, case: dict) -> list[str]:
    seller_ids = []
    for spec in case.get("setup", {}).get("sellers", []):
        seller_id = spec["seller_id"]
        seller_ids.append(seller_id)
        fixture = ROOT / spec["fixture"]
        target = workdir / "sellers" / seller_id
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True)
        for name in spec.get("include", []):
            source = fixture / name
            destination = target / name
            if source.is_dir():
                shutil.copytree(source, destination)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
        profile = target / "profile.yaml"
        if profile.is_file():
            text = profile.read_text(encoding="utf-8")
            text = text.replace('seller_id: "eval-content"', f'seller_id: "{seller_id}"')
            text = text.replace('seller_id: "eval-conservative"', f'seller_id: "{seller_id}"')
            profile.write_text(text, encoding="utf-8")
            if "confirmed" in spec:
                rules = learned_rules.load_rules(profile)
                rule_id = spec.get("rule_id", learned_rules.DEMO_RULE_ID)
                try:
                    rule = learned_rules.find_rule(rules, rule_id)
                except KeyError as exc:
                    raise SystemExit(
                        f"Case {case['id']} fixture has no learned rule_id {rule_id}"
                    ) from exc
                if spec["confirmed"] is True:
                    rule["status"] = "active"
                    rule["confirmed_by"] = "eval-fixture"
                    rule["confirmed_at"] = "2026-07-11T00:00:00+00:00"
                elif spec["confirmed"] is False:
                    rule["status"] = "proposed"
                    rule["confirmed_by"] = None
                    rule["confirmed_at"] = None
                    rule["revoked_by"] = None
                    rule["revoked_at"] = None
                    rule["revoke_reason"] = None
                else:
                    raise SystemExit(f"Case {case['id']} confirmed must be true or false")
                learned_rules.save_rules(profile, rules)
    return seller_ids


def hash_tree(root: Path) -> dict[str, str]:
    result = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or ".git" in path.parts:
            continue
        rel = str(path.relative_to(root))
        result[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def changed_paths(before: dict[str, str], after: dict[str, str]) -> list[str]:
    return sorted(path for path in set(before) | set(after) if before.get(path) != after.get(path))


def allowed_change(path: str, seller_ids: list[str]) -> bool:
    return any(path.startswith(f"reports/{seller_id}/") for seller_id in seller_ids)


def parse_result(path: Path) -> dict:
    text = path.read_text(encoding="utf-8").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(text)


def collect_ids(items: list[dict]) -> set[str]:
    return {str(item.get("candidate_id")) for item in items}


def collect_invoked_tool_names(events_path: Path) -> list[str]:
    """Extract structured external tool calls without scanning command output or prose."""
    names = []
    if not events_path.is_file():
        return names
    for raw in events_path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            continue
        item = event.get("item")
        if not isinstance(item, dict):
            continue
        item_type = str(item.get("type", ""))
        if item_type not in {"mcp_tool_call", "tool_call", "function_call", "dynamic_tool_call"}:
            continue
        name = item.get("tool_name") or item.get("tool") or item.get("name")
        if isinstance(name, dict):
            name = name.get("name")
        if not isinstance(name, str) or not name:
            continue
        server = item.get("server")
        names.append(f"{server}:{name}" if isinstance(server, str) and server else name)
    return sorted(set(names))


def grade_case(
    case: dict,
    result: dict,
    workdir: Path,
    unauthorized_changes: list[str],
    invoked_tools: list[str],
) -> tuple[bool, list[str], Optional[Path]]:
    errors = []
    expected = case["expected"]
    if result.get("status") not in expected["statuses"]:
        errors.append(f"status={result.get('status')} expected one of {expected['statuses']}")
    if result.get("platform_adapter") != expected["platform_adapter"]:
        errors.append(
            f"platform_adapter={result.get('platform_adapter')} expected {expected['platform_adapter']}"
        )

    report = None
    report_path = result.get("report_path")
    if report_path:
        candidate = (workdir / report_path).resolve()
        try:
            candidate.relative_to(workdir.resolve())
            report = candidate
        except ValueError:
            errors.append("report_path escapes the isolated workspace")
    if expected["report_required"]:
        if report is None or not report.is_file():
            errors.append("required report was not created")
    elif report_path is not None:
        errors.append("report must be null for this case")

    recommended = collect_ids(result.get("recommended", []))
    filtered = collect_ids(result.get("filtered", []))
    pending = collect_ids(result.get("blocked_pending_data", []))
    for candidate_id in expected["recommended_include"]:
        if candidate_id not in recommended:
            errors.append(f"recommended missing {candidate_id}")
    for candidate_id in expected["recommended_exclude"]:
        if candidate_id in recommended:
            errors.append(f"forbidden recommendation present {candidate_id}")
    for candidate_id in expected["filtered_include"]:
        if candidate_id not in filtered:
            errors.append(f"filtered missing {candidate_id}")
    for candidate_id in expected["pending_include"]:
        if candidate_id not in pending:
            errors.append(f"blocked_pending_data missing {candidate_id}")

    report_text = report.read_text(encoding="utf-8") if report and report.is_file() else ""
    combined = json.dumps(result, ensure_ascii=False) + "\n" + report_text
    for term in expected["required_terms"]:
        if term not in combined:
            errors.append(f"required term missing: {term}")
    for term in expected["forbidden_terms"]:
        if term in combined:
            errors.append(f"forbidden term present: {term}")
    invoked_lower = [name.lower() for name in invoked_tools]
    for forbidden in expected.get("forbidden_tool_calls", []):
        if any(forbidden.lower() in name for name in invoked_lower):
            errors.append(f"forbidden external tool invoked: {forbidden}")

    expected_access = expected.get("data_access")
    if expected_access is not None:
        actual_access = result.get("data_access")
        if not isinstance(actual_access, dict):
            errors.append("required data_access object missing")
        else:
            sources = actual_access.get("sources_used", [])
            providers = {item.get("provider") for item in sources if isinstance(item, dict)}
            roles = {item.get("source_role") for item in sources if isinstance(item, dict)}
            collectors = set(actual_access.get("collectors_used", []))
            transformations = set(actual_access.get("transformations_used", []))
            denied = set(actual_access.get("denied_operations", []))
            for provider in expected_access.get("providers_include", []):
                if provider not in providers:
                    errors.append(f"data_access provider missing: {provider}")
            for provider in expected_access.get("providers_exclude", []):
                if provider in providers:
                    errors.append(f"data_access forbidden provider present: {provider}")
            for role in expected_access.get("source_roles_include", []):
                if role not in roles:
                    errors.append(f"data_access source role missing: {role}")
            for collector in expected_access.get("collectors_include", []):
                if collector not in collectors:
                    errors.append(f"data_access collector missing: {collector}")
            for transformation in expected_access.get("transformations_include", []):
                if transformation not in transformations:
                    errors.append(f"data_access transformation missing: {transformation}")
            for operation in expected_access.get("denied_operations_include", []):
                if operation not in denied:
                    errors.append(f"data_access denied operation missing: {operation}")
    if unauthorized_changes:
        errors.append("unauthorized file changes: " + ", ".join(unauthorized_changes))
    return not errors, errors, report


def run_agent_case(case: dict, args: argparse.Namespace, run_root: Path) -> bool:
    case_artifacts = run_root / case["id"]
    case_artifacts.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"product-research-{case['id']}-") as temp:
        workdir = Path(temp) / "workspace"
        copy_project(workdir)
        seller_ids = setup_sellers(workdir, case)
        before = hash_tree(workdir)

        result_path = case_artifacts / "result.json"
        events_path = case_artifacts / "events.jsonl"
        stderr_path = case_artifacts / "stderr.log"
        command = [
            "codex",
            "exec",
            "--ephemeral",
            "--ignore-user-config",
            "--skip-git-repo-check",
            "-c",
            'approval_policy="never"',
            "-s",
            "workspace-write",
            "-C",
            str(workdir),
            "--output-schema",
            str(RESULT_SCHEMA),
            "-o",
            str(result_path),
            "--json",
            "--color",
            "never",
        ]
        if args.model:
            command.extend(["--model", args.model])
        command.append("-")
        prompt = (
            case["prompt"]
            + "\n评测环境是隔离副本。严格遵守 AGENTS.md 与 product-research Skill。"
            + "\n最终响应只返回评测 schema 要求的 JSON；报告仍按项目契约写盘。"
        )
        env = os.environ.copy()
        for name in [
            "SELLERSPRITE_MCP_URL",
            "SELLERSPRITE_MCP_API_KEY",
            "SIF_MCP_URL",
            "SIF_MCP_API_KEY",
            "SORFTIME_MCP_URL",
            "SORFTIME_MCP_API_KEY",
        ]:
            env.pop(name, None)
        try:
            completed = subprocess.run(
                command,
                input=prompt,
                text=True,
                capture_output=True,
                timeout=args.timeout,
                env=env,
            )
        except subprocess.TimeoutExpired as exc:
            events_path.write_text(exc.stdout or "", encoding="utf-8")
            stderr_path.write_text(exc.stderr or "timeout", encoding="utf-8")
            print(f"FAIL {case['id']}: timed out after {args.timeout}s")
            return False

        events_path.write_text(completed.stdout, encoding="utf-8")
        stderr_path.write_text(completed.stderr, encoding="utf-8")
        after = hash_tree(workdir)
        changes = changed_paths(before, after)
        unauthorized = [path for path in changes if not allowed_change(path, seller_ids)]
        invoked_tools = collect_invoked_tool_names(events_path)

        errors = []
        report = None
        if completed.returncode != 0:
            errors.append(f"codex exit code {completed.returncode}")
        if not result_path.is_file():
            errors.append("missing final result JSON")
        result = None
        if not errors:
            try:
                result = parse_result(result_path)
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"invalid final result JSON: {exc}")
        if result is not None:
            passed, grade_errors, report = grade_case(
                case, result, workdir, unauthorized, invoked_tools
            )
            errors.extend(grade_errors)
        else:
            passed = False

        if report and report.is_file():
            shutil.copy2(report, case_artifacts / "report.md")
        (case_artifacts / "file-changes.json").write_text(
            json.dumps({"changed": changes, "unauthorized": unauthorized}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (case_artifacts / "tool-calls.json").write_text(
            json.dumps({"structured_external_tool_calls": invoked_tools}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (case_artifacts / "grade.json").write_text(
            json.dumps({"passed": not errors, "errors": errors}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        if args.keep_workdir:
            shutil.copytree(workdir, case_artifacts / "workspace", symlinks=True)

        if errors:
            print(f"FAIL {case['id']}: " + " | ".join(errors))
            return False
        print(f"PASS {case['id']}: {case['title']}")
        return passed


def main() -> None:
    args = parse_args()
    cases = load_cases()
    if args.list:
        list_cases(cases)
        return
    static_validate(cases)
    if args.mode == "static":
        return

    selected = select_cases(cases, args.case, args.suite)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_root = ARTIFACTS / stamp
    run_root.mkdir(parents=True, exist_ok=True)
    passed = sum(run_agent_case(case, args, run_root) for case in selected)
    summary = {
        "selected": len(selected),
        "passed": passed,
        "failed": len(selected) - passed,
        "artifact_dir": str(run_root.relative_to(ROOT)),
    }
    (run_root / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False))
    if passed != len(selected):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
