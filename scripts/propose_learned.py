#!/usr/bin/env python3
"""Propose the deterministic demo learned rule from structured decisions."""

from __future__ import annotations

import argparse
import datetime as dt
import re
from pathlib import Path
from typing import Iterable

try:
    import learned_rules
except ModuleNotFoundError:  # Imported as ``scripts.propose_learned`` in tests.
    from scripts import learned_rules


ROOT = Path(__file__).resolve().parents[1]
SAFE_SELLER_ID = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_-]{0,63}$")
DEMO_RULE_ID = "learned_tiktok_same_density_diff_001"
DEMO_CONDITION_TAG_IDS = [
    "same_product_density_high",
    "differentiation_space_low",
]
DEMO_SUMMARY = (
    "用户连续拒绝同款密度高且差异化空间小的 TikTok 候选品，"
    "后续推荐中应降低这类候选品的竞争维度得分。"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Propose a structured learned rule in sellers/{seller_id}/profile.yaml."
    )
    parser.add_argument("seller_id", help="Seller directory under sellers/.")
    return parser.parse_args()


def validate_seller_id(seller_id: str) -> None:
    if not SAFE_SELLER_ID.fullmatch(seller_id):
        raise SystemExit("Invalid seller_id: paths and dots are forbidden.")


def aggregate_candidate_paths(
    decision_paths: Iterable[Path],
    *,
    created: str | None = None,
) -> dict | None:
    """Return the one supported v2 candidate from an explicit decision window.

    Keeping this as a public pure function lets ``run_demo.py`` render the same
    proposal that this command persists instead of maintaining a second
    keyword-based aggregator.
    """

    candidate = learned_rules.aggregate_demo_rule(
        decision_paths,
        rule_id=DEMO_RULE_ID,
        summary=DEMO_SUMMARY,
        condition_tag_ids=DEMO_CONDITION_TAG_IDS,
        scope={"platforms": ["tiktok"], "markets": ["US"], "categories": []},
        action={"dimension": "competition", "delta": -1},
        created=created or dt.date.today().isoformat(),
    )
    if candidate is not None:
        # Keep the documented condition order deterministic for human review;
        # matching remains a subset operation in the shared kernel.
        candidate["condition_tag_ids"] = list(DEMO_CONDITION_TAG_IDS)
        candidate = learned_rules.validate_rule(candidate)
    return candidate


def aggregate_candidate_rule(
    decision_dir: Path,
    *,
    created: str | None = None,
) -> dict | None:
    """Aggregate all decision files for the profile-update command."""

    try:
        paths = learned_rules.safe_decision_paths(decision_dir)
    except learned_rules.RuleValidationError as exc:
        raise SystemExit(f"Invalid decision directory: {exc}") from exc
    return aggregate_candidate_paths(paths, created=created)


# Backward-compatible name for callers of the old command module. It now
# delegates to the single structured aggregator above.
build_candidate_rule = aggregate_candidate_rule


def propose_rule(profile_path: Path, decision_dir: Path, *, created: str | None = None) -> tuple[dict, bool]:
    try:
        context = learned_rules.validate_profile_entry(
            profile_path, decision_dir=decision_dir
        )
    except learned_rules.RuleValidationError as exc:
        raise SystemExit(f"Invalid seller context: {exc}") from exc
    profile_path = context["profile_path"]
    decision_dir = context["decisions_path"]
    candidate = aggregate_candidate_rule(decision_dir, created=created)
    if candidate is None:
        raise SystemExit(
            "No learned candidate found. Need >=3 rejected structured decisions "
            "with tag IDs same_product_density_high and differentiation_space_low "
            "from >=2 independent sessions."
        )

    profile_text = profile_path.read_text(encoding="utf-8")
    read_hash = learned_rules.profile_content_hash(profile_text)
    rules = learned_rules.load_rules(profile_text)
    try:
        existing = learned_rules.find_rule(rules, candidate["rule_id"])
    except (KeyError, LookupError, ValueError):
        existing = None
    if existing is None:
        rules.append(candidate)
        try:
            learned_rules.save_rules(profile_path, rules, expected_hash=read_hash)
        except learned_rules.RuleValidationError as exc:
            raise SystemExit(str(exc)) from exc
        return candidate, True
    return candidate, False


def main() -> None:
    args = parse_args()
    validate_seller_id(args.seller_id)
    try:
        context = learned_rules.validate_seller_context(ROOT, args.seller_id)
    except learned_rules.RuleValidationError as exc:
        raise SystemExit(f"Invalid seller context: {exc}") from exc
    profile_path = context["profile_path"]
    decision_dir = context["decisions_path"]

    candidate, changed = propose_rule(profile_path, decision_dir)
    if not changed:
        print(f"Learned rule {candidate['rule_id']} already exists; no change.")
        return

    print(f"Proposed learned rule: {candidate['rule_id']}")
    print(f"Summary: {candidate['summary']}")
    print("Evidence:")
    for evidence in candidate["evidence"]:
        print(f"- {evidence['decision_path']} [{evidence['session_id']}]")
    print(f"Updated {profile_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
