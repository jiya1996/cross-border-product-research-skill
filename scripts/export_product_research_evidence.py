#!/usr/bin/env python3
"""Export a fail-closed, public-safe subset of one product-research eval run."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Any

try:
    from scripts import public_release_safety as safety
except ModuleNotFoundError:  # Direct execution puts scripts/ rather than repo root on sys.path.
    import public_release_safety as safety  # type: ignore[no-redef]


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_ROOT = ROOT / "evals" / "product-research" / "artifacts"
EVIDENCE_ROOT = ROOT / "evals" / "product-research" / "evidence"

REQUIRED_CASE_FILES = {
    "grade.json",
    "result.json",
    "file-changes.json",
    "tool-calls.json",
    "command-audit.json",
}
EXCLUDED_RAW_ENTRIES = {
    "events.jsonl",
    "stderr.log",
    "workspace/",
    "raw commands",
    "raw stdout/stderr",
    "environment and credentials",
}
MAX_FILE_BYTES = 8 * 1024 * 1024
SAFE_COMPONENT_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
PUBLIC_SELLER_ID_RE = re.compile(r"eval-[a-z0-9][a-z0-9._-]*\Z")
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
COMMIT_RE = re.compile(r"[0-9a-f]{40}\Z", re.IGNORECASE)
SELLER_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_.-])(?:sellers|reports)[/\\]([A-Za-z0-9][A-Za-z0-9._-]*)"
)
SELLER_LINE_RE = re.compile(
    r"(?im)^\s*(?:[-*]\s*)?seller_id\s*[:=]\s*[`\"']?"
    r"([A-Za-z0-9][A-Za-z0-9._-]*)"
)
FORBIDDEN_JSON_KEYS = {
    "args",
    "argv",
    "command",
    "commands",
    "cwd",
    "env",
    "environment",
    "output",
    "outputs",
    "prompt",
    "raw_command",
    "raw_output",
    "stderr",
    "stdin",
    "stdout",
    "workdir",
    "workspace",
}
SANITIZATION_RULES = [
    "export only manifest.json, summary.json, and the per-case file allowlist",
    "never export events, stderr, workspace, raw commands, raw output, or environment",
    "reject repository escape and every symbolic link in the source or destination path",
    "reject machine-specific and temporary absolute paths",
    "reject credentials, credential-bearing URLs, PEM private keys, and common token prefixes",
    "reject seller_id values and seller or report paths outside the explicit seller allowlist",
    "canonicalize JSON and record SHA-256 for every exported payload",
]


class EvidenceExportError(ValueError):
    """Raised when raw artifacts cannot be proven safe to publish."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export sanitized product-research eval evidence.",
        epilog=(
            "Full-suite seller allowlist: repeat --allowed-seller-id for "
            "eval-content, eval-missing-profile, eval-missing-sop, and "
            "eval-conservative."
        ),
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        required=True,
        help="Direct child of evals/product-research/artifacts to export.",
    )
    parser.add_argument(
        "--allowed-seller-id",
        action="append",
        default=[],
        help="Seller id allowed to appear in public evidence; repeat as needed.",
    )
    parser.add_argument(
        "--evaluated-commit",
        help="Explicit supplement only when run metadata omitted evaluated_commit.",
    )
    parser.add_argument(
        "--codex-version",
        help="Explicit supplement only when run metadata omitted codex_version.",
    )
    parser.add_argument(
        "--command-profile",
        help=(
            "Explicit supplement only when run metadata omitted command_profile; "
            "accepts a JSON value or a plain profile id."
        ),
    )
    return parser.parse_args()


