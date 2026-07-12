#!/usr/bin/env python3
"""Run the synthetic TikTok product-research demo with deterministic guardrails.

This script is intentionally limited to the repository's synthetic fixture. It proves
the memory, filtering, scoring, attribution and learned-rule plumbing; it does not
claim that a live marketplace data connector has been verified.
"""

from __future__ import annotations

import argparse
import datetime as dt
import math
import re
import sys
from pathlib import Path
from typing import Optional


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import learned_rules  # noqa: E402
from propose_learned import aggregate_candidate_paths  # noqa: E402


DEFAULT_SELLER_ID = "_example"
SAFE_SELLER_ID = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_-]{0,63}$")

# Synthetic-only values mirrored from the cited repository references.
USD_CNY = 7.2  # references/demo-data/demo-assumptions.md
PLATFORM_RATE = 0.09  # 0.06 commission + 0.03 processing, references/platform-fees.md
PLATFORM_FIXED_USD = 0.30  # references/platform-fees.md

DEFAULT_WEIGHTS = {
    "demand": 0.25,
    "competition": 0.20,
    "margin": 0.20,
    "capability_fit": 0.20,
    "risk": 0.15,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the synthetic product-selection demo.")
    parser.add_argument(
        "--seller-id",
        default=DEFAULT_SELLER_ID,
        help="Safe seller directory name under sellers/. Defaults to _example.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=8,
        help="Number of ranked candidates to show in the report.",
    )
    parser.add_argument(
        "--label",
        default="",
        help="Optional report filename label, e.g. before or after.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Optional repository-relative report directory; defaults to reports/{seller_id}.",
    )
    return parser.parse_args()


def validate_seller_id(seller_id: str) -> None:
    if not SAFE_SELLER_ID.fullmatch(seller_id):
        raise SystemExit(
            "Invalid seller_id: use 1-64 letters, digits, underscores or hyphens; "
            "paths and dots are forbidden."
        )


def parse_scalar(value: str):
    value = value.strip()
    if value in {"null", ""}:
        return None
    if value in {"true", "false"}:
        return value == "true"
    if value.startswith("[") and value.endswith("]"):
        raw = value[1:-1].strip()
        if not raw:
            return []
        return [item.strip().strip('"').strip("'") for item in raw.split(",")]
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        pass
    try:
        number = float(value)
        if not math.isfinite(number):
            raise SystemExit("Profile numeric values must be finite; NaN/Inf are forbidden.")
        return number
    except ValueError:
        return value


def load_profile_text(text: str) -> dict:
    """Parse the small profile subset used by the deterministic demo."""
    data: dict[str, dict] = {}
    section = None
    subsection = None
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        if indent == 0 and stripped.endswith(":"):
            section = stripped[:-1]
            data[section] = {}
            subsection = None
            continue
        if indent == 0 and ":" in stripped:
            key, value = stripped.split(":", 1)
            data[key] = parse_scalar(value)
            section = key
            subsection = None
            continue
        if section and indent == 2 and ":" in stripped:
            key, value = stripped.split(":", 1)
            if value.strip():
                data[section][key] = parse_scalar(value)
                subsection = None
            else:
                data[section][key] = {}
                subsection = key
            continue
        if section and subsection and indent == 4 and ":" in stripped:
            key, value = stripped.split(":", 1)
            data[section][subsection][key] = parse_scalar(value)
    return data


def read_required_context(seller_id: str, run_at: str | None = None) -> dict:
    """Read all mandatory files in the same order as the Skill contract."""
    validate_seller_id(seller_id)
    try:
        context_paths = learned_rules.validate_seller_context(
            ROOT, seller_id, require_decisions=False
        )
    except learned_rules.RuleValidationError as exc:
        raise SystemExit(f"Invalid seller context: {exc}") from exc
    seller_root = context_paths["seller_root"]
    profile_path = context_paths["profile_path"]
    sop_path = seller_root / "sop.md"
    if not profile_path.is_file() or not sop_path.is_file():
        missing = []
        if not profile_path.is_file():
            missing.append(str(profile_path.relative_to(ROOT)))
        if not sop_path.is_file():
            missing.append(str(sop_path.relative_to(ROOT)))
        raise SystemExit("Missing seller memory; run intake-interview first: " + ", ".join(missing))

    try:
        context_paths = learned_rules.validate_seller_context(ROOT, seller_id)
    except learned_rules.RuleValidationError as exc:
        raise SystemExit(f"Invalid seller context: {exc}") from exc
    try:
        sop_path = learned_rules.validate_contained_file(
            seller_root, sop_path, "seller SOP"
        )
        decision_paths = learned_rules.safe_decision_paths(
            context_paths["decisions_path"]
        )
    except learned_rules.RuleValidationError as exc:
        raise SystemExit(f"Invalid seller memory path: {exc}") from exc

    # 1. profile, 2. SOP, 3. most recent ten decisions.
    profile_text = profile_path.read_text(encoding="utf-8")
    sop_text = sop_path.read_text(encoding="utf-8")
    rules = learned_rules.load_rules(profile_text)
    recent_paths = sorted(decision_paths, key=lambda path: path.name, reverse=True)[:10]
    recent_decisions = [(path, path.read_text(encoding="utf-8")) for path in recent_paths]
    for rule in learned_rules.active_rules(rules, now=run_at):
        try:
            learned_rules.validate_rule_evidence_files(rule, seller_root, ROOT)
        except learned_rules.RuleValidationError as exc:
            raise SystemExit(
                f"Active learned rule {rule['rule_id']} failed evidence validation: {exc}"
            ) from exc

    # 4-11. Policy, checklists, data map/contract, tool roles and platform strategy.
    reference_paths = [
        ROOT / "references" / "knowledge-policy.md",
        ROOT / "references" / "checklists" / "product-selection.md",
        ROOT / "references" / "checklists" / "scoring-rubric.md",
        ROOT / "references" / "data-sources" / "platform-data-map.md",
        ROOT / "references" / "data-sources" / "adapter-contract.md",
        ROOT / "references" / "data-sources" / "ecosystem-tool-role-map.md",
        ROOT / "references" / "data-sources" / "tool-role-registry.json",
        ROOT / "references" / "platforms" / "tiktok.md",
        ROOT / "references" / "demo-data" / "demo-assumptions.md",
        ROOT / "references" / "freight.md",
        ROOT / "references" / "platform-fees.md",
    ]
    reference_texts = {}
    for path in reference_paths:
        if not path.is_file():
            raise SystemExit(f"Missing required reference: {path.relative_to(ROOT)}")
        reference_texts[str(path.relative_to(ROOT))] = path.read_text(encoding="utf-8")

    return {
        "profile_path": profile_path,
        "profile_text": profile_text,
        "profile": load_profile_text(profile_text),
        "learned_rules": rules,
        "sop_path": sop_path,
        "sop_text": sop_text,
        "recent_decisions": recent_decisions,
        "references": reference_texts,
    }


def load_candidates(path: Path) -> list[dict]:
    rows = []
    table_lines = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip().startswith("|")
    ]
    if len(table_lines) < 3:
        return rows
    header = [cell.strip() for cell in table_lines[0].strip("|").split("|")]
    for line in table_lines[2:]:
        values = [cell.strip() for cell in line.strip("|").split("|")]
        if len(values) == len(header):
            row = dict(zip(header, values))
            raw_tags = row.get("rule_tag_ids", "").strip()
            if raw_tags.startswith("[") and raw_tags.endswith("]"):
                raw_tags = raw_tags[1:-1]
            row["rule_tag_ids"] = [
                item.strip().strip('"').strip("'")
                for item in re.split(r"[,，]", raw_tags)
                if item.strip()
            ]
            rows.append(row)
    return rows


