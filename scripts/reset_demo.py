#!/usr/bin/env python3
"""Reset the public _example profile to its empty learned-rule baseline."""

from __future__ import annotations

import argparse
import os
import stat
import tempfile
from pathlib import Path

try:
    import learned_rules
except ModuleNotFoundError:  # Imported as ``scripts.reset_demo`` in tests.
    from scripts import learned_rules


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "references" / "demo-data" / "example-profile-baseline.yaml"
TARGET = ROOT / "sellers" / "_example" / "profile.yaml"


def validate_reset_paths(
    root: Path, source: Path, target: Path
) -> tuple[Path, dict[str, Path]]:
    root = Path(root)
    source = Path(source)
    target = Path(target)
    demo_data_root = root / "references" / "demo-data"
    for path, label in (
        (root, "repository root"),
        (root / "references", "references directory"),
        (demo_data_root, "demo-data directory"),
    ):
        if path.is_symlink() or not path.is_dir():
            raise SystemExit(f"{label} must be a real directory: {path}")
    try:
        demo_data_root.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise SystemExit("demo-data directory escapes repository root.") from exc
    try:
        source = learned_rules.validate_contained_file(
            demo_data_root, source, "demo baseline"
        )
        context = learned_rules.validate_seller_context(root, "_example")
    except learned_rules.RuleValidationError as exc:
        raise SystemExit(f"Unsafe demo reset path: {exc}") from exc
    if target.absolute() != context["profile_path"].absolute():
        raise SystemExit("Reset target must be exactly sellers/_example/profile.yaml.")
    return source, context


def reset_profile(root: Path, source: Path, target: Path) -> None:
    root = Path(root)
    target = Path(target)
    source, context = validate_reset_paths(root, source, target)
    baseline = source.read_text(encoding="utf-8")
    if learned_rules.profile_meta_seller_id(baseline) != "_example":
        raise SystemExit("Demo baseline meta.seller_id must be _example.")

    target_stat = target.lstat()
    fd, temp_name = tempfile.mkstemp(
        prefix=".profile.yaml.reset.", suffix=".tmp", dir=target.parent
    )
    temporary = Path(temp_name)
    try:
        if temporary.is_symlink() or target.parent.is_symlink() or target.is_symlink():
            raise SystemExit("Reset profile/temp path must not be a symlink.")
        os.fchmod(fd, stat.S_IMODE(target_stat.st_mode))
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            fd = -1
            handle.write(baseline)
            handle.flush()
            os.fsync(handle.fileno())
        if temporary.parent.resolve() != target.parent.resolve():
            raise SystemExit("Reset temporary file escaped sellers/_example.")
        if target.parent.is_symlink() or target.is_symlink() or temporary.is_symlink():
            raise SystemExit("Reset path changed to a symlink during update.")
        os.replace(temporary, target)
    finally:
        if fd >= 0:
            os.close(fd)
        if temporary.exists() or temporary.is_symlink():
            temporary.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset only sellers/_example/profile.yaml.")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Apply the reset. Without this flag the script is a dry run.",
    )
    args = parser.parse_args()
    validate_reset_paths(ROOT, SOURCE, TARGET)
    if not args.yes:
        print(f"Dry run: would restore {TARGET.relative_to(ROOT)} from {SOURCE.relative_to(ROOT)}")
        return
    reset_profile(ROOT, SOURCE, TARGET)
    print(f"Restored {TARGET.relative_to(ROOT)}; learned rules are empty")


if __name__ == "__main__":
    main()
