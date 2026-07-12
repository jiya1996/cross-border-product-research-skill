#!/usr/bin/env python3
"""Confirm learned profile rules for a seller profile."""

from __future__ import annotations

import argparse
import datetime as dt
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAFE_SELLER_ID = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_-]{0,63}$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Confirm learned rules in sellers/{seller_id}/profile.yaml.")
    parser.add_argument("seller_id", help="Seller directory under sellers/.")
    parser.add_argument(
        "--index",
        type=int,
        default=0,
        help="Zero-based learned rule index to confirm. Defaults to 0.",
    )
    parser.add_argument("--all", action="store_true", help="Confirm all learned rules.")
    return parser.parse_args()


def collect_rules(lines: list[str]) -> list[dict]:
    rules = []
    current = None
    for lineno, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("- rule:"):
            if current:
                rules.append(current)
            current = {
                "rule": stripped.split(":", 1)[1].strip().strip('"'),
                "rule_line": lineno,
                "evidence": [],
                "confirmed_line": None,
                "confirmed_at_line": None,
            }
            continue
        if current and stripped.startswith("- decisions/"):
            current["evidence"].append(stripped[2:])
            continue
        if current and stripped.startswith("confirmed:"):
            current["confirmed_line"] = lineno
            continue
        if current and stripped.startswith("confirmed_at:"):
            current["confirmed_at_line"] = lineno
    if current:
        rules.append(current)
    return rules


def replace_value(line: str, key: str, value: str) -> str:
    indent = line[: len(line) - len(line.lstrip(" "))]
    return f"{indent}{key}: {value}\n"


def update_meta_date(lines: list[str], today: str) -> None:
    for index, line in enumerate(lines):
        if re.match(r"\s*updated:", line):
            lines[index] = replace_value(line, "updated", f'"{today}"')
            return


def main() -> None:
    args = parse_args()
    if not SAFE_SELLER_ID.fullmatch(args.seller_id):
        raise SystemExit("Invalid seller_id: paths and dots are forbidden.")
    today = dt.date.today().isoformat()
    profile_path = ROOT / "sellers" / args.seller_id / "profile.yaml"
    if not profile_path.is_file():
        raise SystemExit(f"Missing profile: {profile_path.relative_to(ROOT)}")

    lines = profile_path.read_text(encoding="utf-8").splitlines(keepends=True)
    rules = collect_rules(lines)
    if not rules:
        raise SystemExit("No learned rules found.")

    target_indexes = range(len(rules)) if args.all else [args.index]
    target_indexes = list(target_indexes)
    confirmed = []
    for rule_index in sorted(target_indexes, reverse=True):
        if rule_index < 0 or rule_index >= len(rules):
            raise SystemExit(f"Learned rule index out of range: {rule_index}")
        rule = rules[rule_index]
        for evidence in rule["evidence"]:
            evidence_path = ROOT / "sellers" / args.seller_id / evidence
            if not evidence_path.is_file():
                raise SystemExit(f"Missing evidence file: {evidence_path.relative_to(ROOT)}")
        confirmed_line = rule["confirmed_line"]
        if confirmed_line is None:
            raise SystemExit(f"Rule {rule_index} has no confirmed field.")
        lines[confirmed_line] = replace_value(lines[confirmed_line], "confirmed", "true")
        confirmed_at_line = rule["confirmed_at_line"]
        if confirmed_at_line is None:
            lines.insert(confirmed_line + 1, f"    confirmed_at: \"{today}\"\n")
        else:
            lines[confirmed_at_line] = replace_value(lines[confirmed_at_line], "confirmed_at", f'"{today}"')
        confirmed.append((rule_index, rule["rule"]))

    update_meta_date(lines, today)
    profile_path.write_text("".join(lines), encoding="utf-8")

    for rule_index, rule in sorted(confirmed):
        print(f"Confirmed learned[{rule_index}]: {rule}")
    print(f"Updated {profile_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