def parse_volume(text: str) -> Optional[tuple[float, float, float]]:
    match = re.fullmatch(
        r"\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*[xX×]\s*"
        r"([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*[xX×]\s*"
        r"([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*",
        text or "",
    )
    if match is None:
        return None
    nums = [float(value) for value in match.groups()]
    if any(not math.isfinite(value) or value <= 0 for value in nums):
        return None
    return tuple(nums)  # type: ignore[return-value]


def parse_float(candidate: dict, field: str) -> Optional[float]:
    try:
        raw = candidate.get(field, "")
        if raw in {None, ""}:
            return None
        value = float(raw)
        if not math.isfinite(value):
            return None
        strictly_positive = {
            "target_price_usd",
            "supply_price_cny",
            "weight_g",
            "moq",
        }
        if field in strictly_positive and value <= 0:
            return None
        if field not in strictly_positive and value < 0:
            return None
        return value
    except (TypeError, ValueError):
        return None


def forbidden_reasons(candidate: dict, profile: dict, sop_text: str) -> list[str]:
    constraints = profile.get("constraints", {})
    category = candidate.get("category", "")
    risk_text = " ".join(
        [category, candidate.get("risk_flags", ""), candidate.get("product", "")]
    )
    reasons = []

    targets = [str(item).lower() for item in constraints.get("target_marketplaces", [])]
    if targets and not any("tiktok" in item for item in targets):
        reasons.append("目标平台 TikTok 不在 profile.constraints.target_marketplaces")

    for forbidden in constraints.get("forbidden_categories", []):
        if forbidden and str(forbidden) in category:
            reasons.append(f"命中 profile.constraints.forbidden_categories: {forbidden}")

    for forbidden in constraints.get("forbidden_attributes", []):
        text = str(forbidden)
        direct = text and text in risk_text
        compound_match = any(atom in risk_text for atom in ["易碎", "大件"] if atom in text)
        if direct or compound_match:
            reasons.append(f"命中 profile.constraints.forbidden_attributes: {forbidden}")

    # The demo SOP mirrors profile constraints. Reading and applying these explicit words
    # proves that deleting or changing SOP can no longer silently pass.
    for atom in ["易碎", "液体", "粉末", "大件", "侵权"]:
        if atom in sop_text and atom in risk_text:
            reasons.append(f"命中 sop.md 一票否决规则: {atom}")
    return list(dict.fromkeys(reasons))


