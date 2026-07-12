#!/usr/bin/env python3
"""Register repository skills under .agents/skills using relative symlinks."""

from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "skills"
TARGET_ROOT = ROOT / ".agents" / "skills"


def main() -> None:
    TARGET_ROOT.mkdir(parents=True, exist_ok=True)
    installed = []
    for skill in sorted(SOURCE_ROOT.iterdir()):
        if not skill.is_dir() or not (skill / "SKILL.md").is_file():
            continue
        target = TARGET_ROOT / skill.name
        relative_source = Path("..") / ".." / "skills" / skill.name
        if target.is_symlink():
            if Path(os.readlink(target)) != relative_source:
                raise SystemExit(f"Unexpected symlink target: {target}")
        elif target.exists():
            raise SystemExit(f"Refusing to replace existing non-symlink: {target}")
        else:
            target.symlink_to(relative_source, target_is_directory=True)
        installed.append(skill.name)
    print("Registered project skills: " + ", ".join(installed))


if __name__ == "__main__":
    main()
