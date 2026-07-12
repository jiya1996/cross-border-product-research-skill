"""Shared fail-closed validation for public releases and sanitized eval evidence."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any


EVIDENCE_PREFIX = "evals/product-research/evidence/"
EVIDENCE_ROOT_FILES = {"manifest.json", "summary.json"}
EVIDENCE_CASE_FILES = {
    "grade.json",
    "result.json",
    "file-changes.json",
    "tool-calls.json",
    "command-audit.json",
    "report.md",
}
EVIDENCE_REQUIRED_CASE_FILES = EVIDENCE_CASE_FILES - {"report.md"}
SAFE_COMPONENT_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
PUBLIC_EVAL_SELLER_ID_RE = re.compile(r"eval-[a-z0-9][a-z0-9._-]*\Z")
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
COMMIT_RE = re.compile(r"[0-9a-f]{40}\Z")

FORBIDDEN_EVIDENCE_JSON_KEYS = {
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

_PATH_MARKERS = {
    b"/" + b"Users/": "machine-specific macOS path",
    b"/" + b"home/": "machine-specific Linux path",
    b"/" + b"root/": "machine-specific root path",
    b"/" + b"Volumes/": "machine-specific mounted-volume path",
    b"/" + b"tmp/": "temporary absolute path",
    b"/private/" + b"tmp/": "temporary absolute path",
    b"/var/" + b"tmp/": "temporary absolute path",
    b"/var/" + b"folders/": "temporary absolute path",
    b"/private/var/" + b"folders/": "temporary absolute path",
}
_WINDOWS_ABSOLUTE_RE = re.compile(
    rb"(?i)(?:^|[\s\"'=:(])(?:[A-Z]:[\\/]+)"
)
_WINDOWS_UNC_RE = re.compile(
    rb"(?i)(?:^|[\s\"'=:(])\\{2,}[A-Za-z0-9._$-]+\\+[^\\\s\"']+"
)
_PEM_RE = re.compile(rb"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----", re.IGNORECASE)
_COMMON_TOKEN_RE = re.compile(
    rb"(?:"
    rb"gh[pousr]_[A-Za-z0-9]{20,}|"
    rb"github_pat_[A-Za-z0-9_]{20,}|"
    rb"glpat-[A-Za-z0-9_-]{20,}|"
    rb"sk-(?:live_|proj-)?[A-Za-z0-9_-]{20,}|"
    rb"xox[baprs]-[A-Za-z0-9-]{20,}|"
    rb"(?:AKIA|ASIA)[A-Z0-9]{16}|"
    rb"AIza[A-Za-z0-9_-]{30,}|"
    rb"ya29\.[A-Za-z0-9_-]{20,}|"
    rb"hf_[A-Za-z0-9]{20,}|"
    rb"npm_[A-Za-z0-9]{20,}|"
    rb"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"
    rb")"
)
_ASSIGNMENT_RE = re.compile(
    rb"(?i)(?:^|[^A-Za-z0-9_])"
    rb"[\"']?(?P<key>[A-Za-z_][A-Za-z0-9_.-]*|api key)[\"']?\s*[:=]\s*"
    rb"(?:(?P<quote>[\"'])(?P<quoted>[^\"'\r\n]*)[\"']|"
    rb"(?P<bare>[^\s,;\]]+))",
    re.MULTILINE,
)
_BEARER_RE = re.compile(rb"(?i)\bbearer\s+([A-Za-z0-9._~+/=${}<>*-]+)")
_AUTHENTICATED_URL_RE = re.compile(
    rb"(?i)https?://(?:[^\s/@:]+):(?:[^\s/@]+)@[^\s/]+"
)
_CREDENTIAL_QUERY_RE = re.compile(
    rb"(?i)https?://[^\s]+[?&]"
    rb"(?:api[_.-]?key|access[_.-]?token|token|secret|password)="
    rb"([^\s&#]+)"
)
_STRICT_PLACEHOLDERS = {
    b"token",
    b"<token>",
    b"<api-key>",
    b"<api_key>",
    b"<secret>",
    b"<password>",
    b"${token}",
    b"${api_key}",
    b"${secret}",
    b"${password}",
    b"replace-with-local-secret",
    b"replace-with-local-token",
    b"redacted",
    b"***redacted***",
}
_NON_LITERAL_KEYWORDS = {b"if", b"for", b"raise", b"return", b"while"}
_SELLER_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_.-])(?:sellers|reports)[/\\]([A-Za-z0-9][A-Za-z0-9._-]*)"
)
_SELLER_FIELD_RE = re.compile(
    r"(?im)(?:^|[,{]\s*|^\s*(?:[-*]\s*)?)"
    r"[\"']?seller_id[\"']?\s*[:=]\s*[\"'`]?"
    r"([A-Za-z0-9][A-Za-z0-9._-]*)"
)


class PublicSafetyError(ValueError):
    """Raised when content cannot be proven safe for a public artifact."""


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant {value}")


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def strict_json_loads(payload: bytes | str, label: str) -> Any:
    try:
        text = payload.decode("utf-8") if isinstance(payload, bytes) else payload
        return json.loads(
            text,
            object_pairs_hook=_unique_pairs,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise PublicSafetyError(f"invalid strict JSON in {label}: {exc}") from exc


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def safe_posix_relative_path(value: str, *, label: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\0" in value:
        raise PublicSafetyError(f"{label} must be a non-empty relative path")
    if "\\" in value:
        raise PublicSafetyError(f"Windows separator forbidden in {label}")
    posix = PurePosixPath(value)
    windows = PureWindowsPath(value)
    if (
        posix.is_absolute()
        or posix.root
        or ".." in posix.parts
        or "." in posix.parts
        or windows.is_absolute()
        or windows.drive
        or windows.root
        or ".." in windows.parts
        or value != posix.as_posix()
    ):
        raise PublicSafetyError(f"unsafe relative path in {label}: {value!r}")
    return posix


def _looks_like_placeholder(value: bytes) -> bool:
    stripped = value.strip()
    lowered = stripped.lower()
    if lowered in _STRICT_PLACEHOLDERS:
        return True
    return (
        re.fullmatch(rb"\$\{[A-Z_][A-Z0-9_]*\}", stripped) is not None
        or re.fullmatch(rb"\$[A-Z_][A-Z0-9_]*", stripped) is not None
    )


def _looks_like_nonliteral_code(value: bytes) -> bool:
    lowered = value.strip().lower()
    return (
        lowered in _NON_LITERAL_KEYWORDS
        or re.fullmatch(rb"[A-Za-z_][A-Za-z0-9_.]*\([^\r\n]*", value.strip())
        is not None
        or re.fullmatch(rb"(?:list|dict|set|tuple)\[[^\r\n]*", lowered) is not None
    )


def _key_parts(value: bytes) -> list[str]:
    decoded = value.decode("ascii", errors="ignore")
    separated = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", decoded)
    lowered = separated.casefold()
    return [part for part in re.split(r"[_.-]+", lowered) if part]


def _is_credential_key(value: bytes) -> bool:
    lowered = value.decode("ascii", errors="ignore").casefold()
    if lowered in {"authorization", "cookie", "api key"}:
        return True
    parts = _key_parts(value)
    if any(part in {"token", "secret", "password"} for part in parts):
        return True
    return any(
        parts[index : index + 2] == ["api", "key"]
        for index in range(max(0, len(parts) - 1))
    )


def _is_environment_reference(key: bytes, value: bytes) -> bool:
    key_parts = _key_parts(key)
    return (
        (key_parts[-1:] == ["env"] or key_parts[-2:] == ["env", "var"])
        and re.fullmatch(rb"[A-Z][A-Z0-9_]*", value.strip()) is not None
    )


def sensitive_content_findings(payload: bytes) -> list[str]:
    findings: list[str] = []
    lowered = payload.lower()
    for marker, label in _PATH_MARKERS.items():
        if marker.lower() in lowered:
            findings.append(label)
    if _WINDOWS_ABSOLUTE_RE.search(payload):
        findings.append("machine-specific Windows path")
    if _WINDOWS_UNC_RE.search(payload):
        findings.append("Windows UNC path")
    if _PEM_RE.search(payload):
        findings.append("private key")
    if _COMMON_TOKEN_RE.search(payload):
        findings.append("common credential token prefix")
    for match in _ASSIGNMENT_RE.finditer(payload):
        key = match.group("key")
        if not _is_credential_key(key):
            continue
        quoted = match.group("quoted")
        value = quoted if quoted is not None else match.group("bare")
        if _looks_like_placeholder(value):
            continue
        if _is_environment_reference(key, value):
            continue
        if quoted is None and _looks_like_nonliteral_code(value):
            continue
        findings.append("credential assignment")
        break
    for match in _BEARER_RE.finditer(payload):
        if not _looks_like_placeholder(match.group(1)):
            findings.append("Bearer " + "credential")
            break
    if _AUTHENTICATED_URL_RE.search(payload):
        findings.append("authenticated URL")
    for match in _CREDENTIAL_QUERY_RE.finditer(payload):
        if not _looks_like_placeholder(match.group(1)):
            findings.append("credential-bearing URL")
            break
    return list(dict.fromkeys(findings))


def validate_sensitive_payload(payload: bytes, label: str) -> None:
    if b"\0" in payload:
        raise PublicSafetyError(f"NUL byte forbidden in {label}")
    findings = sensitive_content_findings(payload)
    if findings:
        raise PublicSafetyError(f"unsafe {', '.join(findings)} in {label}")


def _schema_type_matches(instance: Any, expected: str) -> bool:
    if expected == "null":
        return instance is None
    if expected == "object":
        return isinstance(instance, dict)
    if expected == "array":
        return isinstance(instance, list)
    if expected == "string":
        return isinstance(instance, str)
    if expected == "boolean":
        return isinstance(instance, bool)
    if expected == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if expected == "number":
        return (
            isinstance(instance, (int, float))
            and not isinstance(instance, bool)
            and math.isfinite(instance)
        )
    raise PublicSafetyError(f"unsupported JSON schema type: {expected}")


def validate_json_schema(instance: Any, schema: Any, path: str = "$") -> None:
    if not isinstance(schema, dict):
        raise PublicSafetyError(f"schema node at {path} must be an object")
    expected_type = schema.get("type")
    if expected_type is not None:
        types = expected_type if isinstance(expected_type, list) else [expected_type]
        if not all(isinstance(item, str) for item in types):
            raise PublicSafetyError(f"invalid schema type declaration at {path}")
        if not any(_schema_type_matches(instance, item) for item in types):
            raise PublicSafetyError(f"schema type mismatch at {path}")
    if "enum" in schema and instance not in schema["enum"]:
        raise PublicSafetyError(f"schema enum mismatch at {path}")
    if "const" in schema and instance != schema["const"]:
        raise PublicSafetyError(f"schema const mismatch at {path}")
    if "not" in schema:
        try:
            validate_json_schema(instance, schema["not"], path)
        except PublicSafetyError:
            pass
        else:
            raise PublicSafetyError(f"schema not constraint failed at {path}")

    if isinstance(instance, dict):
        required = schema.get("required", [])
        if not isinstance(required, list) or not all(
            isinstance(item, str) for item in required
        ):
            raise PublicSafetyError(f"invalid required declaration at {path}")
        missing = [item for item in required if item not in instance]
        if missing:
            raise PublicSafetyError(f"schema missing {', '.join(missing)} at {path}")
        properties = schema.get("properties", {})
        if not isinstance(properties, dict):
            raise PublicSafetyError(f"invalid properties declaration at {path}")
        additional = schema.get("additionalProperties", True)
        for key, value in instance.items():
            if key in properties:
                validate_json_schema(value, properties[key], f"{path}.{key}")
            elif additional is False:
                raise PublicSafetyError(f"schema additional property {key!r} at {path}")
            elif isinstance(additional, dict):
                validate_json_schema(value, additional, f"{path}.{key}")

    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            raise PublicSafetyError(f"schema minItems failed at {path}")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            raise PublicSafetyError(f"schema maxItems failed at {path}")
        if schema.get("uniqueItems"):
            encoded = [
                json.dumps(item, sort_keys=True, ensure_ascii=False, allow_nan=False)
                for item in instance
            ]
            if len(encoded) != len(set(encoded)):
                raise PublicSafetyError(f"schema uniqueItems failed at {path}")
        items = schema.get("items")
        if items is not None:
            for index, value in enumerate(instance):
                validate_json_schema(value, items, f"{path}[{index}]")

    if isinstance(instance, str) and "minLength" in schema:
        if len(instance) < schema["minLength"]:
            raise PublicSafetyError(f"schema minLength failed at {path}")
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if not math.isfinite(instance):
            raise PublicSafetyError(f"non-finite number at {path}")
        if "minimum" in schema and instance < schema["minimum"]:
            raise PublicSafetyError(f"schema minimum failed at {path}")
        if "maximum" in schema and instance > schema["maximum"]:
            raise PublicSafetyError(f"schema maximum failed at {path}")


def validate_evidence_name(name: str) -> None:
    path = safe_posix_relative_path(name, label="evidence release path")
    parts = path.parts
    if len(parts) not in {5, 6} or parts[:3] != (
        "evals",
        "product-research",
        "evidence",
    ):
        raise PublicSafetyError(f"invalid sanitized evidence path: {name}")
    if not SAFE_COMPONENT_RE.fullmatch(parts[3]):
        raise PublicSafetyError(f"invalid evidence run id: {name}")
    if len(parts) == 5:
        if parts[4] not in EVIDENCE_ROOT_FILES:
            raise PublicSafetyError(f"unexpected evidence root file: {name}")
        return
    if not SAFE_COMPONENT_RE.fullmatch(parts[4]):
        raise PublicSafetyError(f"invalid evidence case id: {name}")
    if parts[5] not in EVIDENCE_CASE_FILES:
        raise PublicSafetyError(f"unexpected evidence case file: {name}")


def _walk_json(value: Any):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key, child
            yield from _walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_json(child)


def _validate_no_raw_fields(value: Any, label: str) -> None:
    for key, _ in _walk_json(value):
        normalized = key.strip().casefold().replace("-", "_")
        if normalized in FORBIDDEN_EVIDENCE_JSON_KEYS:
            raise PublicSafetyError(f"raw execution field {key!r} forbidden in {label}")


def _validate_string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise PublicSafetyError(f"{label} must be a string list")
    return value


def _validate_command_audit(value: Any, label: str) -> None:
    if not isinstance(value, dict) or set(value) != {"command_execution"}:
        raise PublicSafetyError(f"invalid command audit: {label}")
    execution = value["command_execution"]
    if not isinstance(execution, dict) or set(execution) != {
        "count",
        "hashes",
        "classifications",
        "violations",
    }:
        raise PublicSafetyError(f"invalid command audit fields: {label}")
    count = execution["count"]
    hashes = execution["hashes"]
    classifications = execution["classifications"]
    violations = execution["violations"]
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise PublicSafetyError(f"invalid command count: {label}")
    if not isinstance(hashes, list) or len(hashes) != count or not all(
        isinstance(item, str) and SHA256_RE.fullmatch(item) for item in hashes
    ):
        raise PublicSafetyError(f"invalid command hashes: {label}")
    for items, field in ((classifications, "classifications"), (violations, "violations")):
        if not isinstance(items, list) or not all(
            isinstance(item, str) and SAFE_COMPONENT_RE.fullmatch(item) for item in items
        ):
            raise PublicSafetyError(f"invalid command {field}: {label}")


def _validate_file_changes(value: Any, label: str) -> None:
    if not isinstance(value, dict) or set(value) != {"changed", "unauthorized"}:
        raise PublicSafetyError(f"invalid file changes: {label}")
    for field in ("changed", "unauthorized"):
        for index, item in enumerate(_validate_string_list(value[field], f"{label}.{field}")):
            safe_posix_relative_path(item, label=f"{label}.{field}[{index}]")


def _validate_grade(value: Any, label: str) -> bool:
    if not isinstance(value, dict) or set(value) != {"passed", "errors"}:
        raise PublicSafetyError(f"invalid grade: {label}")
    if not isinstance(value["passed"], bool):
        raise PublicSafetyError(f"grade passed must be boolean: {label}")
    errors = _validate_string_list(value["errors"], f"{label}.errors")
    if value["passed"] != (errors == []):
        raise PublicSafetyError(f"grade passed/errors semantics disagree: {label}")
    return value["passed"]


def _validate_tool_calls(value: Any, label: str) -> None:
    if not isinstance(value, dict) or set(value) != {"structured_external_tool_calls"}:
        raise PublicSafetyError(f"invalid tool calls: {label}")
    _validate_string_list(value["structured_external_tool_calls"], label)


def _validate_result_paths(result: dict[str, Any], case_id: str) -> None:
    seller_id = result["seller_id"]
    report_path = result["report_path"]
    if report_path is not None:
        path = safe_posix_relative_path(report_path, label=f"{case_id}.report_path")
        if seller_id is None or len(path.parts) < 3 or path.parts[:2] != (
            "reports",
            seller_id,
        ):
            raise PublicSafetyError(f"report path is outside seller namespace: {case_id}")
    inputs = result["inputs_read"]
    for field in ("profile", "sop", "policy", "platform_strategy"):
        value = inputs[field]
        if value is not None:
            safe_posix_relative_path(value, label=f"{case_id}.inputs_read.{field}")
    for index, value in enumerate(inputs["decisions"]):
        safe_posix_relative_path(
            value, label=f"{case_id}.inputs_read.decisions[{index}]"
        )


def _validate_commit_exists(repo_root: Path | None, commit: str) -> None:
    if repo_root is None or not (repo_root / ".git").exists():
        return
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", ""),
        "LANG": "C",
        "LC_ALL": "C",
    }
    completed = subprocess.run(
        ["git", "-C", str(repo_root), "cat-file", "-e", f"{commit}^{{commit}}"],
        capture_output=True,
        check=False,
        env=env,
    )
    if completed.returncode != 0:
        raise PublicSafetyError(f"evaluated commit is not present in Git: {commit}")


def _observed_seller_ids(payload: bytes, parsed: Any | None) -> set[str]:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PublicSafetyError("evidence payload must be UTF-8") from exc
    observed = set(_SELLER_PATH_RE.findall(text))
    observed.update(_SELLER_FIELD_RE.findall(text))
    observed.discard("null")
    if parsed is not None:
        for key, value in _walk_json(parsed):
            normalized = key.strip().casefold().replace("-", "_")
            if normalized == "seller_id" and isinstance(value, str):
                observed.add(value)
            elif normalized == "seller_ids" and isinstance(value, list):
                observed.update(item for item in value if isinstance(item, str))
    return observed


def validate_evidence_bundle(
    run_id: str,
    bundle: dict[str, bytes],
    *,
    result_schema_payload: bytes,
    repo_root: Path | None,
) -> None:
    if not SAFE_COMPONENT_RE.fullmatch(run_id):
        raise PublicSafetyError(f"invalid evidence run id: {run_id}")
    required_root = {"manifest.json", "summary.json"}
    if missing := sorted(required_root - set(bundle)):
        raise PublicSafetyError(f"evidence {run_id} missing {', '.join(missing)}")

    parsed: dict[str, Any] = {}
    for name, payload in bundle.items():
        inner = safe_posix_relative_path(name, label=f"{run_id} evidence entry")
        full_name = f"{EVIDENCE_PREFIX}{run_id}/{inner.as_posix()}"
        validate_evidence_name(full_name)
        validate_sensitive_payload(payload, full_name)
        if name.endswith(".json"):
            parsed[name] = strict_json_loads(payload, full_name)
            _validate_no_raw_fields(parsed[name], full_name)

    manifest = parsed.get("manifest.json")
    summary = parsed.get("summary.json")
    if not isinstance(manifest, dict) or not isinstance(summary, dict):
        raise PublicSafetyError(f"evidence roots must be JSON objects: {run_id}")
    expected_manifest_fields = {
        "schema_version",
        "run_id",
        "evaluated_commit",
        "codex_version",
        "case_count",
        "case_ids",
        "command_profile",
        "command_audit_contract",
        "metadata_sources",
        "allowed_seller_ids",
        "file_allowlist",
        "excluded_raw_entries",
        "sanitization_rules",
        "entries",
    }
    expected_summary_fields = {
        "run_id",
        "selected",
        "passed",
        "failed",
        "case_ids",
        "evaluated_commit",
        "codex_version",
        "command_profile",
    }
    if set(manifest) != expected_manifest_fields or set(summary) != expected_summary_fields:
        raise PublicSafetyError(f"unexpected evidence root fields: {run_id}")
    if manifest["schema_version"] != 1 or manifest["run_id"] != run_id:
        raise PublicSafetyError(f"evidence manifest identity mismatch: {run_id}")
    if summary["run_id"] != run_id:
        raise PublicSafetyError(f"evidence summary identity mismatch: {run_id}")
    for field in ("evaluated_commit", "codex_version", "case_ids", "command_profile"):
        if manifest[field] != summary[field]:
            raise PublicSafetyError(f"evidence metadata mismatch for {field}: {run_id}")
    commit = manifest["evaluated_commit"]
    if not isinstance(commit, str) or not COMMIT_RE.fullmatch(commit):
        raise PublicSafetyError(f"invalid evaluated commit: {run_id}")
    _validate_commit_exists(repo_root, commit)
    if not isinstance(manifest["codex_version"], str) or not manifest[
        "codex_version"
    ].strip() or any(character in manifest["codex_version"] for character in "\r\n\0"):
        raise PublicSafetyError(f"invalid Codex version: {run_id}")
    if not isinstance(manifest["command_profile"], str) or not SAFE_COMPONENT_RE.fullmatch(
        manifest["command_profile"]
    ):
        raise PublicSafetyError(f"invalid command profile: {run_id}")

    case_ids = manifest["case_ids"]
    if not isinstance(case_ids, list) or case_ids != sorted(set(case_ids)) or not all(
        isinstance(case_id, str) and SAFE_COMPONENT_RE.fullmatch(case_id)
        for case_id in case_ids
    ):
        raise PublicSafetyError(f"invalid evidence case ids: {run_id}")
    actual_case_ids = sorted(
        {
            PurePosixPath(name).parts[0]
            for name in bundle
            if len(PurePosixPath(name).parts) == 2
        }
    )
    if case_ids != actual_case_ids:
        raise PublicSafetyError(f"evidence case directories mismatch: {run_id}")
    for count_field in ("selected", "passed", "failed"):
        value = summary[count_field]
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise PublicSafetyError(f"invalid summary count {count_field}: {run_id}")
    if (
        summary["selected"] != len(case_ids)
        or summary["passed"] + summary["failed"] != summary["selected"]
        or manifest["case_count"] != summary["selected"]
    ):
        raise PublicSafetyError(f"evidence summary counts mismatch: {run_id}")

    allowed_sellers = manifest["allowed_seller_ids"]
    if not isinstance(allowed_sellers, list) or allowed_sellers != sorted(
        set(allowed_sellers)
    ) or not all(
        isinstance(value, str) and PUBLIC_EVAL_SELLER_ID_RE.fullmatch(value)
        for value in allowed_sellers
    ):
        raise PublicSafetyError(f"invalid public seller allowlist: {run_id}")
    allowed_set = set(allowed_sellers)
    for name, payload in bundle.items():
        unexpected = sorted(_observed_seller_ids(payload, parsed.get(name)) - allowed_set)
        if unexpected:
            raise PublicSafetyError(
                f"non-allowlisted seller_id in {run_id}/{name}: {', '.join(unexpected)}"
            )

    expected_allowlist = {
        "root": sorted(EVIDENCE_ROOT_FILES),
        "per_case": sorted(EVIDENCE_CASE_FILES),
    }
    if manifest["file_allowlist"] != expected_allowlist:
        raise PublicSafetyError(f"evidence file allowlist mismatch: {run_id}")
    expected_audit_contract = {
        "raw_commands_exported": False,
        "raw_output_exported": False,
        "environment_exported": False,
        "published_fields": [
            "count",
            "hashes",
            "classifications",
            "violations",
        ],
    }
    if manifest["command_audit_contract"] != expected_audit_contract:
        raise PublicSafetyError(f"evidence command audit contract mismatch: {run_id}")
    metadata_sources = manifest["metadata_sources"]
    if not isinstance(metadata_sources, dict) or set(metadata_sources) != {
        "evaluated_commit",
        "codex_version",
        "command_profile",
    } or not all(
        value in {"run_metadata", "cli_supplement"}
        for value in metadata_sources.values()
    ):
        raise PublicSafetyError(f"invalid evidence metadata sources: {run_id}")
    _validate_string_list(manifest["excluded_raw_entries"], "excluded_raw_entries")
    _validate_string_list(manifest["sanitization_rules"], "sanitization_rules")

    entries = manifest["entries"]
    if not isinstance(entries, list):
        raise PublicSafetyError(f"evidence manifest entries missing: {run_id}")
    expected_hashes: dict[str, tuple[str, int]] = {}
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256", "bytes"}:
            raise PublicSafetyError(f"invalid evidence manifest entry: {run_id}")
        name = entry["path"]
        digest = entry["sha256"]
        size = entry["bytes"]
        safe_posix_relative_path(name, label=f"{run_id} manifest entry")
        if (
            name == "manifest.json"
            or name in expected_hashes
            or not isinstance(digest, str)
            or not SHA256_RE.fullmatch(digest)
            or not isinstance(size, int)
            or isinstance(size, bool)
            or size < 0
        ):
            raise PublicSafetyError(f"invalid evidence manifest entry: {run_id}")
        expected_hashes[name] = (digest, size)
    if set(expected_hashes) != set(bundle) - {"manifest.json"}:
        raise PublicSafetyError(f"evidence files differ from manifest: {run_id}")
    for name, (digest, size) in expected_hashes.items():
        payload = bundle[name]
        if len(payload) != size or sha256(payload) != digest:
            raise PublicSafetyError(f"evidence hash mismatch: {run_id}/{name}")

    result_schema = strict_json_loads(result_schema_payload, "final-result.schema.json")
    grade_passed = 0
    for case_id in case_ids:
        for required in EVIDENCE_REQUIRED_CASE_FILES:
            if f"{case_id}/{required}" not in bundle:
                raise PublicSafetyError(f"evidence case incomplete: {run_id}/{case_id}")
        grade = parsed[f"{case_id}/grade.json"]
        grade_passed += int(_validate_grade(grade, f"{run_id}/{case_id}/grade.json"))
        _validate_file_changes(
            parsed[f"{case_id}/file-changes.json"],
            f"{run_id}/{case_id}/file-changes.json",
        )
        _validate_tool_calls(
            parsed[f"{case_id}/tool-calls.json"],
            f"{run_id}/{case_id}/tool-calls.json",
        )
        _validate_command_audit(
            parsed[f"{case_id}/command-audit.json"],
            f"{run_id}/{case_id}/command-audit.json",
        )
        result = parsed[f"{case_id}/result.json"]
        validate_json_schema(result, result_schema)
        _validate_result_paths(result, case_id)
        seller_id = result["seller_id"]
        if seller_id is not None and seller_id not in allowed_set:
            raise PublicSafetyError(f"result seller_id is not allowlisted: {case_id}")
        has_report = f"{case_id}/report.md" in bundle
        if (result["report_path"] is not None) != has_report:
            raise PublicSafetyError(f"report presence disagrees with result: {case_id}")
    if grade_passed != summary["passed"]:
        raise PublicSafetyError(f"grade count disagrees with summary: {run_id}")


def group_evidence_payloads(
    root: Path, payloads: list[tuple[Path, bytes]]
) -> dict[str, dict[str, bytes]]:
    grouped: dict[str, dict[str, bytes]] = {}
    for path, payload in payloads:
        try:
            relative = path.relative_to(root).as_posix()
        except ValueError as exc:
            raise PublicSafetyError("release input escapes repository") from exc
        if not relative.startswith(EVIDENCE_PREFIX):
            continue
        validate_evidence_name(relative)
        parts = PurePosixPath(relative).parts
        run_id = parts[3]
        inner = PurePosixPath(*parts[4:]).as_posix()
        if inner in grouped.setdefault(run_id, {}):
            raise PublicSafetyError(f"duplicate evidence entry: {relative}")
        grouped[run_id][inner] = payload
    return grouped