def competition_score(text: str) -> Optional[int]:
    if not text.strip():
        return None
    if "极多" in text or "过多" in text:
        return 1
    if "高" in text:
        return 2
    if "中等" in text or "中等" in text:
        return 3
    return 4


def demand_score(text: str) -> Optional[int]:
    if not text.strip():
        return None
    if any(word in text for word in ["强", "明确", "高互动"]):
        return 4
    if any(word in text for word in ["稳定", "直观", "内容可拍", "复购潜力"]):
        return 3
    return 2


def freight_cost(candidate: dict, billable_kg: float) -> tuple[str, float]:
    flags = candidate.get("risk_flags", "")
    if "带电" in flags:
        # references/freight.md synthetic battery route.
        return "CN -> US 带电专线(合成)", billable_kg * 75 + 12
    # references/freight.md synthetic general-goods route.
    return "CN -> US 小包普货(合成)", billable_kg * 58 + 8


def known_cost_margin(candidate: dict) -> tuple[Optional[int], Optional[float], str, Optional[float]]:
    sale_usd = parse_float(candidate, "target_price_usd")
    supply_cny = parse_float(candidate, "supply_price_cny")
    weight_g = parse_float(candidate, "weight_g")
    volume = parse_volume(candidate.get("volume_cm", ""))
    if sale_usd is None or supply_cny is None or weight_g is None or volume is None:
        return None, None, "需人工核实", None

    length, width, height = volume
    billable_kg = max(weight_g / 1000, length * width * height / 6000)
    freight_route, freight_cny = freight_cost(candidate, billable_kg)
    platform_fee_cny = (sale_usd * PLATFORM_RATE + PLATFORM_FIXED_USD) * USD_CNY
    revenue_cny = sale_usd * USD_CNY
    margin_pct = (
        revenue_cny - supply_cny - freight_cny - platform_fee_cny
    ) / revenue_cny * 100
    if margin_pct >= 60:
        score = 5
    elif margin_pct >= 45:
        score = 4
    elif margin_pct >= 35:
        score = 3
    elif margin_pct >= 25:
        score = 2
    else:
        score = 1
    return score, margin_pct, freight_route, freight_cny


def capability_score(candidate: dict, profile: dict) -> Optional[int]:
    hook = candidate.get("content_hook", "").strip()
    content_skill = profile.get("capabilities", {}).get("content_skill")
    if not hook or content_skill is None:
        return None
    if float(content_skill) >= 4 and any(
        word in hook for word in ["前后", "对比", "一秒", "痛点", "场景"]
    ):
        return 4
    return 3


