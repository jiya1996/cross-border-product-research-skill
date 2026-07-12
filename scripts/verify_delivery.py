#!/usr/bin/env python3
"""Run all offline delivery gates and produce one fresh synthetic demo report."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


COMMANDS = [
    [sys.executable, "scripts/validate_repo.py"],
    [sys.executable, "scripts/run_product_research_evals.py", "--mode", "static"],
    [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
    [sys.executable, "scripts/check_data_access.py", "--json"],
    [
        sys.executable,
        "scripts/run_demo.py",
        "--seller-id",
        "_example",
        "--top-n",
        "8",
        "--label",
        "delivery-verify",
    ],
]


def main() -> None:
    for command in COMMANDS:
        print("+ " + " ".join(command), flush=True)
        completed = subprocess.run(command, cwd=ROOT)
        if completed.returncode != 0:
            raise SystemExit(completed.returncode)
    print("OK: offline delivery gates passed; live MCP still requires a separate read-only smoke test")


if __name__ == "__main__":
    main()
