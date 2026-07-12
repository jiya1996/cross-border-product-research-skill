#!/usr/bin/env python3
"""Append learned candidate rules from seller decision logs."""

from __future__ import annotations

import argparse
import datetime as dt
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAFE_SELLER_ID = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_-]{0,63}$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Append learned candidate rules to a seller profile.")
    parser.add_argument("seller_id", help="Seller directory under sellers/.")
    return parser.parse_args()


def decision_tags(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"归类标签:\s*\[(.*?)\]", text)
    if not match:
        return []
    return [tag.strip() for tag in match.group(1).split(",")]


def rejected_decision(path: Path) -> bool:
    return "用户决定: rejected" in path.read_text(encoding="utf-8")


def build_candidate_rule(decision_dir: Path) -> tuple[str, list[str]] | None:
    evidence = []
    for path in sorted(decision_dir.glob("*.md")):
        if not rejected_decision(path):
            continue
        tags = decision_tags(path)
        if "同款过多" in tags and "差异化不足" in tags:
            evidence.append(path.name)
    if len(evidence) < 3:
        return None
    return (
        "用户连续拒绝同款过多且差异化不足的 TikTok 品, 后续推荐中应降低同款密度高且内容记忆点弱的候选权重。",
        evidence[:3],
    )


def learned_block(rule: str, evidence: list[str], today: str) -> list[str]:
    lines = [
        f'  - rule: "{rule}"\n',
        "    evidence:\n",
    ]
    for item in evidence:
        lines.append(f"      - decisions/{item}\n")
    lines.extend(
        [
            "    confirmed: false\n",
            f'    created: "{today}"\n',
            "    confirmed_at: null\n",
        ]
    )
    return lines


def append_rule(profile_path: Path, rule: str, evidence: list[str]) -> bool:
    today = dt.date.today().isoformat()
    text = profile_path.read_text(encoding="utf-8")
    if rule in text:
        return False

    lines = text.splitlines(keepends=True)
    block = learned_block(rule, evidence, today)
    for index, line in enumerate(lines):
        if line.strip() == "learned: []":
            lines[index : index + 1] = ["learned:\n", *block]
            profile_path.write_text("".join(lines), encoding="utf-8")
            return True
        if line.strip() == "learned:":
            insert_at = len(lines)
            for next_index in range(index + 1, len(lines)):
                stripped = lines[next_index].strip()
                if stripped and not lines[next_index].startswith((" ", "\t")):
                    insert_at = next_index
                    break
            lines[insert_at:insert_at] = block
            profile_path.write_text("".join(lines), encoding="utf-8")
            return True

    lines.extend(["\n", "learned:\n", *block])
    profile_path.write_text("".join(lines), encoding="utf-8")
    return True


def main() -> None:
    args = parse_args()
    if not SAFE_SELLER_ID.fullmatch(args.seller_id):
        raise SystemExit("Invalid seller_id: paths and dots are forbidden.")
    seller_root = ROOT / "sellers" / args.seller_id
    profile_path = seller_root / "profile.yaml"
    decision_dir = seller_root / "decisions"
    if not profile_path.is_file():
        raise SystemExit(f"Missing profile: {profile_path.relative_to(ROOT)}")
    if not decision_dir.is_dir():
        raise SystemExit(f"Missing decision directory: {decision_dir.relative_to(ROOT)}")

    candidate = build_candidate_rule(decision_dir)
    if not candidate:
        raise SystemExit("No learned candidate found. Need >=3 rejected decisions with 同款过多 and 差异化不足.")
    rule, evidence = candidate
    changed = append_rule(profile_path, rule, evidence)
    if changed:
        print(f"Proposed learned rule: {rule}")
        print("Evidence:")
        for item in evidence:
            print(f"- decisions/{item}")
        print(f"Updated {profile_path.relative_to(ROOT)}")
    else:
        print("Learned rule already exists; no change.")


if __name__ == "__main__":
    main()
