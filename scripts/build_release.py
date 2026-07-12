#!/usr/bin/env python3
"""Build a public-safe release ZIP from an explicit allowlist."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import stat
import subprocess
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
    "reports/_example/2026-07-06_tiktok-desk-accessories.md",
}
BLOCKED_PARTS = {"artifacts", "__pycache__", ".git", ".codex", "dist"}
BLOCKED_NAMES = {".env", ".env.local", ".DS_Store"}
BLOCKED_CONTENT = {
    b"/" + b"Users/": "machine-specific macOS path",
    b"C:" + b"\\Users\\": "machine-specific Windows path",
    b"-----BEGIN " + b"OPENSSH PRIVATE KEY-----": "private key",
    b"-----BEGIN " + b"PRIVATE KEY-----": "private key",
}


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
    """Return only files already present in the Git index and public allowlist."""

    completed = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z", "--cached"],
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise SystemExit(f"Cannot read Git index for release build: {detail}")

    files: list[Path] = []
    root_resolved = ROOT.resolve()
    for raw in completed.stdout.split(b"\0"):
        if not raw:
            continue
        rel = Path(os.fsdecode(raw))
        if not allowed(rel):
            continue
        path = ROOT / rel
        if not path.exists():
            raise SystemExit(f"Tracked release file is missing: {rel.as_posix()}")
        cursor = ROOT
        for part in rel.parts:
            cursor = cursor / part
            if cursor.is_symlink():
                raise SystemExit(f"Symlink forbidden in release: {rel.as_posix()}")
        try:
            path.resolve(strict=True).relative_to(root_resolved)
        except (OSError, ValueError) as exc:
            raise SystemExit(f"Release path escapes repository: {rel.as_posix()}") from exc
        if not path.is_file():
            raise SystemExit(f"Tracked release entry is not a regular file: {rel.as_posix()}")
        files.append(path)
    return sorted(files, key=lambda path: path.relative_to(ROOT).as_posix())


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def read_payload(path: Path) -> bytes:
    """Read one regular file without following a final-component symlink."""

    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise SystemExit(
            f"Cannot safely open release file: {path.relative_to(ROOT)}"
        ) from exc
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise SystemExit(
                f"Release entry is not a regular file: {path.relative_to(ROOT)}"
            )
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            return stream.read()
    finally:
        os.close(descriptor)


def validate_names(names: list[str]) -> None:
    for name in names:
        if name.startswith("sellers/") and not name.startswith(SAFE_SELLER_PREFIX):
            raise SystemExit(f"Unsafe seller path in release: {name}")
        if name.startswith("reports/") and name not in SAFE_REPORTS:
            raise SystemExit(f"Unsafe report path in release: {name}")
        lowered = name.lower()
        if "/.env" in lowered or lowered.startswith(".env") or "artifacts/" in lowered:
            raise SystemExit(f"Sensitive or generated path in release: {name}")


def validate_content(payloads: list[tuple[Path, bytes]]) -> None:
    for path, payload in payloads:
        for marker, label in BLOCKED_CONTENT.items():
            if marker in payload:
                raise SystemExit(
                    f"Unsafe {label} in release file: {path.relative_to(ROOT)}"
                )


def main() -> None:
    args = parse_args()
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    files = release_files()
    payloads = [(path, read_payload(path)) for path in files]
    validate_content(payloads)
    entries = [
        {
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": sha256(payload),
        }
        for path, payload in payloads
    ]
    validate_names([entry["path"] for entry in entries])
    manifest = {
        "release_date": dt.date.today().isoformat(),
        "entry_count": len(entries),
        "safety": "allowlist only; real sellers, generated reports, eval artifacts and secrets excluded",
        "entries": entries,
    }
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path, payload in payloads:
            archive.writestr(path.relative_to(ROOT).as_posix(), payload)
        archive.writestr(
            "RELEASE_MANIFEST.json",
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        )
    with zipfile.ZipFile(output) as archive:
        archive_names = [
            name for name in archive.namelist() if name != "RELEASE_MANIFEST.json"
        ]
        validate_names(archive_names)
        if archive.testzip() is not None:
            raise SystemExit("ZIP integrity check failed")
        expected_hashes = {entry["path"]: entry["sha256"] for entry in entries}
        if set(archive_names) != set(expected_hashes):
            raise SystemExit("ZIP entries do not match release manifest")
        for name, expected_hash in expected_hashes.items():
            if sha256(archive.read(name)) != expected_hash:
                raise SystemExit(f"ZIP payload hash mismatch: {name}")
    print(f"Built {output}")
    print(f"Files: {len(entries)}")


if __name__ == "__main__":
    main()
