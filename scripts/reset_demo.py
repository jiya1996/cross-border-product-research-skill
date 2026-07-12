#!/usr/bin/env python3
"""Reset the public _example profile to its unconfirmed learned-rule baseline."""

from __future__ import annotations

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "references" / "demo-data" / "example-profile-baseline.yaml"
TARGET = ROOT / "sellers" / "_example" / "profile.yaml"


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset only sellers/_example/profile.yaml.")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Apply the reset. Without this flag the script is a dry run.",
    )
    args = parser.parse_args()
    if not SOURCE.is_file():
        raise SystemExit(f"Missing baseline: {SOURCE.relative_to(ROOT)}")
    if not args.yes:
        print(f"Dry run: would restore {TARGET.relative_to(ROOT)} from {SOURCE.relative_to(ROOT)}")
        return
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(SOURCE.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"Restored {TARGET.relative_to(ROOT)}; learned rules are empty")


if __name__ == "__main__":
    main()