def risk_score(candidate: dict, is_filtered: bool) -> Optional[int]:
    if is_filtered:
        return 0
    flags = candidate.get("risk_flags", "").strip()
    if not flags:
        return None
    if any(
        marker in flags.casefold()
        for marker in ["待核实", "需核实", "待确认", "需确认", "unknown", "未知"]
    ):
        return None
    if any(word in flags for word in ["低客单", "兼容", "适配", "退货"]):
        return 3
    return 4


def apply_structured_rules(
    candidate: dict,
    scores: dict[str, Optional[int]],
    rules: list[dict],
    run_at: str | None = None,
) -> dict:
    """Apply v2 rules from IDs and data fields only; summary prose is inert."""

    result = learned_rules.apply_rules(
        candidate,
        scores,
        rules,
        platform="tiktok",
        market="US",
        category=str(candidate.get("category") or ""),
        now=run_at,
    )
    scores.update(result["scores"])
    return result


def actual_weights(profile: dict) -> dict[str, float]:
    raw = profile.get("preferences", {}).get("scoring_weights")
    if raw is None:
        raw = DEFAULT_WEIGHTS
    if not isinstance(raw, dict) or any(key not in raw for key in DEFAULT_WEIGHTS):
        raise SystemExit(
            "profile.preferences.scoring_weights must provide every scoring dimension"
        )
    try:
        weights = {key: float(raw[key]) for key in DEFAULT_WEIGHTS}
    except (TypeError, ValueError) as exc:
        raise SystemExit("profile.preferences.scoring_weights must be numeric") from exc
    if any(not math.isfinite(value) or not 0 <= value <= 1 for value in weights.values()):
        raise SystemExit(
            "profile.preferences.scoring_weights must be finite values from 0 to 1"
        )
    if abs(sum(weights.values()) - 1.0) > 0.001:
        raise SystemExit("profile.preferences.scoring_weights must sum to 1.0")
    return weights


def profile_number(
    value,
    field: str,
    *,
    minimum: float,
    maximum: float | None = None,
) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise SystemExit(f"{field} must be numeric") from exc
    if not math.isfinite(number) or number < minimum or (
        maximum is not None and number > maximum
    ):
        upper = f" and <= {maximum}" if maximum is not None else ""
        raise SystemExit(f"{field} must be finite and >= {minimum}{upper}")
    return number