def _json_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise EvidenceExportError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_json(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            payload.decode("utf-8"), object_pairs_hook=_json_no_duplicates
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceExportError(f"invalid UTF-8 JSON in {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise EvidenceExportError(f"JSON root must be an object: {label}")
    return value


def canonical_json(value: Any) -> bytes:
    return safety.canonical_json(value)


def safe_read(path: Path, label: str) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise EvidenceExportError(f"cannot safely open {label}") from exc
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            raise EvidenceExportError(f"not a regular file: {label}")
        if info.st_size > MAX_FILE_BYTES:
            raise EvidenceExportError(f"file exceeds export size limit: {label}")
        payload = bytearray()
        while len(payload) <= MAX_FILE_BYTES:
            chunk = os.read(descriptor, min(1024 * 1024, MAX_FILE_BYTES + 1 - len(payload)))
            if not chunk:
                break
            payload.extend(chunk)
        if len(payload) > MAX_FILE_BYTES:
            raise EvidenceExportError(f"file exceeds export size limit: {label}")
        return bytes(payload)
    finally:
        os.close(descriptor)


def ensure_no_symlinks(path: Path, *, recursive: bool) -> None:
    if path.is_symlink():
        raise EvidenceExportError(f"symbolic link forbidden: {path.name}")
    if not recursive:
        return
    for current, dirnames, filenames in os.walk(path, followlinks=False):
        current_path = Path(current)
        for name in [*dirnames, *filenames]:
            candidate = current_path / name
            if candidate.is_symlink():
                raise EvidenceExportError(
                    f"symbolic link forbidden inside run: {candidate.relative_to(path)}"
                )


def ensure_path_chain_has_no_symlink(root: Path, path: Path) -> None:
    root_resolved = root.resolve(strict=True)
    try:
        relative = path.absolute().relative_to(root.absolute())
    except ValueError as exc:
        raise EvidenceExportError("destination path escapes repository") from exc
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        if cursor.exists() and cursor.is_symlink():
            raise EvidenceExportError(f"symbolic link forbidden in destination: {part}")
    try:
        existing_parent = path if path.exists() else path.parent
        existing_parent.resolve(strict=True).relative_to(root_resolved)
    except (OSError, ValueError) as exc:
        raise EvidenceExportError("destination path escapes repository") from exc


def ensure_ignored(run_dir: Path) -> None:
    root = ROOT.resolve(strict=True)
    try:
        relative = run_dir.resolve(strict=True).relative_to(root)
    except ValueError as exc:
        raise EvidenceExportError("run directory is outside the repository") from exc
    completed = subprocess.run(
        ["git", "-C", str(root), "check-ignore", "--quiet", "--", relative.as_posix()],
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise EvidenceExportError("run directory is not covered by Git ignore rules")


def resolve_run_dir(requested: Path) -> Path:
    artifacts = ARTIFACTS_ROOT.resolve(strict=True)
    candidate = requested.expanduser()
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    if not candidate.exists() or not candidate.is_dir():
        raise EvidenceExportError("run directory does not exist")
    ensure_path_chain_has_no_symlink(ROOT, ARTIFACTS_ROOT)
    ensure_path_chain_has_no_symlink(ROOT, candidate)
    ensure_no_symlinks(candidate, recursive=True)
    resolved = candidate.resolve(strict=True)
    if resolved.parent != artifacts:
        raise EvidenceExportError("run directory must be a direct artifacts child")
    if not SAFE_COMPONENT_RE.fullmatch(resolved.name):
        raise EvidenceExportError("invalid run id")
    ensure_ignored(resolved)
    return resolved


def validate_allowed_seller_ids(values: list[str]) -> set[str]:
    allowed: set[str] = set()
    for value in values:
        if not PUBLIC_SELLER_ID_RE.fullmatch(value):
            raise EvidenceExportError(f"invalid allowed seller id: {value!r}")
        allowed.add(value)
    return allowed


def iter_json_items(value: Any):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key, child
            yield from iter_json_items(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_json_items(child)


def validate_no_raw_fields(value: Any, label: str) -> None:
    for key, _ in iter_json_items(value):
        normalized = key.strip().casefold().replace("-", "_")
        if normalized in FORBIDDEN_JSON_KEYS:
            raise EvidenceExportError(f"raw execution field {key!r} forbidden in {label}")


def validate_seller_ids(
    payload: bytes,
    label: str,
    allowed_seller_ids: set[str],
    parsed_json: dict[str, Any] | None = None,
) -> None:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise EvidenceExportError(f"evidence must be UTF-8 text: {label}") from exc
    observed: set[str] = set(SELLER_PATH_RE.findall(text))
    observed.update(SELLER_LINE_RE.findall(text))
    if parsed_json is not None:
        for key, value in iter_json_items(parsed_json):
            normalized = key.strip().casefold().replace("-", "_")
            if normalized == "seller_id" and isinstance(value, str):
                observed.add(value)
            elif normalized == "seller_ids" and isinstance(value, list):
                observed.update(item for item in value if isinstance(item, str))
    disallowed = sorted(observed - allowed_seller_ids)
    if disallowed:
        raise EvidenceExportError(
            f"non-allowlisted seller_id in {label}: {', '.join(disallowed)}"
        )


def validate_public_payload(
    payload: bytes,
    label: str,
    allowed_seller_ids: set[str],
    parsed_json: dict[str, Any] | None = None,
) -> None:
    if b"\0" in payload:
        raise EvidenceExportError(f"NUL byte forbidden in evidence: {label}")
    findings = safety.sensitive_content_findings(payload)
    if findings:
        raise EvidenceExportError(
            f"sensitive content in {label}: {', '.join(findings)}"
        )
    validate_seller_ids(payload, label, allowed_seller_ids, parsed_json)
    if parsed_json is not None:
        validate_no_raw_fields(parsed_json, label)


def validate_relative_paths(values: Any, label: str) -> None:
    if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
        raise EvidenceExportError(f"{label} must be a list of relative paths")
    for value in values:
        path = Path(value)
        if path.is_absolute() or ".." in path.parts or not value:
            raise EvidenceExportError(f"unsafe path in {label}")


def validate_grade(value: dict[str, Any]) -> None:
    if set(value) != {"passed", "errors"}:
        raise EvidenceExportError("grade.json contains unexpected fields")
    if not isinstance(value["passed"], bool):
        raise EvidenceExportError("grade.json passed must be boolean")
    if not isinstance(value["errors"], list) or not all(
        isinstance(item, str) for item in value["errors"]
    ):
        raise EvidenceExportError("grade.json errors must be a string list")
    if value["passed"] != (value["errors"] == []):
        raise EvidenceExportError("grade passed/errors semantics disagree")


def validate_file_changes(value: dict[str, Any]) -> None:
    if set(value) != {"changed", "unauthorized"}:
        raise EvidenceExportError("file-changes.json contains unexpected fields")
    validate_relative_paths(value["changed"], "file-changes.changed")
    validate_relative_paths(value["unauthorized"], "file-changes.unauthorized")


def validate_tool_calls(value: dict[str, Any]) -> None:
    if set(value) != {"structured_external_tool_calls"}:
        raise EvidenceExportError("tool-calls.json contains unexpected fields")
    calls = value["structured_external_tool_calls"]
    if not isinstance(calls, list) or not all(isinstance(item, str) for item in calls):
        raise EvidenceExportError("tool-calls.json must contain tool names only")


def validate_command_audit(value: dict[str, Any]) -> None:
    if set(value) != {"command_execution"} or not isinstance(
        value["command_execution"], dict
    ):
        raise EvidenceExportError("command-audit.json has an unexpected contract")
    execution = value["command_execution"]
    expected = {"count", "hashes", "classifications", "violations"}
    if set(execution) != expected:
        raise EvidenceExportError("command-audit.json has unexpected execution fields")
    count = execution["count"]
    hashes = execution["hashes"]
    classifications = execution["classifications"]
    violations = execution["violations"]
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise EvidenceExportError("command execution count must be a non-negative integer")
    if not isinstance(hashes, list) or len(hashes) != count or not all(
        isinstance(item, str) and SHA256_RE.fullmatch(item) for item in hashes
    ):
        raise EvidenceExportError("command hashes must be one SHA-256 per execution")
    if not isinstance(classifications, list) or not all(
        isinstance(item, str) and bool(item.strip()) for item in classifications
    ):
        raise EvidenceExportError("command classifications must be non-empty strings")
    if not isinstance(violations, list) or not all(
        isinstance(item, str) for item in violations
    ):
        raise EvidenceExportError("command violations must be a string list")


def parse_command_profile_argument(raw: str | None) -> Any:
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def merge_run_metadata(summary: dict[str, Any], run_dir: Path) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    embedded = summary.get("metadata")
    if embedded is not None:
        if not isinstance(embedded, dict):
            raise EvidenceExportError("summary metadata must be an object")
        metadata.update(embedded)
    metadata_path = run_dir / "metadata.json"
    if metadata_path.exists():
        raw_metadata = parse_json(safe_read(metadata_path, "metadata.json"), "metadata.json")
        for key, value in raw_metadata.items():
            if key in metadata and metadata[key] != value:
                raise EvidenceExportError(f"conflicting run metadata: {key}")
            metadata[key] = value
    for key in ("evaluated_commit", "codex_version", "command_profile"):
        if key in summary:
            if key in metadata and metadata[key] != summary[key]:
                raise EvidenceExportError(f"conflicting summary metadata: {key}")
            metadata[key] = summary[key]
    return metadata


def resolve_metadata(
    run_metadata: dict[str, Any],
    supplements: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, str]]:
    resolved: dict[str, Any] = {}
    sources: dict[str, str] = {}
    for key in ("evaluated_commit", "codex_version", "command_profile"):
        recorded = run_metadata.get(key)
        supplement = supplements.get(key)
        if recorded is not None and supplement is not None and recorded != supplement:
            raise EvidenceExportError(f"CLI supplement conflicts with run metadata: {key}")
        if recorded is not None:
            resolved[key] = recorded
            sources[key] = "run_metadata"
        elif supplement is not None:
            resolved[key] = supplement
            sources[key] = "cli_supplement"
        else:
            raise EvidenceExportError(f"missing required run metadata: {key}")

    if not isinstance(resolved["evaluated_commit"], str) or not COMMIT_RE.fullmatch(
        resolved["evaluated_commit"]
    ):
        raise EvidenceExportError("evaluated_commit must be a full 40-hex commit")
    resolved["evaluated_commit"] = resolved["evaluated_commit"].lower()
    if not isinstance(resolved["codex_version"], str) or not resolved[
        "codex_version"
    ].strip():
        raise EvidenceExportError("codex_version must be a non-empty string")
    if not isinstance(resolved["command_profile"], str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", resolved["command_profile"]
    ):
        raise EvidenceExportError("command_profile must be a non-empty profile id")
    if len(resolved["codex_version"]) > 200 or any(
        character in resolved["codex_version"] for character in "\r\n\0"
    ):
        raise EvidenceExportError("codex_version contains unsafe text")
    return resolved, sources


def discover_case_ids(run_dir: Path) -> list[str]:
    permitted_root_files = {"summary.json", "metadata.json"}
    case_ids: list[str] = []
    for entry in run_dir.iterdir():
        if entry.is_file():
            if entry.name not in permitted_root_files:
                raise EvidenceExportError(f"unexpected run-root file: {entry.name}")
            continue
        if not entry.is_dir() or not SAFE_COMPONENT_RE.fullmatch(entry.name):
            raise EvidenceExportError(f"unexpected run-root entry: {entry.name}")
        case_ids.append(entry.name)
    return sorted(case_ids)


def load_case_payloads(
    run_dir: Path, case_id: str, allowed_seller_ids: set[str]
) -> tuple[dict[str, bytes], bool]:
    case_dir = run_dir / case_id
    missing = sorted(name for name in REQUIRED_CASE_FILES if not (case_dir / name).is_file())
    if missing:
        raise EvidenceExportError(
            f"{case_id} missing required evidence: {', '.join(missing)}"
        )

    exported: dict[str, bytes] = {}
    parsed: dict[str, dict[str, Any]] = {}
    for name in sorted(REQUIRED_CASE_FILES):
        source = case_dir / name
        raw = safe_read(source, f"{case_id}/{name}")
        value = parse_json(raw, f"{case_id}/{name}")
        validate_public_payload(raw, f"{case_id}/{name}", allowed_seller_ids, value)
        parsed[name] = value
        exported[name] = canonical_json(value)

    validate_grade(parsed["grade.json"])
    validate_file_changes(parsed["file-changes.json"])
    validate_tool_calls(parsed["tool-calls.json"])
    validate_command_audit(parsed["command-audit.json"])

    report_path = parsed["result.json"].get("report_path")
    expects_report = isinstance(report_path, str) and bool(report_path.strip())
    if report_path is not None and not expects_report:
        raise EvidenceExportError(f"{case_id} result report_path has invalid type")
    report_source = case_dir / "report.md"
    if expects_report != report_source.is_file():
        raise EvidenceExportError(
            f"{case_id} report.md presence disagrees with result report_path"
        )
    if expects_report:
        report = safe_read(report_source, f"{case_id}/report.md")
        validate_public_payload(report, f"{case_id}/report.md", allowed_seller_ids)
        try:
            report.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise EvidenceExportError(f"report is not UTF-8: {case_id}") from exc
        exported["report.md"] = report

    return exported, parsed["grade.json"]["passed"]


def load_summary(run_dir: Path) -> tuple[dict[str, Any], bytes]:
    source = run_dir / "summary.json"
    if not source.is_file():
        raise EvidenceExportError("run is missing summary.json")
    payload = safe_read(source, "summary.json")
    return parse_json(payload, "summary.json"), payload


def export_run(
    requested_run_dir: Path,
    *,
    allowed_seller_ids: list[str],
    evaluated_commit: str | None = None,
    codex_version: str | None = None,
    command_profile: Any = None,
) -> Path:
    run_dir = resolve_run_dir(requested_run_dir)
    allowed = validate_allowed_seller_ids(allowed_seller_ids)
    case_ids = discover_case_ids(run_dir)
    if not case_ids:
        raise EvidenceExportError("run contains no case directories")

    raw_summary, raw_summary_payload = load_summary(run_dir)
    validate_public_payload(raw_summary_payload, "summary.json", allowed, raw_summary)
    run_metadata = merge_run_metadata(raw_summary, run_dir)
    metadata, metadata_sources = resolve_metadata(
        run_metadata,
        {
            "evaluated_commit": evaluated_commit,
            "codex_version": codex_version,
            "command_profile": command_profile,
        },
    )

    selected = raw_summary.get("selected")
    passed = raw_summary.get("passed")
    failed = raw_summary.get("failed")
    if not all(
        isinstance(value, int) and not isinstance(value, bool) and value >= 0
        for value in (selected, passed, failed)
    ):
        raise EvidenceExportError("summary counts must be non-negative integers")
    if selected != len(case_ids) or passed + failed != selected:
        raise EvidenceExportError("summary counts disagree with discovered cases")

    payloads: dict[str, bytes] = {}
    grade_passed = 0
    for case_id in case_ids:
        case_payloads, case_passed = load_case_payloads(run_dir, case_id, allowed)
        grade_passed += int(case_passed)
        for name, payload in case_payloads.items():
            relative = f"{case_id}/{name}"
            validate_public_payload(
                payload,
                relative,
                allowed,
                parse_json(payload, relative) if name.endswith(".json") else None,
            )
            payloads[relative] = payload
    if grade_passed != passed:
        raise EvidenceExportError("summary pass count disagrees with case grades")

    sanitized_summary = {
        "run_id": run_dir.name,
        "selected": selected,
        "passed": passed,
        "failed": failed,
        "case_ids": case_ids,
        **metadata,
    }
    summary_payload = canonical_json(sanitized_summary)
    validate_public_payload(summary_payload, "summary.json", allowed, sanitized_summary)
    payloads["summary.json"] = summary_payload

    entries = [
        {
            "path": path,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "bytes": len(payload),
        }
        for path, payload in sorted(payloads.items())
    ]
    manifest = {
        "schema_version": 1,
        "run_id": run_dir.name,
        "evaluated_commit": metadata["evaluated_commit"],
        "codex_version": metadata["codex_version"],
        "case_count": selected,
        "case_ids": case_ids,
        "command_profile": metadata["command_profile"],
        "command_audit_contract": {
            "raw_commands_exported": False,
            "raw_output_exported": False,
            "environment_exported": False,
            "published_fields": [
                "count",
                "hashes",
                "classifications",
                "violations",
            ],
        },
        "metadata_sources": metadata_sources,
        "allowed_seller_ids": sorted(allowed),
        "file_allowlist": {
            "root": sorted(safety.EVIDENCE_ROOT_FILES),
            "per_case": sorted(safety.EVIDENCE_CASE_FILES),
        },
        "excluded_raw_entries": sorted(EXCLUDED_RAW_ENTRIES),
        "sanitization_rules": SANITIZATION_RULES,
        "entries": entries,
    }
    manifest_payload = canonical_json(manifest)
    validate_public_payload(manifest_payload, "manifest.json", allowed, manifest)
    payloads["manifest.json"] = manifest_payload

    schema_path = ROOT / "evals" / "product-research" / "schemas" / "final-result.schema.json"
    schema_payload = safe_read(schema_path, "final-result.schema.json")
    try:
        safety.validate_evidence_bundle(
            run_dir.name,
            payloads,
            result_schema_payload=schema_payload,
            repo_root=ROOT,
        )
    except safety.PublicSafetyError as exc:
        raise EvidenceExportError(str(exc)) from exc

    ensure_path_chain_has_no_symlink(ROOT, EVIDENCE_ROOT)
    EVIDENCE_ROOT.mkdir(parents=True, exist_ok=True)
    ensure_no_symlinks(EVIDENCE_ROOT, recursive=False)
    destination = EVIDENCE_ROOT / run_dir.name
    if destination.exists() or destination.is_symlink():
        raise EvidenceExportError(f"evidence destination already exists: {run_dir.name}")

    temp_dir = Path(tempfile.mkdtemp(prefix=f".{run_dir.name}.", dir=EVIDENCE_ROOT))
    try:
        for relative, payload in sorted(payloads.items()):
            target = temp_dir / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
        ensure_no_symlinks(temp_dir, recursive=True)
        temp_dir.rename(destination)
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise
    return destination


def main() -> None:
    args = parse_args()
    try:
        destination = export_run(
            args.run_dir,
            allowed_seller_ids=args.allowed_seller_id,
            evaluated_commit=args.evaluated_commit,
            codex_version=args.codex_version,
            command_profile=parse_command_profile_argument(args.command_profile),
        )
    except EvidenceExportError as exc:
        raise SystemExit(f"Evidence export refused: {exc}") from exc
    print(f"Exported sanitized evidence to {destination.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
