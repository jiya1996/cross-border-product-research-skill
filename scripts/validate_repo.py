#!/usr/bin/env python3
"""Validate the offline delivery structure and evaluation contract."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import learned_rules

ROOT = Path(__file__).resolve().parents[1]


REQUIRED_FILES = [
    "AGENTS.md",
    "CLAUDE_REVIEW.md",
    "DELIVERY_STATUS.md",
    "README.md",
    ".gitignore",
    "references/schemas/profile-template.yaml",
    "references/schemas/sop-template.md",
    "references/checklists/scoring-rubric.md",
    "references/data-sources/adapter-contract.md",
    "references/data-sources/ecosystem-tool-role-map.md",
    "references/data-sources/tool-role-registry.json",
    "references/data-sources/lingxing-readonly-plan.md",
    "references/data-sources/hubu-collector-boundary.md",
    "references/data-sources/1688-supply-validation.md",
    "references/schemas/candidate-batch.schema.json",
    "references/upstream/handsomewang-ai-skills-review.md",
    "references/demo-data/tiktok-candidates.md",
    "references/demo-data/demo-assumptions.md",
    "references/demo-data/example-profile-baseline.yaml",
    "references/demo-data/eval-tool-role-boundaries.json",
    "references/demo-data/eval-learned-transfer-candidates.md",
    "references/freight.md",
    "references/platform-fees.md",
    "references/demo-script.md",
    "references/demo-opening-positioning.md",
    "references/human-validation-plan.md",
    "references/private-deployment.md",
    "references/questions/recent-selection-retrospective.md",
    "config/hubu-rpa-allowlist.example.yaml",
    "config/public-release-files.txt",
    "sellers/_example/profile.yaml",
    "sellers/_example/sop.md",
    "reports/_example/2026-07-06_tiktok-pet-products.md",
    "reports/_example/2026-07-06_tiktok-desk-accessories.md",
    "evals/product-research/fixtures/reports/eval-content/2026-07-06_tiktok-cleaning-accessories.md",
    "evals/product-research/fixtures/reports/eval-content/2026-07-06_tiktok-desk-accessories.md",
    "scripts/run_demo.py",
    "scripts/learned_rules.py",
    "scripts/propose_learned.py",
    "scripts/confirm_learned.py",
    "scripts/revoke_learned.py",
    "scripts/check_data_access.py",
    "scripts/reset_demo.py",
    "scripts/run_product_research_evals.py",
    "scripts/run_video_demo.py",
    "scripts/verify_delivery.py",
    "scripts/install_project_skills.py",
    "scripts/build_release.py",
    "scripts/export_product_research_evidence.py",
    "scripts/public_release_safety.py",
    "evals/product-research/cases.json",
    "evals/product-research/rubric.json",
    "evals/product-research/schemas/final-result.schema.json",
    "evals/product-research/README.md",
    "evals/intake-retrospective/cases.json",
    "evals/intake-retrospective/README.md",
    "tests/test_product_research_demo.py",
    "tests/test_learned_rules.py",
    "tests/test_learned_cli.py",
    "tests/test_eval_setup.py",
    "tests/test_video_demo.py",
    "tests/test_reset_demo.py",
    "tests/test_build_release.py",
    "tests/test_eval_runner_security.py",
    "tests/test_evidence_export.py",
    "THIRD_PARTY_NOTICES.md",
]


REQUIRED_SKILL_REFERENCES = {
    "skills/intake-interview/SKILL.md": [
        "references/schemas/profile-template.yaml",
        "references/schemas/sop-template.md",
        "references/questions/recent-selection-retrospective.md",
        "historical_retrospective",
    ],
    "skills/product-research/SKILL.md": [
        "references/checklists/scoring-rubric.md",
        "references/freight.md",
        "references/platform-fees.md",
        "references/data-sources/adapter-contract.md",
        "references/data-sources/ecosystem-tool-role-map.md",
        "references/data-sources/tool-role-registry.json",
        "references/data-sources/lingxing-readonly-plan.md",
        "references/data-sources/hubu-collector-boundary.md",
        "references/schemas/candidate-batch.schema.json",
        "references/data-sources/1688-supply-validation.md",
        "PRODUCT_RESEARCH_EVAL=1",
        "rule_effects",
    ],
    "skills/recommendation-review/SKILL.md": [
        "YYYY-MM-DD_product-slug.md",
        "historical_retrospective",
        "后来结果状态",
        "recalled",
    ],
    "skills/profile-update/SKILL.md": ["status: proposed", "status: active", "rule_id"],
}


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def count_demo_candidates() -> int:
    path = ROOT / "references/demo-data/tiktok-candidates.md"
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("| tt-"))


def shared_rejection_count(tag: str) -> int:
    count = 0
    for path in (ROOT / "sellers/_example/decisions").glob("*.md"):
        text = path.read_text(encoding="utf-8")
        if "用户决定: rejected" in text and tag in text:
            count += 1
    return count


def example_learned_rules() -> list[dict]:
    return learned_rules.load_rules(ROOT / "sellers/_example/profile.yaml")


def validate_learned_evidence() -> None:
    decision_root = ROOT / "sellers/_example"
    for learned in example_learned_rules():
        if not learned["evidence"]:
            fail(f"learned rule has no evidence: {learned['rule_id']}")
        sessions = set()
        for evidence in learned["evidence"]:
            rel = evidence["decision_path"]
            path = decision_root / rel
            if not path.is_file():
                fail(f"learned evidence missing: sellers/_example/{rel}")
            decision = learned_rules.parse_decision(path)
            if not set(learned["condition_tag_ids"]).issubset(
                decision["explicit_tag_ids"]
            ):
                fail(f"learned evidence tags do not match rule: sellers/_example/{rel}")
            sessions.add(learned_rules.independent_session_key(decision))
        if len(learned["evidence"]) < 3 or len(sessions) < 2:
            fail(f"learned rule lacks 3 evidence / 2 sessions: {learned['rule_id']}")


def main() -> None:
    for rel in REQUIRED_FILES:
        if not (ROOT / rel).is_file():
            fail(f"missing {rel}")

    for duplicate in [
        "intake-interview.md",
        "product-research.md",
        "recommendation-review.md",
        "profile-update.md",
    ]:
        if (ROOT / duplicate).exists():
            fail(f"root duplicate should be removed: {duplicate}")

    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for needle in [
        "sellers/*",
        "!sellers/_example/**",
        "reports/*",
        "!reports/_example/**",
        "__pycache__/",
        "*.py[cod]",
        ".codex/",
    ]:
        if needle not in gitignore:
            fail(f".gitignore missing {needle}")

    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    for needle in [
        "references/schemas/profile-template.yaml",
        "references/checklists/scoring-rubric.md",
        "真实 `sellers/` 和 `reports/` 数据不得提交",
    ]:
        if needle not in agents:
            fail(f"AGENTS.md missing {needle}")

    for rel, needles in REQUIRED_SKILL_REFERENCES.items():
        text = (ROOT / rel).read_text(encoding="utf-8")
        for needle in needles:
            if needle not in text:
                fail(f"{rel} missing {needle}")

    if count_demo_candidates() < 15:
        fail("demo data should contain at least 15 candidates")
    if shared_rejection_count("同款过多") < 3:
        fail("demo decisions should contain >=3 repeated rejection evidence")
    validate_learned_evidence()

    guardrail_fixture = (
        ROOT / "references/demo-data/eval-guardrail-candidates.md"
    ).read_text(encoding="utf-8")
    safe_visual_rows = [
        line for line in guardrail_fixture.splitlines() if line.startswith("| safe-visual |")
    ]
    if len(safe_visual_rows) != 1 or "塑料齿梳结构，常规普货低风险" not in safe_visual_rows[0]:
        fail("guardrail fixture safe-visual must remain an unambiguous positive control")

    transfer_fixture = (
        ROOT / "references/demo-data/eval-learned-transfer-candidates.md"
    ).read_text(encoding="utf-8")
    for needle in [
        "pre_rule_competition_score",
        "controlled_initial_investment_cny",
        "controlled_cash_cycle_days",
        "hard_constraint_status",
        "effect-only 合成实验",
        "| lr-d88 |",
    ]:
        if needle not in transfer_fixture:
            fail(f"learned transfer fixture missing {needle}")

    run_demo = (ROOT / "scripts/run_demo.py").read_text(encoding="utf-8")
    for needle in [
        "--seller-id",
        "--label",
        "read_required_context",
        "forbidden_categories",
        "missing_dimensions",
        "为什么适合你",
        "为什么不适合你",
        "CN -> US 带电专线",
        "排序键",
    ]:
        if needle not in run_demo:
            fail(f"scripts/run_demo.py missing {needle}")

    data_access = (ROOT / "scripts/check_data_access.py").read_text(encoding="utf-8")
    for needle in [
        "credential_config_ready",
        "live_tool_smoke_tested",
        "synthetic_demo_ready",
        '"sif"',
        '"lingxing"',
        "LINGXING_MCP_KEY",
    ]:
        if needle not in data_access:
            fail(f"scripts/check_data_access.py missing {needle}")

    hubu_allowlist = (ROOT / "config/hubu-rpa-allowlist.example.yaml").read_text(encoding="utf-8")
    for needle in [
        "mode: deny_by_default",
        "enabled: false",
        "rpa_id: null",
        "allow_agent_supplied_rpa_id: false",
        "collector_role: collection_only",
        "output_source_role: seller_first_party_data",
        "write_operations: []",
    ]:
        if needle not in hubu_allowlist:
            fail(f"Hubu allowlist missing safe default: {needle}")

    cases = json.loads((ROOT / "evals/product-research/cases.json").read_text(encoding="utf-8"))["cases"]
    if len(cases) < 26:
        fail("product-research eval suite should contain at least 26 cases")
    if len({case["id"] for case in cases}) != len(cases):
        fail("product-research eval case IDs must be unique")
    for case_id in ["DS01", "DS02", "DS03", "DS04", "DS05", "DS06", "DS07", "W02"]:
        if case_id not in {case["id"] for case in cases}:
            fail(f"product-research eval suite missing {case_id}")
    cases_by_id = {case["id"]: case for case in cases}
    nonempty_effect_cases = []
    for case in cases:
        expected_effects = case.get("expected", {}).get("rule_effects")
        if not isinstance(expected_effects, dict) or not isinstance(
            expected_effects.get("exact"), list
        ):
            fail(f"eval case {case['id']} missing expected.rule_effects.exact")
        if expected_effects["exact"]:
            nonempty_effect_cases.append(case["id"])
        for seller in case.get("setup", {}).get("sellers", []):
            if "confirmed" in seller:
                fail(f"eval case {case['id']} still uses legacy confirmed boolean")
    if nonempty_effect_cases != ["L02"]:
        fail("only L02 may define non-empty expected rule effects")

    l01_seller = cases_by_id["L01"]["setup"]["sellers"][0]
    l02_seller = cases_by_id["L02"]["setup"]["sellers"][0]
    if l01_seller.get("status") != "proposed" or l02_seller.get("status") != "active":
        fail("L01/L02 must use proposed/active status setup")
    if l01_seller.get("rule_id") != learned_rules.DEMO_RULE_ID:
        fail("L01 must address the fixed learned rule_id")
    if l02_seller.get("rule_id") != learned_rules.DEMO_RULE_ID:
        fail("L02 must address the fixed learned rule_id")
    l02_effects = cases_by_id["L02"]["expected"]["rule_effects"]["exact"]
    if {item.get("candidate_id") for item in l02_effects} != {
        "lr-a17",
        "lr-b42",
        "lr-c63",
    }:
        fail("L02 must target the three neutral transfer candidates exactly")
    for item in l02_effects:
        if set(item) != {"rule_id", "candidate_id", "dimension", "delta"}:
            fail("L02 expected effects must not hard-code before/after scores")
        if item["rule_id"] != learned_rules.DEMO_RULE_ID:
            fail("L02 effect rule_id mismatch")
        if item["dimension"] != "competition" or item["delta"] != -1:
            fail("L02 effect must be competition -1")
    if "eval-learned-transfer-candidates.md" not in cases_by_id["L02"]["prompt"]:
        fail("L02 must use the neutral learned-transfer fixture")

    oracle_fixture_paths = [
        "references/demo-data/tiktok-candidates.md",
        "references/demo-data/eval-learned-transfer-candidates.md",
        "references/demo-data/eval-pressure-test.md",
        "references/demo-data/eval-guardrail-candidates.md",
        "references/demo-data/eval-platform-comparison.md",
        "references/demo-data/eval-community-supply.md",
    ]
    for rel in oracle_fixture_paths:
        text = (ROOT / rel).read_text(encoding="utf-8")
        for marker in ["intended_demo_role", "评测期望", "\n期望：", "演示使用方式"]:
            if marker in text:
                fail(f"eval input fixture leaks oracle marker {marker}: {rel}")

    candidate_schema = json.loads(
        (ROOT / "references/schemas/candidate-batch.schema.json").read_text(encoding="utf-8")
    )
    if candidate_schema["properties"]["schema_version"].get("const") != "1.1":
        fail("candidate-batch schema should be version 1.1")
    source_schema = candidate_schema["properties"]["sources"]["items"]
    for field in ["source_role", "allowed_dimensions", "read_only", "measurement_kind"]:
        if field not in source_schema["required"]:
            fail(f"candidate-batch source schema missing required {field}")
    if "xlsx" not in source_schema["properties"]["source_type"]["enum"]:
        fail("candidate-batch source_type should support xlsx")

    registry = json.loads(
        (ROOT / "references/data-sources/tool-role-registry.json").read_text(encoding="utf-8")
    )
    expected_providers = {
        "sellersprite", "ziniao", "sif", "amz123", "lingxing", "zhiwubuyan",
        "amazon_ads", "google_translate", "hubu_rpa", "linkfox",
    }
    providers = {item.get("provider_id"): item for item in registry.get("providers", [])}
    if expected_providers - set(providers):
        fail("tool-role registry missing providers: " + ", ".join(sorted(expected_providers - set(providers))))
    for provider_id in ["sellersprite", "ziniao", "lingxing", "amazon_ads", "hubu_rpa", "linkfox"]:
        capabilities = providers[provider_id].get("capabilities", [])
        if not any(item.get("source_role") == "forbidden_write" for item in capabilities):
            fail(f"tool-role registry missing forbidden_write capability for {provider_id}")

    boundary_fixture = json.loads(
        (ROOT / "references/demo-data/eval-tool-role-boundaries.json").read_text(encoding="utf-8")
    )
    if boundary_fixture.get("schema_version") != "1.1":
        fail("tool-role boundary fixture should use schema 1.1")
    if len(boundary_fixture.get("candidates", [])) < 5:
        fail("tool-role boundary fixture should contain at least 5 candidates")
    sources = {item.get("source_id"): item for item in boundary_fixture.get("sources", [])}
    hubu_source = sources.get("hubu-collector", {})
    if hubu_source.get("provider") != "amazon_ads":
        fail("Hubu-transported report must preserve amazon_ads provider")
    if hubu_source.get("source_role") != "seller_first_party_data":
        fail("Hubu-transported report must preserve seller_first_party_data role")
    if hubu_source.get("collector") != "hubu_rpa":
        fail("Hubu-transported report must record hubu_rpa as collector")
    candidates = {item.get("candidate_id"): item for item in boundary_fixture.get("candidates", [])}
    for candidate_id in ["lingxing-history-only", "hubu-transported-ads"]:
        if candidate_id not in candidates:
            fail(f"tool-role boundary fixture missing candidate {candidate_id}")

    retrospective_cases = json.loads(
        (ROOT / "evals/intake-retrospective/cases.json").read_text(encoding="utf-8")
    ).get("cases", [])
    retrospective_ids = {case.get("id") for case in retrospective_cases}
    if retrospective_ids != {"IR01", "IR02", "IR03", "IR04"}:
        fail("intake retrospective eval suite must contain IR01-IR04")
    ir03 = next(case for case in retrospective_cases if case.get("id") == "IR03")
    ir03_decisions = ir03.get("input", {}).get("decisions", [])
    if len(ir03_decisions) != 3:
        fail("IR03 must contain exactly three rejection records")
    ir03_dates = {item.get("decided_at") for item in ir03_decisions}
    if None in ir03_dates or len(ir03_dates) < 2:
        fail("IR03 must span at least two historical event dates/sessions")
    required_tags = {"same_product_density_high", "differentiation_space_low"}
    for item in ir03_decisions:
        if item.get("record_type") != "historical_retrospective":
            fail("IR03 decisions must use historical_retrospective")
        if item.get("platform") != "TikTok" or item.get("market") != "US":
            fail("IR03 must preserve TikTok US context")
        if not required_tags.issubset(set(item.get("tag_ids", []))):
            fail("IR03 decisions must use explicit learned tag IDs")
    ir03_rule = ir03.get("expected", {}).get("learned_rule", {})
    if ir03_rule != {"rule_id": learned_rules.DEMO_RULE_ID, "status": "proposed"}:
        fail("IR03 must expect the fixed proposed learned rule")
    if ir03.get("expected", {}).get("independent_session_count", 0) < 2:
        fail("IR03 must assert two independent sessions")

    demo_script = (ROOT / "references/demo-script.md").read_text(encoding="utf-8")
    mac_home = "/" + "Users/"
    windows_home = "C:" + "\\Users\\"
    if mac_home in demo_script or windows_home in demo_script:
        fail("references/demo-script.md must not contain a machine-specific absolute path")
    for needle in ["demo-opening-positioning.md", "合成闭环", "虎步", "历史回测"]:
        if needle not in demo_script:
            fail(f"references/demo-script.md missing {needle}")
    video_demo = (ROOT / "scripts/run_video_demo.py").read_text(encoding="utf-8")
    for needle in ["OPENING_POSITIONING", "跨工具决策记忆缺口"]:
        if needle not in video_demo:
            fail(f"scripts/run_video_demo.py missing {needle}")

    result_schema = json.loads(
        (ROOT / "evals/product-research/schemas/final-result.schema.json").read_text(encoding="utf-8")
    )
    if "data_access" not in result_schema.get("properties", {}):
        fail("final-result schema missing data_access audit object")
    if "rule_effects" not in result_schema.get("properties", {}):
        fail("final-result schema missing rule_effects audit array")
    if "rule_effects" not in result_schema.get("required", []):
        fail("final-result schema must require rule_effects")

    rubric = json.loads((ROOT / "evals/product-research/rubric.json").read_text(encoding="utf-8"))
    if sum(item["points"] for item in rubric["dimensions"]) != 100:
        fail("product-research rubric must sum to 100")

    propose_script = (ROOT / "scripts/propose_learned.py").read_text(encoding="utf-8")
    for needle in [
        "No learned candidate found",
        "same_product_density_high",
        "differentiation_space_low",
        "aggregate_demo_rule",
    ]:
        if needle not in propose_script:
            fail(f"scripts/propose_learned.py missing {needle}")

    confirm_script = (ROOT / "scripts/confirm_learned.py").read_text(encoding="utf-8")
    for needle in [
        "--rule-id",
        "--confirmed-by",
        "confirmed_at",
        "validate_rule_evidence_files",
        '"active"',
    ]:
        if needle not in confirm_script:
            fail(f"scripts/confirm_learned.py missing {needle}")

    learned_kernel = (ROOT / "scripts/learned_rules.py").read_text(encoding="utf-8")
    for needle in ["Missing evidence file", "report_candidate_ids", "explicit_tag_ids"]:
        if needle not in learned_kernel:
            fail(f"scripts/learned_rules.py missing {needle}")

    revoke_script = (ROOT / "scripts/revoke_learned.py").read_text(encoding="utf-8")
    for needle in ["--rule-id", "--revoked-by", "--reason", '"revoked"']:
        if needle not in revoke_script:
            fail(f"scripts/revoke_learned.py missing {needle}")

    print("OK: repository structure and offline eval package are delivery-ready")


if __name__ == "__main__":
    main()