def score_candidates(
    profile: dict,
    sop_text: str,
    candidates: list[dict],
    rules: list[dict],
    run_at: str | None = None,
) -> tuple[list[dict], list[dict], list[dict], dict[str, float]]:
    weights = actual_weights(profile)
    scored = []
    filtered = []
    pending = []
    margin_floor = profile_number(
        profile.get("preferences", {}).get("margin_floor_pct"),
        "profile.preferences.margin_floor_pct",
        minimum=0,
        maximum=100,
    )
    capital_max = profile_number(
        profile.get("constraints", {}).get("capital_per_sku_max"),
        "profile.constraints.capital_per_sku_max",
        minimum=0,
    )
    profile_number(
        profile.get("capabilities", {}).get("content_skill"),
        "profile.capabilities.content_skill",
        minimum=0,
        maximum=5,
    )

    for candidate in candidates:
        reasons = forbidden_reasons(candidate, profile, sop_text)
        margin, margin_pct, freight_route, freight_cny = known_cost_margin(candidate)
        moq = parse_float(candidate, "moq")
        supply_cny = parse_float(candidate, "supply_price_cny")
        candidate_data_missing = [
            field
            for field in ("target_price_usd", "supply_price_cny", "weight_g", "moq")
            if parse_float(candidate, field) is None
        ]
        if parse_volume(candidate.get("volume_cm", "")) is None:
            candidate_data_missing.append("volume_cm")
        known_initial_cny = None
        if moq is not None and supply_cny is not None and freight_cny is not None:
            known_initial_cny = moq * (supply_cny + freight_cny)
            if capital_max is not None and known_initial_cny > capital_max:
                reasons.append(
                    "已知采购+演示头程投入 "
                    f"{known_initial_cny:.0f} CNY 超过 profile.constraints.capital_per_sku_max="
                    f"{capital_max} CNY"
                )
        if margin_pct is not None and margin_floor is not None and margin_pct < margin_floor:
            reasons.append(
                f"已知演示成本口径毛利 {margin_pct:.1f}% 低于 "
                f"profile.preferences.margin_floor_pct={margin_floor}%"
            )

        is_filtered = bool(reasons)
        scores: dict[str, Optional[int]] = {
            "demand": demand_score(candidate.get("demand_signal", "")),
            "competition": competition_score(candidate.get("competition_signal", "")),
            "margin": margin,
            "capability_fit": capability_score(candidate, profile),
            "risk": risk_score(candidate, is_filtered),
        }
        missing_dimensions = [key for key, value in scores.items() if value is None]
        missing_dimensions.extend(
            f"data.{field}" for field in candidate_data_missing
        )
        missing_dimensions = list(dict.fromkeys(missing_dimensions))
        rule_result: dict = {"effects": [], "aggregates": [], "skipped": []}
        if not is_filtered and not missing_dimensions:
            rule_result = apply_structured_rules(candidate, scores, rules, run_at=run_at)
        rule_effects = rule_result["effects"]
        rule_aggregates = rule_result["aggregates"]

        total = None
        if not is_filtered and not missing_dimensions:
            total = sum(float(scores[key] or 0) * weights[key] for key in weights)

        row = {
            **candidate,
            **scores,
            "known_cost_margin_pct": margin_pct,
            "total": total,
            "freight_route": freight_route,
            "known_initial_cny": known_initial_cny,
            "rule_effects": rule_effects,
            "rule_aggregates": rule_aggregates,
            "rule_skips": rule_result["skipped"],
            "applied_profile_rules": "; ".join(
                f"{','.join(aggregate['rule_ids'])}: {aggregate['dimension']} "
                f"aggregate_delta={aggregate['total_delta']} "
                f"{aggregate['before']}->{aggregate['after']}"
                for aggregate in rule_aggregates
            )
            if rule_aggregates
            else "-",
            "filter_reason": "; ".join(dict.fromkeys(reasons)),
            "missing_dimensions": missing_dimensions,
        }
        if is_filtered:
            filtered.append(row)
        elif missing_dimensions:
            pending.append(row)
        else:
            scored.append(row)

    scored.sort(
        key=lambda item: (float(item["total"] or 0), float(item["known_cost_margin_pct"] or 0)),
        reverse=True,
    )
    return scored, filtered, pending, weights


def report_filename(today: str, label: str) -> str:
    if not label:
        return f"{today}_demo-run.md"
    safe_label = re.sub(r"[^a-zA-Z0-9_-]+", "-", label.strip()).strip("-").lower()
    return f"{today}_demo-run-{safe_label}.md" if safe_label else f"{today}_demo-run.md"


def report_output_dir(seller_id: str, requested: Path | None) -> Path:
    seller_report_root = ROOT / "reports" / seller_id
    if requested is None:
        candidate = seller_report_root
    else:
        requested = Path(requested)
        if requested.is_absolute():
            raise SystemExit("--output-dir must be repository-relative.")
        candidate = ROOT / requested
    root_resolved = ROOT.resolve()
    candidate_resolved = candidate.resolve()
    try:
        candidate_resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise SystemExit("--output-dir must stay inside the repository.") from exc

    allowed = candidate_resolved == seller_report_root.resolve()
    is_eval_seller = seller_id == "_example" or seller_id.startswith("eval-")
    eval_root = ROOT / "evals" / "product-research" / "artifacts"
    if is_eval_seller:
        try:
            candidate_resolved.relative_to(eval_root.resolve())
            allowed = True
        except ValueError:
            pass
    if not allowed:
        raise SystemExit(
            f"--output-dir for seller {seller_id!r} must be reports/{seller_id}; "
            "only synthetic/eval sellers may use evals/product-research/artifacts/."
        )

    current = candidate
    while True:
        if current.is_symlink():
            raise SystemExit(f"--output-dir path must not contain symlinks: {current}")
        if current.absolute() == ROOT.absolute():
            break
        if current.parent == current:
            raise SystemExit("--output-dir parent chain does not reach the repository root.")
        current = current.parent
    return candidate


def score_text(value: Optional[int]) -> str:
    return "N/A" if value is None else str(value)


