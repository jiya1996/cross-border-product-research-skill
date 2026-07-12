#!/usr/bin/env python3
"""Build a public-safe release ZIP from an explicit allowlist."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "dist" / f"cross-border-product-research-skill-{dt.date.today().isoformat()}.zip"

ROOT_FILES = {
    ".gitignore",
    "AGENTS.md",
    "CLAUDE_REVIEW.md",
    "DELIVERY_STATUS.md",
    "README.md",
    "THIRD_PARTY_NOTICES.md",
    "选品记忆Agent执行方案.md",
}
ALLOWED_DIRS = {"config", "skills", "references", "scripts", "tests", "evals"}
SAFE_SELLER_PREFIX = "sellers/_example/"
SAFE_REPORTS = {
    "reports/.gitkeep",
    "reports/_example/2026-07-06_tiktok-pet-products.md",
}
BLOCKED_PARTS = {"artifacts", "__pycache__", ".git", "dist"}
BLOCKED_NAMES = {".env", ".env.local", ".DS_Store"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a public-safe Skill release ZIP.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def allowed(rel: Path) -> bool:
    posix = rel.as_posix()
    if any(part in BLOCKED_PARTS for part in rel.parts):
        return False
    if rel.name in BLOCKED_NAMES or rel.suffix in {".pyc", ".zip"}:
        return False
    if posix in ROOT_FILES or posix in SAFE_REPORTS:
        return True
    if posix.startswith(SAFE_SELLER_PREFIX):
        return True
    return bool(rel.parts and rel.parts[0] in ALLOWED_DIRS)


def release_files() -> list[Path]:
    files = []
    for path in ROOT.rglob("*"):
        if path.is_file() and allowed(path.relative_to(ROOT)):
            files.append(path)
    return sorted(files, key=lambda path: path.relative_to(ROOT).as_posix())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_names(names: list[str]) -> None:
    for name in names:
        if name.startswith("sellers/") and not name.startswith(SAFE_SELLER_PREFIX):
            raise SystemExit(f"Unsafe seller path in release: {name}")
        if name.startswith("reports/") and name not in SAFE_REPORTS:
            raise SystemExit(f"Unsafe report path in release: {name}")
        lowered = name.lower()
        if "/.env" in lowered or lowered.startswith(".env") or "artifacts/" in lowered:
            raise SystemExit(f"Sensitive or generated path in release: {name}")


def main() -> None:
    args = parse_args()
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    files = release_files()
    entries = [
        {
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": sha256(path),
        }
        for path in files
    ]
    validate_names([entry["path"] for entry in entries])
    manifest = {
        "release_date": dt.date.today().isoformat(),
        "entry_count": len(entries),
        "safety": "allowlist only; real sellers, generated reports, eval artifacts and secrets excluded",
        "entries": entries,
    }
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(ROOT).as_posix())
        archive.writestr(
            "RELEASE_MANIFEST.json",
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        )
    with zipfile.ZipFile(output) as archive:
        validate_names([name for name in archive.namelist() if name != "RELEASE_MANIFEST.json"])
        if archive.testzip() is not None:
            raise SystemExit("ZIP integrity check failed")
    print(f"Built {output}")
    print(f"Files: {len(entries)}")


if __name__ == "__main__":
    main()
