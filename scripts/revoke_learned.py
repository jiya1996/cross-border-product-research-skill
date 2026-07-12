#!/usr/bin/env python3
"""Revoke one active learned rule while retaining its audit history."""

from __future__ import annotations

import argparse
import datetime as dt
import re
from pathlib import Path

try:
    import learned_rules
except ModuleNotFoundError:  # Imported as ``scripts.revoke_learned`` in tests.
    from scripts import learned_rules


ROOT = Path(__file__).resolve().parents[1]
SAFE_SELLER_ID = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_-]{0,63}$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Revoke one active learned rule.")
    parser.add_argument("seller_id", help="Seller directory under sellers/.")
    parser.add_argument("--rule-id", required=True, help="Exact active learned rule_id to revoke.")
    parser.add_argument(
        "--revoked-by",
        required=True,
        help="Human/operator identity recorded in the audit trail.",
    )
    parser.add_argument("--reason", required=True, help="Why the active rule is being revoked.")
    return parser.parse_args()


def validate_seller_id(seller_id: str) -> None:
    if not SAFE_SELLER_ID.fullmatch(seller_id):
        raise SystemExit("Invalid seller_id: paths and dots are forbidden.")


def revoke_rule(
    profile_path: Path,
    rule_id: str,
    revoked_by: str,
    reason: str,
    *,
    revoked_at: str | None = None,
) -> dict:
    actor = revoked_by.strip()
    explanation = reason.strip()
    if not actor:
        raise SystemExit("--revoked-by must not be blank.")
    if not explanation:
        raise SystemExit("--reason must not be blank.")

    try:
        context = learned_rules.validate_profile_entry(profile_path)
    except learned_rules.RuleValidationError as exc:
        raise SystemExit(f"Invalid seller context: {exc}") from exc
    profile_path = context["profile_path"]
    profile_text = profile_path.read_text(encoding="utf-8")
    read_hash = learned_rules.profile_content_hash(profile_text)
    rules = learned_rules.load_rules(profile_text)
    try:
        rule = learned_rules.find_rule(rules, rule_id)
    except (KeyError, LookupError, ValueError) as exc:
        raise SystemExit(f"Unknown learned rule_id: {rule_id}") from exc
    if rule is None:
        raise SystemExit(f"Unknown learned rule_id: {rule_id}")
    if rule.get("status") != "active":
        raise SystemExit(
            f"Rule {rule_id} is {rule.get('status')}; only active rules can be revoked."
        )

    rule["status"] = "revoked"
    rule["revoked_by"] = actor
    rule["revoked_at"] = revoked_at or dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    rule["revoke_reason"] = explanation
    rule = learned_rules.validate_rule(rule)
    rules = [rule if item.get("rule_id") == rule_id else item for item in rules]
    try:
        learned_rules.save_rules(profile_path, rules, expected_hash=read_hash)
    except learned_rules.RuleValidationError as exc:
        raise SystemExit(str(exc)) from exc
    return rule


def main() -> None:
    args = parse_args()
    validate_seller_id(args.seller_id)
    try:
        context = learned_rules.validate_seller_context(ROOT, args.seller_id)
    except learned_rules.RuleValidationError as exc:
        raise SystemExit(f"Invalid seller context: {exc}") from exc
    profile_path = context["profile_path"]

    rule = revoke_rule(profile_path, args.rule_id, args.revoked_by, args.reason)
    print(f"Revoked learned rule: {rule['rule_id']}")
    print(f"Revoked by: {rule['revoked_by']}")
    print(f"Reason: {rule['revoke_reason']}")
    print(f"Updated {profile_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