def personalized_fit(row: dict, profile: dict) -> str:
    content_skill = profile.get("capabilities", {}).get("content_skill")
    styles = profile.get("preferences", {}).get("product_style", [])
    hook = row.get("content_hook", "")
    return (
        f"`profile.capabilities.content_skill={content_skill}` 与该品的素材钩子“{hook}”匹配；"
        f"`profile.preferences.product_style={styles}` 支持用轻创新/功能改良方式测试。"
    )


def personalized_misfit(row: dict, profile: dict) -> str:
    tolerance = profile.get("preferences", {}).get("competition_tolerance")
    margin_floor = profile.get("preferences", {}).get("margin_floor_pct")
    competition = row.get("competition_signal", "")
    return (
        f"`profile.preferences.competition_tolerance={tolerance}` 会放大“{competition}”的竞争风险；"
        f"且当前仅有已知演示成本口径，尚不能证明完整毛利高于 "
        f"`profile.preferences.margin_floor_pct={margin_floor}%`。"
    )


def write_report(
    seller_id: str,
    top_n: int,
    label: str,
    context: dict,
    scored: list[dict],
    filtered: list[dict],
    pending: list[dict],
    weights: dict[str, float],
    run_at: str | None = None,
    output_dir: Path | None = None,
) -> Path:
    today = dt.date.today().isoformat()
    out_dir = report_output_dir(seller_id, output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / report_filename(today, label)
    if out.is_symlink():
        raise SystemExit(f"Refusing to overwrite symlinked report file: {out}")
    profile = context["profile"]
    decision_names = [path.name for path, _ in context["recent_decisions"]]
    effective_at = run_at or dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    rules = context.get("learned_rules") or learned_rules.load_rules(context["profile_text"])
    active = learned_rules.active_rules(rules, now=effective_at)
    successor_by_predecessor = {
        rule["supersedes"]: rule
        for rule in rules
        if rule.get("supersedes")
    }
    inactive = []
    for rule in rules:
        status = learned_rules.effective_status(rule, now=effective_at)
        if status == "active":
            continue
        if status == "proposed":
            reason = "等待人工确认"
        elif status == "revoked":
            reason = f"{rule.get('revoke_reason')}; revoked_at={rule.get('revoked_at')}"
        elif status == "expired":
            reason = f"expires_at={rule.get('expires_at')}"
        elif status == "superseded":
            successor = successor_by_predecessor.get(rule["rule_id"])
            reason = (
                f"superseded_by={successor['rule_id']}"
                if successor is not None
                else "superseded_by=需人工核实"
            )
        else:
            reason = "需人工核实"
        if status == "superseded":
            successor = successor_by_predecessor.get(rule["rule_id"])
            audit_time = (
                successor.get("confirmed_at") if successor is not None else None
            )
        else:
            audit_time = None
        inactive.append(
            {
                "rule_id": rule["rule_id"],
                "status": status,
                "summary": rule["summary"],
                "scope": "/".join(
                    [
                        ",".join(rule["scope"]["platforms"]) or "*",
                        ",".join(rule["scope"]["markets"]) or "*",
                        ",".join(rule["scope"]["categories"]) or "*",
                    ]
                ),
                "audit_time": audit_time
                or rule.get("revoked_at")
                or rule.get("expires_at")
                or rule.get("confirmed_at")
                or rule["created"],
                "reason": reason,
            }
        )

    lines = [
        "# TikTok 画像感知选品 · 合成数据演示",
        "",
        "> 运行模式：`synthetic_demo`。本报告只证明流程与规则可运行，不构成真实市场、采购、利润或上架建议。实时卖家精灵/Sorftime MCP 尚需单独通过只读查询验证。",
        "",
        "## 任务与平台适配器",
        "",
        f"- seller_id: `{seller_id}`",
        "- 需求平台: TikTok US（推荐流量）",
        "- 平台策略: `references/platforms/tiktok.md`",
        "- 流程: 数据完整性检查 → constraints/SOP 过滤 → 五维评分 → 个性化归因",
        "",
        "## 已读取的卖家记忆",
        "",
        f"- profile: `sellers/{seller_id}/profile.yaml`",
        f"- sop: `sellers/{seller_id}/sop.md`",
        f"- 最近决策（最多 10 条）: {decision_names or '无'}",
        f"- learned 规则评估时点（UTC）: `{effective_at}`",
        f"- active learned 规则数: {len(active)}",
        f"- 停用/未生效 learned 规则数: {len(inactive)}",
        "",
        "## 数据来源、样本边界与缺口",
        "",
        "- 候选: `references/demo-data/tiktok-candidates.md`（15 条合成数据）",
        "- 换算假设: `references/demo-data/demo-assumptions.md`（合成）",
        "- 运费: `references/freight.md` 的演示线路",
        "- 平台费: `references/platform-fees.md` 的演示公式",
        "- 评分: `references/checklists/scoring-rubric.md`",
        "- 缺口: 广告、退货、税费、认证、合规、尾程与资金成本均未覆盖，必须人工核实；因此下表只能写“已知演示成本口径毛利”。",
        "",
        "## 实际评分权重",
        "",
        "| demand | competition | margin | capability_fit | risk |",
        "|---:|---:|---:|---:|---:|",
        f"| {weights['demand']:.2f} | {weights['competition']:.2f} | {weights['margin']:.2f} | {weights['capability_fit']:.2f} | {weights['risk']:.2f} |",
        "",
        "## 候选清单",
        "",
        "| product | demand | competition | margin | capability_fit | risk | 已知成本毛利* | total | 已应用画像规则 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in scored[:top_n]:
        margin_pct = row["known_cost_margin_pct"]
        lines.append(
            f"| {row['product']} | {score_text(row['demand'])} | {score_text(row['competition'])} | "
            f"{score_text(row['margin'])} | {score_text(row['capability_fit'])} | {score_text(row['risk'])} | "
            f"{margin_pct:.1f}% | {row['total']:.2f} | {row['applied_profile_rules']} |"
        )
    lines.extend(
        [
            "",
            "* 已知成本毛利仅含合成售价、采购、演示头程和演示平台费，不是实际毛利。",
            "",
            "排序键：先按 `total` 降序，再按已知成本口径毛利降序打破同分。",
            "",
            "## Top 候选逐项归因",
        ]
    )
    for index, row in enumerate(scored[:top_n], 1):
        lines.extend(
            [
                "",
                f"### {index}. {row['product']} (`{row['id']}`)",
                "",
                f"- 为什么适合你：{personalized_fit(row, profile)}",
                f"- 为什么不适合你：{personalized_misfit(row, profile)}",
                f"- 主要风险（合成候选字段）：{row.get('risk_flags') or '需人工核实'}。事实风险需用真实来源复核。",
                "- 下一步最小验证：补齐真实目标平台需求、竞争数据、供应商报价/重量尺寸，以及广告、退货、合规和税费后重算。",
            ]
        )

    adjusted = [row for row in scored if row["applied_profile_rules"] != "-"]
    lines.extend(["", "## 已应用 active learned 规则的候选", ""])
    if adjusted:
        lines.extend(
            [
                "| product | 已应用规则及分值变化 | total |",
                "|---|---|---:|",
            ]
        )
        for row in adjusted:
            lines.append(
                f"| {row['product']} | {row['applied_profile_rules']} | {row['total']:.2f} |"
            )
    else:
        lines.append("- 无。本轮没有 active 规则命中；learned 不改变硬过滤，且非 active 不参与打分。")

    skipped_rows = [
        (row["product"], item["rule_id"], item["reason"])
        for row in scored[:top_n]
        for item in row["rule_skips"]
    ]
    lines.extend(["", "## active learned 未命中说明（本报告 Top 候选）", ""])
    if skipped_rows:
        lines.extend(["| product | rule_id | reason |", "|---|---|---|"])
        for product, rule_id, reason in skipped_rows:
            lines.append(f"| {product} | {rule_id} | {reason} |")
    else:
        lines.append("- 无 active 规则跳过记录。")

    lines.extend(["", "## 已停用或未生效的 learned 规则", ""])
    if inactive:
        lines.extend(
            [
                "| rule_id | status | scope(platform/market/category) | audit_time | reason | summary |",
                "|---|---|---|---|---|---|",
            ]
        )
        for rule in inactive:
            lines.append(
                f"| {rule['rule_id']} | {rule['status']} | {rule['scope']} | "
                f"{rule['audit_time']} | {rule['reason']} | {rule['summary']} |"
            )
    else:
        lines.append("- 无。停用规则不会从记忆中消失；有记录时将在此显示。")

    lines.extend(["", "## 被过滤品及原因", "", "| product | reason |", "|---|---|"])
    if filtered:
        for row in filtered:
            lines.append(f"| {row['product']} | {row['filter_reason']} |")
    else:
        lines.append("| - | 本轮无一票否决项 |")

    lines.extend(["", "## blocked_pending_data", ""])
    if pending:
        lines.extend(["| product | 缺失评分维度 |", "|---|---|"])
        for row in pending:
            lines.append(f"| {row['product']} | {', '.join(row['missing_dimensions'])} |")
    else:
        lines.append("- 本合成 fixture 的五维演示字段齐全；真实运行不得据此假设数据同样齐全。")

    lines.extend(["", "## profile-update 聚合结果", ""])
    proposal = aggregate_candidate_paths(
        [path for path, _ in context["recent_decisions"]], created=today
    )
    if proposal:
        session_count = len({item["session_id"] for item in proposal["evidence"]})
        try:
            persisted = learned_rules.find_rule(rules, proposal["rule_id"])
            persisted_status = learned_rules.effective_status(persisted, now=effective_at)
        except KeyError:
            persisted_status = "not_persisted"
        lines.extend(
            [
                f"- rule_id: `{proposal['rule_id']}`",
                f"- summary: {proposal['summary']}",
                f"- condition_tag_ids: `{proposal['condition_tag_ids']}`",
                f"- action: `{proposal['action']['dimension']} {proposal['action']['delta']:+d}`",
                f"- evidence: {len(proposal['evidence'])} 条拒绝，{session_count} 个独立会话",
                f"- profile 中当前状态: `{persisted_status}`；只有 `active` 参与评分。",
            ]
        )
    else:
        lines.append("- 暂无满足至少 3 条拒绝证据且跨至少 2 个独立会话的候选规则。")

    lines.extend(
        [
            "",
            "## 依据分类",
            "",
            "- 画像依据：本卖家的 profile、SOP、最近 10 条决策。",
            "- 数据依据：合成候选、演示换算、演示运费与演示平台费。",
            "- 经验依据：TikTok 推荐流量与素材可拍性策略。",
            "- 需人工核实：所有真实价格、需求、竞争、供应链、物流、平台费用、广告、退货、合规、认证和税费。",
            "",
            "## 下一步建议",
            "",
            "1. 先按 `config/mcp.md` 接入并验证一个只读数据源；",
            "2. 将真实返回归一化为 `references/schemas/candidate-batch.schema.json`；",
            "3. 对本轮 Top 候选补 1688 供应链验证与完整成本，再运行模式 B 压力测试；",
            "4. 用户反馈必须通过 recommendation-review 记录，不在本 Skill 中修改画像。",
        ]
    )
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def main() -> None:
    args = parse_args()
    validate_seller_id(args.seller_id)
    if args.top_n < 1:
        raise SystemExit("--top-n must be >= 1")

    run_at = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    context = read_required_context(args.seller_id, run_at=run_at)
    rules = context["learned_rules"]
    candidates = load_candidates(ROOT / "references" / "demo-data" / "tiktok-candidates.md")
    scored, filtered, pending, weights = score_candidates(
        context["profile"], context["sop_text"], candidates, rules, run_at=run_at
    )
    report = write_report(
        args.seller_id,
        args.top_n,
        args.label,
        context,
        scored,
        filtered,
        pending,
        weights,
        run_at=run_at,
        output_dir=args.output_dir,
    )

    print(f"Generated {report.relative_to(ROOT)}")
    print("Top 3:")
    for row in scored[:3]:
        print(
            f"- {row['product']}: {row['total']:.2f} "
            f"(known-cost margin {row['known_cost_margin_pct']:.1f}%)"
        )
    if filtered:
        print("Filtered:")
        for row in filtered:
            print(f"- {row['product']}: {row['filter_reason']}")
    if pending:
        print("Pending data:")
        for row in pending:
            print(f"- {row['product']}: {', '.join(row['missing_dimensions'])}")


if __name__ == "__main__":
    main()
