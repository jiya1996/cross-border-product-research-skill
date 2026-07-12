#!/usr/bin/env python3
"""Build an atomic public-safe release ZIP from a fail-closed file manifest."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import stat
import subprocess
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

try:
    from scripts import public_release_safety as safety
except ModuleNotFoundError:  # Direct execution puts scripts/ on sys.path.
    import public_release_safety as safety  # type: ignore[no-redef]


ROOT = Path(__file__).resolve().parents[1]
STATIC_MANIFEST_RELATIVE = Path("config/public-release-files.txt")
RESULT_SCHEMA_RELATIVE = Path(
    "evals/product-research/schemas/final-result.schema.json"
)
DEFAULT_OUTPUT = (
    ROOT / "dist" / f"cross-border-product-research-skill-{dt.date.today().isoformat()}.zip"
)

FORBIDDEN_PARTS = {
    ".codex",
    ".git",
    "__pycache__",
    "artifacts",
    "dist",
    "raw",
    "raw-run",
    "workspace",
}
FORBIDDEN_NAMES = {
    ".DS_Store",
    ".env",
    ".env.local",
    "events.jsonl",
    "stderr.log",
}
SAFE_SELLER_PREFIX = "sellers/_example/"
SAFE_SELLER_FILES = {"sellers/.gitkeep"}
SAFE_REPORTS = {
    "reports/.gitkeep",
    "reports/_example/2026-07-06_tiktok-pet-products.md",
    "reports/_example/2026-07-06_tiktok-desk-accessories.md",
}

# Compatibility exports for tests and the evidence exporter.
EVIDENCE_PREFIX = safety.EVIDENCE_PREFIX
EVIDENCE_ROOT_FILES = safety.EVIDENCE_ROOT_FILES
EVIDENCE_CASE_FILES = safety.EVIDENCE_CASE_FILES
SAFE_PATH_COMPONENT = safety.SAFE_COMPONENT_RE
sensitive_content_findings = safety.sensitive_content_findings
sha256 = safety.sha256


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a public-safe Skill release ZIP.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def _fail(message: str) -> None:
    raise SystemExit(message)


def _is_forbidden_release_path(relative: str) -> bool:
    try:
        path = safety.safe_posix_relative_path(relative, label="release path")
    except safety.PublicSafetyError:
        return True
    lowered_parts = {part.casefold() for part in path.parts}
    if lowered_parts & {part.casefold() for part in FORBIDDEN_PARTS}:
        return True
    if path.name in FORBIDDEN_NAMES or path.name.casefold() in {
        name.casefold() for name in FORBIDDEN_NAMES
    }:
        return True
    if path.suffix.casefold() in {".pyc", ".zip"}:
        return True
    if any(part.casefold().startswith(".env") for part in path.parts):
        return True
    return False


def validate_evidence_name(name: str) -> None:
    try:
        safety.validate_evidence_name(name)
    except safety.PublicSafetyError as exc:
        _fail(str(exc))


def read_payload(path: Path) -> bytes:
    """Read one regular file without following its final path component."""

    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        _fail(f"Cannot safely open release file: {path}")
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            _fail(f"Release entry is not a regular file: {path}")
        chunks: list[bytes] = []
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _safe_repo_file(relative: str) -> Path:
    try:
        posix = safety.safe_posix_relative_path(relative, label="release path")
    except safety.PublicSafetyError as exc:
        _fail(str(exc))
    path = ROOT.joinpath(*posix.parts)
    cursor = ROOT
    for part in posix.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            _fail(f"Symlink forbidden in release: {relative}")
    try:
        path.resolve(strict=True).relative_to(ROOT.resolve(strict=True))
    except (OSError, ValueError) as exc:
        _fail(f"Release path escapes repository: {relative}")
    if not path.is_file():
        _fail(f"Release file is missing or not regular: {relative}")
    if read_payload(path) != _git_index_payload(relative):
        _fail(f"Release input differs from the Git index: {relative}")
    return path


def _git_index_payload(relative: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(ROOT), "show", f":{relative}"],
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        _fail(f"Cannot read release input from Git index: {relative}")
    return completed.stdout


def _git_blob_payload(object_id: str, relative: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(ROOT), "cat-file", "blob", object_id],
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        _fail(f"Cannot read immutable Git blob for release input: {relative}")
    return completed.stdout


def _parse_static_manifest(payload: bytes) -> set[str]:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        _fail("Static release manifest must be UTF-8")
    entries: set[str] = set()
    for line_number, raw in enumerate(text.splitlines(), start=1):
        value = raw.strip()
        if not value or value.startswith("#"):
            continue
        try:
            safety.safe_posix_relative_path(
                value, label=f"public-release-files.txt:{line_number}"
            )
        except safety.PublicSafetyError as exc:
            _fail(str(exc))
        if value.startswith(EVIDENCE_PREFIX):
            _fail("Sanitized evidence must be dynamically discovered, not statically listed")
        if _is_forbidden_release_path(value):
            _fail(f"Forbidden path in static release manifest: {value}")
        if value in entries:
            _fail(f"Duplicate static release manifest entry: {value}")
        entries.add(value)
    manifest_relative = STATIC_MANIFEST_RELATIVE.as_posix()
    if manifest_relative not in entries:
        _fail(f"Static release manifest must list itself: {manifest_relative}")
    return entries


def load_static_manifest() -> set[str]:
    manifest_path = ROOT / STATIC_MANIFEST_RELATIVE
    if not manifest_path.is_file() or manifest_path.is_symlink():
        _fail("Missing safe static release manifest: config/public-release-files.txt")
    return _parse_static_manifest(_git_index_payload(STATIC_MANIFEST_RELATIVE.as_posix()))


def _tracked_paths() -> set[str]:
    completed = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z", "--cached"],
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        _fail(f"Cannot read Git index for release build: {detail}")
    result: set[str] = set()
    for raw in completed.stdout.split(b"\0"):
        if not raw:
            continue
        value = os.fsdecode(raw)
        try:
            safety.safe_posix_relative_path(value, label="tracked release path")
        except safety.PublicSafetyError as exc:
            _fail(str(exc))
        if value in result:
            _fail(f"Duplicate tracked release path: {value}")
        result.add(value)
    return result


def _tracked_index_entries() -> dict[str, tuple[str, str]]:
    completed = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-s", "-z", "--cached"],
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        _fail(f"Cannot snapshot Git index for release build: {detail}")
    entries: dict[str, tuple[str, str]] = {}
    for raw in completed.stdout.split(b"\0"):
        if not raw:
            continue
        try:
            metadata, raw_path = raw.split(b"\t", 1)
            mode, object_id, stage = metadata.decode("ascii").split()
            relative = os.fsdecode(raw_path)
        except (ValueError, UnicodeDecodeError) as exc:
            _fail("Malformed Git index entry during release snapshot")
        if stage != "0" or relative in entries:
            _fail(f"Unmerged or duplicate Git index entry: {relative}")
        try:
            safety.safe_posix_relative_path(relative, label="tracked release path")
        except safety.PublicSafetyError as exc:
            _fail(str(exc))
        entries[relative] = (mode, object_id)
    return entries


def _selected_index_entries() -> dict[str, tuple[str, str]]:
    entries = _tracked_index_entries()
    manifest_relative = STATIC_MANIFEST_RELATIVE.as_posix()
    manifest_entry = entries.get(manifest_relative)
    if manifest_entry is None or manifest_entry[0] not in {"100644", "100755"}:
        _fail("Static release manifest is absent or not a regular Git blob")
    static_entries = _parse_static_manifest(
        _git_blob_payload(manifest_entry[1], manifest_relative)
    )
    for relative in entries:
        if _is_forbidden_release_path(relative):
            _fail(f"Forbidden tracked path in public repository: {relative}")
    evidence_entries = {
        path for path in entries if path.startswith(EVIDENCE_PREFIX)
    }
    for relative in evidence_entries:
        validate_evidence_name(relative)
    missing = sorted(static_entries - set(entries))
    if missing:
        _fail("Static public release manifest lists untracked files: " + ", ".join(missing))
    selected_names = static_entries | evidence_entries
    selected: dict[str, tuple[str, str]] = {}
    for relative in selected_names:
        mode, object_id = entries[relative]
        if mode not in {"100644", "100755"}:
            _fail(f"Release input is not a regular Git blob: {relative}")
        selected[relative] = (mode, object_id)
    return selected


def allowed(relative: Path) -> bool:
    """Return whether a path is explicitly static or validated evidence-shaped."""

    value = relative.as_posix()
    if _is_forbidden_release_path(value):
        return False
    if value.startswith(EVIDENCE_PREFIX):
        try:
            safety.validate_evidence_name(value)
        except safety.PublicSafetyError:
            return False
        return True
    return value in load_static_manifest()


def release_files() -> list[Path]:
    """Return the exact tracked manifest plus dynamic sanitized evidence files."""

    static_entries = load_static_manifest()
    tracked = _tracked_paths()
    for relative in tracked:
        if _is_forbidden_release_path(relative):
            _fail(f"Forbidden tracked path in public repository: {relative}")

    evidence_entries = {path for path in tracked if path.startswith(EVIDENCE_PREFIX)}
    for relative in evidence_entries:
        validate_evidence_name(relative)
    tracked_static = tracked - evidence_entries
    missing = sorted(static_entries - tracked_static)
    if missing:
        _fail("Static public release manifest lists untracked files: " + ", ".join(missing))

    selected = static_entries | evidence_entries
    files = [_safe_repo_file(relative) for relative in sorted(selected)]
    return files


def release_payloads() -> list[tuple[Path, bytes]]:
    """Snapshot immutable staged blobs; ZIP generation never rereads the worktree."""

    selected = _selected_index_entries()
    return [
        (ROOT / relative, _git_blob_payload(object_id, relative))
        for relative, (_, object_id) in sorted(selected.items())
    ]


def validate_names(names: list[str]) -> None:
    for name in names:
        try:
            safety.safe_posix_relative_path(name, label="release archive name")
        except safety.PublicSafetyError as exc:
            _fail(str(exc))
        if _is_forbidden_release_path(name):
            _fail(f"Forbidden path in release: {name}")
        if (
            name.startswith("sellers/")
            and name not in SAFE_SELLER_FILES
            and not name.startswith(SAFE_SELLER_PREFIX)
        ):
            _fail(f"Unsafe seller path in release: {name}")
        if name.startswith("reports/") and name not in SAFE_REPORTS:
            _fail(f"Unsafe report path in release: {name}")
        if name.startswith(EVIDENCE_PREFIX):
            validate_evidence_name(name)


def validate_content(payloads: list[tuple[Path, bytes]]) -> None:
    for path, payload in payloads:
        try:
            relative = path.relative_to(ROOT).as_posix()
        except ValueError:
            relative = str(path)
        try:
            safety.validate_sensitive_payload(payload, relative)
        except safety.PublicSafetyError as exc:
            _fail(str(exc))


def validate_evidence_json_contract(name: str, value: object) -> None:
    """Compatibility helper used by focused unit tests."""

    try:
        safety._validate_no_raw_fields(value, name)
        if name.endswith("/command-audit.json"):
            safety._validate_command_audit(value, name)
        if name.endswith("/tool-calls.json"):
            safety._validate_tool_calls(value, name)
    except safety.PublicSafetyError as exc:
        _fail(str(exc))


def validate_sanitized_evidence_bundles(
    payloads: list[tuple[Path, bytes]],
    *,
    result_schema_payload: bytes | None = None,
) -> None:
    try:
        grouped = safety.group_evidence_payloads(ROOT, payloads)
        if not grouped:
            return
        schema_payload = result_schema_payload
        if schema_payload is None:
            schema_name = RESULT_SCHEMA_RELATIVE.as_posix()
            schema_payload = next(
                (
                    payload
                    for path, payload in payloads
                    if path.relative_to(ROOT).as_posix() == schema_name
                ),
                None,
            )
        if schema_payload is None:
            _fail("Release snapshot is missing final-result.schema.json")
        for run_id, bundle in grouped.items():
            safety.validate_evidence_bundle(
                run_id,
                bundle,
                result_schema_payload=schema_payload,
                repo_root=ROOT,
            )
    except safety.PublicSafetyError as exc:
        _fail(str(exc))


def _release_manifest(payloads: list[tuple[Path, bytes]]) -> bytes:
    entries = [
        {
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": sha256(payload),
        }
        for path, payload in payloads
    ]
    manifest = {
        "release_date": dt.date.today().isoformat(),
        "entry_count": len(entries),
        "safety": (
            "exact static manifest; raw runs and non-manifest files rejected; "
            "only fully validated sanitized eval evidence is dynamic"
        ),
        "entries": entries,
    }
    payload = safety.canonical_json(manifest)
    try:
        safety.validate_sensitive_payload(payload, "RELEASE_MANIFEST.json")
    except safety.PublicSafetyError as exc:
        _fail(str(exc))
    return payload


def _verify_zip(
    archive_path: Path,
    payloads: list[tuple[Path, bytes]],
    release_manifest: bytes,
) -> None:
    expected = {
        path.relative_to(ROOT).as_posix(): sha256(payload) for path, payload in payloads
    }
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        if names.count("RELEASE_MANIFEST.json") != 1:
            _fail("ZIP must contain exactly one release manifest")
        content_names = [name for name in names if name != "RELEASE_MANIFEST.json"]
        validate_names(content_names)
        if len(content_names) != len(set(content_names)) or set(content_names) != set(expected):
            _fail("ZIP entries do not match release inputs")
        if archive.testzip() is not None:
            _fail("ZIP integrity check failed")
        for name, expected_hash in expected.items():
            if sha256(archive.read(name)) != expected_hash:
                _fail(f"ZIP payload hash mismatch: {name}")
        if archive.read("RELEASE_MANIFEST.json") != release_manifest:
            _fail("ZIP release manifest payload mismatch")


def build_release(output: Path) -> tuple[Path, int]:
    payloads = release_payloads()
    names = [path.relative_to(ROOT).as_posix() for path, _ in payloads]
    validate_names(names)
    validate_content(payloads)
    schema_name = RESULT_SCHEMA_RELATIVE.as_posix()
    schema_payload = next(
        (
            payload
            for path, payload in payloads
            if path.relative_to(ROOT).as_posix() == schema_name
        ),
        None,
    )
    validate_sanitized_evidence_bundles(
        payloads, result_schema_payload=schema_payload
    )

    output = output.expanduser().absolute()
    if output.is_symlink() or (output.exists() and not output.is_file()):
        _fail(f"Unsafe release output path: {output}")
    output_resolved = output.resolve(strict=False)
    for path, _ in payloads:
        same_file = output.exists() and os.path.samefile(output, path)
        if same_file or output_resolved == path.resolve(strict=True):
            _fail(f"Release output aliases an input file: {path.relative_to(ROOT)}")
    output.parent.mkdir(parents=True, exist_ok=True)

    release_manifest = _release_manifest(payloads)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.", suffix=".tmp", dir=output.parent
    )
    temporary = Path(temporary_name)
    try:
        os.close(descriptor)
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path, payload in payloads:
                archive.writestr(path.relative_to(ROOT).as_posix(), payload)
            archive.writestr("RELEASE_MANIFEST.json", release_manifest)
        sync_descriptor = os.open(temporary, os.O_RDONLY)
        try:
            os.fsync(sync_descriptor)
        finally:
            os.close(sync_descriptor)
        _verify_zip(temporary, payloads, release_manifest)
        os.replace(temporary, output)
    except BaseException:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise
    return output.resolve(strict=True), len(payloads)


def main() -> None:
    args = parse_args()
    output, count = build_release(args.output)
    print(f"Built {output}")
    print(f"Files: {count}")


if __name__ == "__main__":
    main()
