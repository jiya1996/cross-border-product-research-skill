#!/usr/bin/env python3
"""Confirm one proposed learned rule after re-validating its evidence."""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import re
from pathlib import Path

try:
    import learned_rules
except ModuleNotFoundError:  # Imported as ``scripts.confirm_learned`` in tests.
    from scripts import learned_rules


ROOT = Path(__file__).resolve().parents[1]
SAFE_SELLER_ID = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_-]{0,63}$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Activate one proposed learned rule after evidence validation."
    )
    parser.add_argument("seller_id", help="Seller directory under sellers/.")
    parser.add_argument("--rule-id", required=True, help="Exact learned rule_id to activate.")
    parser.add_argument(
        "--confirmed-by",
        required=True,
        help="Human/operator identity recorded in the audit trail.",
    )
    return parser.parse_args()


def validate_seller_id(seller_id: str) -> None:
    if not SAFE_SELLER_ID.fullmatch(seller_id):
        raise SystemExit("Invalid seller_id: paths and dots are forbidden.")


def validate_confirmation(
    rule: dict,
    seller_root: Path,
    *,
    now: str,
) -> list[dict]:
    """Re-read and validate every evidence record for one proposed rule."""

    try:
        normalized = learned_rules.validate_rule(rule)
    except (TypeError, ValueError, KeyError) as exc:
        raise SystemExit(
            f"Invalid learned rule {rule.get('rule_id', '<missing>')}: {exc}"
        ) from exc
    if normalized["status"] != "proposed":
        raise SystemExit(
            f"Rule {normalized['rule_id']} is {normalized['status']}; "
            "only proposed rules can be confirmed."
        )
    try:
        status = learned_rules.effective_status(normalized, now=now)
    except learned_rules.RuleValidationError as exc:
        raise SystemExit(f"Invalid confirmation time: {exc}") from exc
    if status != "proposed":
        raise SystemExit(
            f"Rule {normalized['rule_id']} is expired at {now}; expired proposals "
            "cannot be confirmed."
        )
    try:
        return learned_rules.validate_rule_evidence_files(normalized, seller_root, ROOT)
    except learned_rules.RuleValidationError as exc:
        raise SystemExit(str(exc)) from exc


def confirm_rule(
    profile_path: Path,
    seller_root: Path,
    rule_id: str,
    confirmed_by: str,
    *,
    confirmed_at: str | None = None,
) -> dict:
    seller_root = Path(seller_root)
    try:
        context = learned_rules.validate_seller_context(ROOT, seller_root.name)
    except learned_rules.RuleValidationError as exc:
        raise SystemExit(f"Invalid seller context: {exc}") from exc
    if seller_root.absolute() != context["seller_root"].absolute() or Path(
        profile_path
    ).absolute() != context["profile_path"].absolute():
        raise SystemExit("Seller root/profile path does not match the validated seller context.")
    profile_path = context["profile_path"]
    seller_root = context["seller_root"]
    profile_text = profile_path.read_text(encoding="utf-8")
    read_hash = learned_rules.profile_content_hash(profile_text)
    rules = learned_rules.load_rules(profile_text)
    try:
        rule = learned_rules.find_rule(rules, rule_id)
    except (KeyError, LookupError, ValueError) as exc:
        raise SystemExit(f"Unknown learned rule_id: {rule_id}") from exc
    if rule is None:
        raise SystemExit(f"Unknown learned rule_id: {rule_id}")
    actor = confirmed_by.strip()
    if not actor:
        raise SystemExit("--confirmed-by must not be blank.")
    timestamp = confirmed_at or dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    validate_confirmation(rule, seller_root, now=timestamp)

    # Build the complete successor/predecessor transition in memory, validate
    # the collection, and replace the profile once. A proposed successor never
    # changes the old active rule; confirmation is the atomic switch point.
    updated_rules = copy.deepcopy(rules)
    updated_rule = next(item for item in updated_rules if item["rule_id"] == rule_id)
    updated_rule["status"] = "active"
    updated_rule["confirmed_by"] = actor
    updated_rule["confirmed_at"] = timestamp

    predecessor_id = updated_rule["supersedes"]
    if predecessor_id is not None:
        predecessor = next(
            (item for item in updated_rules if item["rule_id"] == predecessor_id), None
        )
        if predecessor is None:  # Defensive; collection validation normally catches this.
            raise SystemExit(f"Unknown superseded rule_id: {predecessor_id}")
        if predecessor["status"] != "active":
            raise SystemExit(
                f"Superseded predecessor {predecessor_id} is {predecessor['status']}; "
                "only an active predecessor can be replaced."
            )
        predecessor["status"] = "superseded"

    try:
        normalized_rules = learned_rules.validate_rules(updated_rules)
    except learned_rules.RuleValidationError as exc:
        raise SystemExit(f"Cannot confirm learned rule {rule_id}: {exc}") from exc
    try:
        learned_rules.save_rules(
            profile_path, normalized_rules, expected_hash=read_hash
        )
    except learned_rules.RuleValidationError as exc:
        raise SystemExit(str(exc)) from exc
    return next(item for item in normalized_rules if item["rule_id"] == rule_id)


def main() -> None:
    args = parse_args()
    validate_seller_id(args.seller_id)
    try:
        context = learned_rules.validate_seller_context(ROOT, args.seller_id)
    except learned_rules.RuleValidationError as exc:
        raise SystemExit(f"Invalid seller context: {exc}") from exc
    seller_root = context["seller_root"]
    profile_path = context["profile_path"]

    rule = confirm_rule(profile_path, seller_root, args.rule_id, args.confirmed_by)
    print(f"Activated learned rule: {rule['rule_id']}")
    print(f"Confirmed by: {rule['confirmed_by']}")
    print(f"Updated {profile_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
