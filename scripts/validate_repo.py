#!/usr/bin/env python3
"""Validate the offline delivery structure and evaluation contract."""

from __future__ import annotations

import json
import sys
from pathlib import Path

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
    "references/freight.md",
    "references/platform-fees.md",
    "references/demo-script.md",
    "references/demo-opening-positioning.md",
    "references/questions/recent-selection-retrospective.md",
    "config/hubu-rpa-allowlist.example.yaml",
    "sellers/_example/profile.yaml",
    "sellers/_example/sop.md",
    "reports/_example/2026-07-06_tiktok-pet-products.md",
    "scripts/run_demo.py",
    "scripts/propose_learned.py",
    "scripts/confirm_learned.py",
    "scripts/check_data_access.py",
    "scripts/reset_demo.py",
    "scripts/run_product_research_evals.py",
    "scripts/run_video_demo.py",
    "scripts/verify_delivery.py",
    "scripts/install_project_skills.py",
    "scripts/build_release.py",
    "evals/product-research/cases.json",
    "evals/product-research/rubric.json",
    "evals/product-research/schemas/final-result.schema.json",
    "evals/product-research/README.md",
    "evals/intake-retrospective/cases.json",
    "evals/intake-retrospective/README.md",
    "tests/test_product_research_demo.py",
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
    ],
    "skills/recommendation-review/SKILL.md": [
        "YYYY-MM-DD_product-slug.md",
        "historical_retrospective",
        "后来结果状态",
        "recalled",
    ],
    "skills/profile-update/SKILL.md": ["confirmed_at: YYYY-MM-DD"],
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


def decision_tags(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("- 归类标签:"):
            raw = line.split(":", 1)[1].strip()
            if raw.startswith("[") and raw.endswith("]"):
                return [tag.strip() for tag in raw[1:-1].split(",")]
    return []


def example_learned_rules() -> list[dict]:
    rules = []
    current = None
    text = (ROOT / "sellers/_example/profile.yaml").read_text(encoding="utf-8")
    for raw in text.splitlines():
        stripped = raw.strip()
        if stripped.startswith("- rule:"):
            if current:
                rules.append(current)
            current = {"rule": stripped.split(":", 1)[1].strip().strip('"'), "evidence": []}
            continue
        if current and stripped.startswith("- decisions/"):
            current["evidence"].append(stripped[2:])
    if current:
        rules.append(current)
    return rules


def keywords_for_rule(rule: str) -> list[str]:
    candidates = ["同款过多", "差异化不足", "素材记忆点弱", "易损", "包装风险", "物流属性待核实"]
    return [keyword for keyword in candidates if keyword in rule]


def validate_learned_evidence() -> None:
    decision_root = ROOT / "sellers/_example"
    for learned in example_learned_rules():
        if not learned["evidence"]:
            fail(f"learned rule has no evidence: {learned['rule']}")
        keywords = keywords_for_rule(learned["rule"])
        for rel in learned["evidence"]:
            path = decision_root / rel
            if not path.is_file():
                fail(f"learned evidence missing: sellers/_example/{rel}")
            tags = decision_tags(path)
            if keywords and not any(keyword in tags for keyword in keywords):
                fail(f"learned evidence tags do not match rule: sellers/_example/{rel}")


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
    for needle in ["sellers/*", "!sellers/_example/**", "reports/*", "!reports/_example/**"]:
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

    demo_script = (ROOT / "references/demo-script.md").read_text(encoding="utf-8")
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

    rubric = json.loads((ROOT / "evals/product-research/rubric.json").read_text(encoding="utf-8"))
    if sum(item["points"] for item in rubric["dimensions"]) != 100:
        fail("product-research rubric must sum to 100")

    propose_script = (ROOT / "scripts/propose_learned.py").read_text(encoding="utf-8")
    for needle in ["No learned candidate found", "同款过多", "差异化不足", "confirmed: false"]:
        if needle not in propose_script:
            fail(f"scripts/propose_learned.py missing {needle}")

    confirm_script = (ROOT / "scripts/confirm_learned.py").read_text(encoding="utf-8")
    for needle in ["confirmed_at", "Missing evidence file", "updated"]:
        if needle not in confirm_script:
            fail(f"scripts/confirm_learned.py missing {needle}")

    print("OK: repository structure and offline eval package are delivery-ready")


if __name__ == "__main__":
    main()
