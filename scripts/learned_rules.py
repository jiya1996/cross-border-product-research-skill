#!/usr/bin/env python3
"""Structured learned-rule kernel for seller profiles.

The repository intentionally has no YAML dependency.  This module therefore
parses and renders only the documented ``learned`` YAML subtree.  Everything
outside that top-level key is preserved byte-for-byte by :func:`replace_rules`.

Rules are data, not prompts: a rule can only match structured candidate tag
IDs and can only add one bounded integer delta to one score dimension.  Rule
``summary`` text is never inspected when applying a rule.
"""

from __future__ import annotations

import ast
import copy
import datetime as dt
import hashlib
import json
import os
import re
import stat
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence


VALID_STATUSES = frozenset({"proposed", "active", "revoked", "expired", "superseded"})
VALID_DIMENSIONS = frozenset({"demand", "competition", "margin", "capability_fit", "risk"})
RULE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{2,127}$")
TAG_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{1,127}$")
SELLER_ID_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_-]{0,63}$")

RULE_FIELDS = (
    "rule_id",
    "version",
    "summary",
    "status",
    "scope",
    "condition_tag_ids",
    "action",
    "evidence",
    "created",
    "confirmed_by",
    "confirmed_at",
    "revoked_by",
    "revoked_at",
    "revoke_reason",
    "expires_at",
    "supersedes",
)
SCOPE_FIELDS = ("platforms", "markets", "categories")
ACTION_FIELDS = ("dimension", "delta")
EVIDENCE_FIELDS = (
    "decision_path",
    "decision_id",
    "session_id",
    "source_report_id",
    "candidate_id",
    "decided_at",
)

DEMO_RULE_ID = "learned_tiktok_same_density_diff_001"
DEMO_CONDITION_TAG_ORDER = ("same_product_density_high", "differentiation_space_low")
DEMO_CONDITION_TAG_IDS = frozenset(DEMO_CONDITION_TAG_ORDER)

# Compatibility bridge for old Chinese decision logs.  The rule engine itself
# sees only the stable IDs on the right-hand side.
DECISION_TAG_ALIASES = {
    "同款过多": "same_product_density_high",
    "同款密度高": "same_product_density_high",
    "差异化不足": "differentiation_space_low",
    "差异化空间小": "differentiation_space_low",
    "红海竞争": "red_ocean_competition",
    "价格竞争": "price_competition",
    "素材记忆点弱": "content_memory_weak",
}

# Decision logs are written by humans and third-party tools, so platform names
# often contain a market or product suffix (for example ``TikTok US`` or
# ``Amazon.com``).  Rules keep their compact platform IDs, while this alias
# layer gives aggregation, runtime evidence validation and score application a
# single comparison rule.
PLATFORM_ID_ALIASES = {
    "1688": "1688",
    "amazon": "amazon",
    "amazon-com": "amazon",
    "dtc": "dtc-seo",
    "dtc-seo": "dtc-seo",
    "reddit": "reddit",
    "seo": "dtc-seo",
    "shein": "shein",
    "tik-tok": "tiktok",
    "tiktok": "tiktok",
    "亚马逊": "amazon",
}
MARKET_ID_ALIASES = {
    "america": "us",
    "united-kingdom": "uk",
    "united-states": "us",
    "united-states-of-america": "us",
    "uk": "uk",
    "us": "us",
    "usa": "us",
    "美国": "us",
    "英国": "uk",
}

_NULLISH = frozenset(
    {
        "",
        "-",
        "none",
        "null",
        "n/a",
        "na",
        "unknown",
        "未知",
        "无",
        "无报告",
        "无（历史复盘）",
        "无(历史复盘)",
    }
)
_FIELD_LABELS = {
    "decision_id": ("决策ID", "decision_id"),
    "session_id": ("决策会话ID", "session_id"),
    "source_report_id": ("来源报告ID", "来源报告", "source_report_id"),
    "candidate_id": ("候选ID", "候选品ID", "candidate_id"),
    "decided_at": ("决策发生日期", "决策日期", "decided_at"),
    "decision": ("用户决定", "decision"),
    "tag_ids": ("归类标签ID", "tag_ids"),
    "tags": ("归类标签", "tags"),
    "platform": ("平台/来源", "platform"),
    "market": ("目标市场", "市场", "market"),
    "category": ("类目", "category"),
    "record_type": ("来源类型", "记录类型", "record_type", "source_type"),
    "event_date": ("复盘事件日期", "event_date"),
}


class RuleValidationError(ValueError):
    """Raised when a learned rule or its YAML subtree violates the v2 schema."""


def _indent(line: str) -> int:
    prefix = line[: len(line) - len(line.lstrip(" \t"))]
    if "\t" in prefix:
        raise RuleValidationError("Tabs are forbidden in the learned YAML block.")
    return len(prefix)


def _split_pair(text: str, line_no: int) -> tuple[str, str]:
    if ":" not in text:
        raise RuleValidationError(f"Expected key: value at learned line {line_no}.")
    key, value = text.split(":", 1)
    key = key.strip()
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
        raise RuleValidationError(f"Invalid learned key {key!r} at line {line_no}.")
    return key, value.strip()


def _inline_items(text: str, line_no: int) -> list[Any]:
    inner = text[1:-1].strip()
    if not inner:
        return []
    parts: list[str] = []
    start = 0
    quote: str | None = None
    escaped = False
    for index, char in enumerate(inner):
        if escaped:
            escaped = False
            continue
        if char == "\\" and quote:
            escaped = True
            continue
        if quote:
            if char == quote:
                quote = None
            continue
        if char in {'"', "'"}:
            quote = char
        elif char == ",":
            parts.append(inner[start:index].strip())
            start = index + 1
    if quote:
        raise RuleValidationError(f"Unterminated quote at learned line {line_no}.")
    parts.append(inner[start:].strip())
    if any(not part for part in parts):
        raise RuleValidationError(f"Empty inline-list item at learned line {line_no}.")
    return [_parse_scalar(part, line_no) for part in parts]


def _parse_scalar(text: str, line_no: int) -> Any:
    if text in {"null", "~"}:
        return None
    if text == "true":
        return True
    if text == "false":
        return False
    if text.startswith("["):
        if not text.endswith("]"):
            raise RuleValidationError(f"Malformed inline list at learned line {line_no}.")
        return _inline_items(text, line_no)
    if text.startswith('"'):
        try:
            value = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuleValidationError(f"Malformed quoted value at learned line {line_no}.") from exc
        if not isinstance(value, str):
            raise RuleValidationError(f"Expected string at learned line {line_no}.")
        return value
    if text.startswith("'"):
        try:
            value = ast.literal_eval(text)
        except (SyntaxError, ValueError) as exc:
            raise RuleValidationError(f"Malformed quoted value at learned line {line_no}.") from exc
        if not isinstance(value, str):
            raise RuleValidationError(f"Expected string at learned line {line_no}.")
        return value
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    if re.fullmatch(r"-?(?:\d+\.\d*|\d*\.\d+)", text):
        return float(text)
    if any(token in text for token in ("{", "}", "&", "*", "!", "|", ">")):
        raise RuleValidationError(f"Unsupported YAML scalar at learned line {line_no}.")
    return text


def _parse_map(tokens: list[tuple[int, str, int]], index: int, indent: int) -> tuple[dict, int]:
    result: dict[str, Any] = {}
    while index < len(tokens):
        current_indent, content, line_no = tokens[index]
        if current_indent < indent:
            break
        if current_indent > indent:
            raise RuleValidationError(f"Unexpected indentation at learned line {line_no}.")
        if content.startswith("-"):
            break
        key, raw_value = _split_pair(content, line_no)
        if key in result:
            raise RuleValidationError(f"Duplicate learned key {key!r} at line {line_no}.")
        index += 1
        if raw_value:
            result[key] = _parse_scalar(raw_value, line_no)
            continue
        if index >= len(tokens) or tokens[index][0] <= indent:
            result[key] = None
            continue
        if tokens[index][0] != indent + 2:
            raise RuleValidationError(f"Nested learned values must use two spaces at line {line_no}.")
        result[key], index = _parse_node(tokens, index, indent + 2)
    return result, index


def _parse_list(tokens: list[tuple[int, str, int]], index: int, indent: int) -> tuple[list, int]:
    result: list[Any] = []
    while index < len(tokens):
        current_indent, content, line_no = tokens[index]
        if current_indent < indent:
            break
        if current_indent > indent:
            raise RuleValidationError(f"Unexpected indentation at learned line {line_no}.")
        if not content.startswith("-"):
            break
        rest = content[1:].strip()
        index += 1
        if not rest:
            if index >= len(tokens) or tokens[index][0] != indent + 2:
                raise RuleValidationError(f"Empty learned list item at line {line_no}.")
            value, index = _parse_node(tokens, index, indent + 2)
            result.append(value)
            continue
        if ":" not in rest:
            result.append(_parse_scalar(rest, line_no))
            continue

        first_key, first_value = _split_pair(rest, line_no)
        if not first_value:
            raise RuleValidationError(
                f"A learned mapping list item must start with a scalar key at line {line_no}."
            )
        item: dict[str, Any] = {first_key: _parse_scalar(first_value, line_no)}
        if index < len(tokens) and tokens[index][0] > indent:
            if tokens[index][0] != indent + 2:
                raise RuleValidationError(f"List mappings must use two spaces at line {line_no}.")
            continuation, index = _parse_map(tokens, index, indent + 2)
            duplicate = set(item) & set(continuation)
            if duplicate:
                raise RuleValidationError(f"Duplicate learned key {sorted(duplicate)[0]!r}.")
            item.update(continuation)
        result.append(item)
    return result, index


def _parse_node(tokens: list[tuple[int, str, int]], index: int, indent: int) -> tuple[Any, int]:
    if index >= len(tokens) or tokens[index][0] != indent:
        raise RuleValidationError("Malformed learned YAML indentation.")
    if tokens[index][1].startswith("-"):
        return _parse_list(tokens, index, indent)
    return _parse_map(tokens, index, indent)


def _learned_span(profile_text: str) -> tuple[list[str], int | None, int | None, str | None]:
    lines = profile_text.splitlines(keepends=True)
    matches: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        if _indent(line) != 0 or line.lstrip().startswith("#"):
            continue
        match = re.fullmatch(r"learned\s*:\s*(.*?)\s*\r?\n?", line)
        if match:
            matches.append((index, match.group(1)))
    if len(matches) > 1:
        raise RuleValidationError("Profile has more than one top-level learned key.")
    if not matches:
        return lines, None, None, None
    start, header_value = matches[0]
    end = start + 1
    while end < len(lines):
        stripped = lines[end].strip()
        if stripped and not stripped.startswith("#") and _indent(lines[end]) == 0:
            break
        if stripped.startswith("#") and _indent(lines[end]) == 0:
            break
        end += 1
    return lines, start, end, header_value


def load_rules(source: str | Path) -> list[dict[str, Any]]:
    """Load and validate the top-level ``learned`` rules from text or a Path.

    Passing a :class:`str` always means profile text; use :class:`Path` for a
    filesystem input.  YAML outside ``learned`` is deliberately not parsed.
    """

    profile_text = source.read_text(encoding="utf-8") if isinstance(source, Path) else source
    if not isinstance(profile_text, str):
        raise TypeError("source must be profile text or pathlib.Path")
    lines, start, end, header_value = _learned_span(profile_text)
    if start is None:
        return []
    if header_value:
        if header_value == "[]":
            return []
        raise RuleValidationError("Top-level learned must be [] or an indented list.")

    tokens: list[tuple[int, str, int]] = []
    assert end is not None
    for index in range(start + 1, end):
        raw = lines[index]
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indentation = _indent(raw)
        if indentation < 2:
            raise RuleValidationError(f"Malformed learned block at profile line {index + 1}.")
        tokens.append((indentation, stripped, index + 1))
    if not tokens:
        raise RuleValidationError("Top-level learned has no list; use learned: [] for no rules.")
    value, next_index = _parse_node(tokens, 0, 2)
    if next_index != len(tokens) or not isinstance(value, list):
        raise RuleValidationError("Top-level learned value must be a list of mappings.")
    return validate_rules(value)


def _quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return _quote(value)
    raise RuleValidationError(f"Cannot render unsupported scalar {type(value).__name__}.")


def _string_list(values: Sequence[str]) -> str:
    return "[" + ", ".join(_quote(item) for item in values) + "]"


def dump_rules(rules: Sequence[Mapping[str, Any]]) -> str:
    """Render validated rules as a deterministic top-level learned YAML block."""

    normalized = validate_rules(rules)
    if not normalized:
        return "learned: []\n"
    lines = ["learned:\n"]
    for rule in normalized:
        lines.extend(
            [
                f"  - rule_id: {_quote(rule['rule_id'])}\n",
                f"    version: {rule['version']}\n",
                f"    summary: {_quote(rule['summary'])}\n",
                f"    status: {_quote(rule['status'])}\n",
                "    scope:\n",
                f"      platforms: {_string_list(rule['scope']['platforms'])}\n",
                f"      markets: {_string_list(rule['scope']['markets'])}\n",
                f"      categories: {_string_list(rule['scope']['categories'])}\n",
                f"    condition_tag_ids: {_string_list(rule['condition_tag_ids'])}\n",
                "    action:\n",
                f"      dimension: {_quote(rule['action']['dimension'])}\n",
                f"      delta: {rule['action']['delta']}\n",
                "    evidence:\n",
            ]
        )
        for evidence in rule["evidence"]:
            lines.append(f"      - decision_path: {_quote(evidence['decision_path'])}\n")
            for field in EVIDENCE_FIELDS[1:]:
                lines.append(f"        {field}: {_scalar(evidence[field])}\n")
        for field in RULE_FIELDS[8:]:
            lines.append(f"    {field}: {_scalar(rule[field])}\n")
    return "".join(lines)


def replace_rules(profile_text: str, rules: Sequence[Mapping[str, Any]]) -> str:
    """Replace only the top-level learned subtree and preserve all other text."""

    if not isinstance(profile_text, str):
        raise TypeError("profile_text must be str")
    block = dump_rules(rules)
    lines, start, end, _ = _learned_span(profile_text)
    if start is None:
        separator = "" if not profile_text or profile_text.endswith("\n") else "\n"
        return profile_text + separator + block
    assert end is not None
    return "".join([*lines[:start], block, *lines[end:]])


def profile_content_hash(profile_text: str) -> str:
    return hashlib.sha256(profile_text.encode("utf-8")).hexdigest()


def profile_meta_seller_id(profile_text: str) -> str:
    """Read the single ``meta.seller_id`` value without parsing arbitrary YAML."""

    in_meta = False
    saw_meta = False
    values: list[str] = []
    for line_no, raw in enumerate(profile_text.splitlines(), start=1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indentation = _indent(raw)
        if indentation == 0:
            if re.fullmatch(r"meta\s*:\s*", stripped):
                if saw_meta:
                    raise RuleValidationError("Profile has more than one top-level meta key.")
                saw_meta = True
                in_meta = True
                continue
            if in_meta:
                break
            continue
        if not in_meta or indentation != 2:
            continue
        match = re.fullmatch(r"seller_id\s*:\s*(.*?)\s*", stripped)
        if not match:
            continue
        raw_value = match.group(1)
        if not raw_value.startswith(("\"", "'")):
            raw_value = raw_value.split("#", 1)[0].strip()
        parsed = _parse_scalar(raw_value, line_no)
        if not isinstance(parsed, str) or not parsed.strip():
            raise RuleValidationError("profile.meta.seller_id must be a non-empty string.")
        values.append(parsed.strip())
    if not saw_meta or len(values) != 1:
        raise RuleValidationError("Profile must contain exactly one meta.seller_id.")
    return values[0]


def validate_seller_context(
    repo_root: Path,
    seller_id: str,
    *,
    require_decisions: bool = True,
) -> dict[str, Path]:
    """Validate one seller's non-aliased file-memory boundary.

    All learned-rule read/write entry points use this guard so a symlink alias
    cannot make seller A operate on seller B's memory, and a copied profile
    cannot silently retain the wrong ``meta.seller_id``.
    """

    if not isinstance(seller_id, str) or not SELLER_ID_RE.fullmatch(seller_id):
        raise RuleValidationError("Invalid seller_id: paths and dots are forbidden.")
    repo_root = Path(repo_root)
    sellers_root = repo_root / "sellers"
    seller_root = sellers_root / seller_id
    profile_path = seller_root / "profile.yaml"
    decisions_path = seller_root / "decisions"
    for path, label in (
        (sellers_root, "sellers directory"),
        (seller_root, "seller root"),
        (profile_path, "profile"),
    ):
        if path.is_symlink():
            raise RuleValidationError(f"{label} must not be a symlink: {path}")
    if not seller_root.is_dir():
        raise RuleValidationError(f"Missing seller root: sellers/{seller_id}")
    if not profile_path.is_file():
        raise RuleValidationError(f"Missing profile: sellers/{seller_id}/profile.yaml")
    profile_id = profile_meta_seller_id(profile_path.read_text(encoding="utf-8"))
    if profile_id != seller_id:
        raise RuleValidationError(
            f"profile.meta.seller_id mismatch: expected {seller_id!r}, found {profile_id!r}."
        )
    if decisions_path.is_symlink():
        raise RuleValidationError(
            f"decisions directory must not be a symlink: sellers/{seller_id}/decisions"
        )
    if require_decisions and not decisions_path.is_dir():
        raise RuleValidationError(
            f"Missing decision directory: sellers/{seller_id}/decisions"
        )
    return {
        "seller_root": seller_root,
        "profile_path": profile_path,
        "decisions_path": decisions_path,
    }


def validate_profile_entry(
    profile_path: Path,
    *,
    decision_dir: Path | None = None,
) -> dict[str, Path]:
    """Infer and validate a standard ``repo/sellers/{id}/profile.yaml`` entry."""

    profile_path = Path(profile_path)
    seller_root = profile_path.parent
    if profile_path.name != "profile.yaml" or seller_root.parent.name != "sellers":
        raise RuleValidationError(
            "profile_path must be repo/sellers/{seller_id}/profile.yaml."
        )
    repo_root = seller_root.parent.parent
    context = validate_seller_context(repo_root, seller_root.name)
    if profile_path.absolute() != context["profile_path"].absolute():
        raise RuleValidationError("profile_path does not match the validated seller profile.")
    if decision_dir is not None and Path(decision_dir).absolute() != context[
        "decisions_path"
    ].absolute():
        raise RuleValidationError("decision_dir does not match the validated seller directory.")
    return context


def save_rules(
    profile_path: Path,
    rules: Sequence[Mapping[str, Any]],
    *,
    expected_hash: str | None = None,
) -> None:
    """Safely and atomically replace a profile's learned subtree.

    The temporary file is created with ``O_EXCL`` under the profile's real
    parent, so a pre-planted fixed-name symlink cannot redirect the write.
    """

    profile_path = Path(profile_path)
    parent = profile_path.parent
    if parent.is_symlink() or not parent.is_dir():
        raise RuleValidationError("Profile parent must be an existing non-symlink directory.")
    if profile_path.is_symlink() or not profile_path.is_file():
        raise RuleValidationError("Profile must be an existing non-symlink file.")

    read_flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        read_fd = os.open(profile_path, read_flags)
    except OSError as exc:
        raise RuleValidationError(f"Cannot safely open profile: {profile_path}") from exc
    try:
        profile_stat = os.fstat(read_fd)
        if not stat.S_ISREG(profile_stat.st_mode):
            raise RuleValidationError("Profile must be a regular file.")
        with os.fdopen(read_fd, "r", encoding="utf-8") as handle:
            read_fd = -1
            current = handle.read()
    finally:
        if read_fd >= 0:
            os.close(read_fd)
    updated = replace_rules(current, rules)
    if expected_hash is not None and profile_content_hash(current) != expected_hash:
        raise RuleValidationError(
            "Profile changed after it was read; refusing to overwrite concurrent edits. Retry."
        )
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{profile_path.name}.learned.", suffix=".tmp", dir=parent
    )
    temporary = Path(temporary_name)
    try:
        if temporary.is_symlink() or temporary.parent.absolute() != parent.absolute():
            raise RuleValidationError("Temporary profile path failed symlink/root validation.")
        os.fchmod(fd, stat.S_IMODE(profile_stat.st_mode))
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            fd = -1
            handle.write(updated)
            handle.flush()
            os.fsync(handle.fileno())
        if temporary.is_symlink() or parent.is_symlink() or profile_path.is_symlink():
            raise RuleValidationError("Profile path changed to a symlink during update.")
        if expected_hash is not None:
            verify_fd = os.open(profile_path, read_flags)
            try:
                with os.fdopen(verify_fd, "r", encoding="utf-8") as handle:
                    verify_fd = -1
                    latest = handle.read()
            finally:
                if verify_fd >= 0:
                    os.close(verify_fd)
            if profile_content_hash(latest) != expected_hash:
                raise RuleValidationError(
                    "Profile changed during update; refusing to overwrite concurrent edits. Retry."
                )
        os.replace(temporary, profile_path)
    finally:
        if fd >= 0:
            os.close(fd)
        if temporary.exists() or temporary.is_symlink():
            temporary.unlink()


def _require_exact_fields(value: Mapping[str, Any], fields: Sequence[str], where: str) -> None:
    missing = set(fields) - set(value)
    extra = set(value) - set(fields)
    if missing or extra:
        pieces = []
        if missing:
            pieces.append(f"missing {sorted(missing)}")
        if extra:
            pieces.append(f"unknown {sorted(extra)}")
        raise RuleValidationError(f"{where}: " + "; ".join(pieces))


def _required_string(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuleValidationError(f"{where} must be a non-empty string.")
    return value.strip()


def _optional_string(value: Any, where: str) -> str | None:
    if value is None:
        return None
    return _required_string(value, where)


def _string_sequence(value: Any, where: str, *, tag_ids: bool = False) -> list[str]:
    if not isinstance(value, list):
        raise RuleValidationError(f"{where} must be a list.")
    normalized = [_required_string(item, f"{where}[]") for item in value]
    if len(normalized) != len(set(normalized)):
        raise RuleValidationError(f"{where} must not contain duplicates.")
    if tag_ids:
        for item in normalized:
            if not TAG_ID_RE.fullmatch(item):
                raise RuleValidationError(f"{where} contains invalid tag ID {item!r}.")
    return normalized


def _parse_iso(value: Any, where: str, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    text = _required_string(value, where)
    try:
        if len(text) == 10:
            dt.date.fromisoformat(text)
        else:
            dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RuleValidationError(f"{where} must be an ISO date or datetime.") from exc
    return text


def _relative_path(value: Any, where: str) -> str:
    text = _required_string(value, where).replace("\\", "/")
    path = PurePosixPath(text)
    if path.is_absolute() or ".." in path.parts:
        raise RuleValidationError(f"{where} must be a safe relative path.")
    return str(path)


def _optional_relative_path(value: Any, where: str) -> str | None:
    if value is None:
        return None
    return _relative_path(value, where)


def validate_rule(rule: Mapping[str, Any]) -> dict[str, Any]:
    """Return a normalized copy of one rule or raise RuleValidationError."""

    if not isinstance(rule, Mapping):
        raise RuleValidationError("Each learned rule must be a mapping.")
    _require_exact_fields(rule, RULE_FIELDS, "learned rule")
    normalized = copy.deepcopy(dict(rule))

    normalized["rule_id"] = _required_string(rule["rule_id"], "rule_id")
    if not RULE_ID_RE.fullmatch(normalized["rule_id"]):
        raise RuleValidationError("rule_id must be a stable lowercase ASCII identifier.")
    if isinstance(rule["version"], bool) or not isinstance(rule["version"], int) or rule["version"] < 1:
        raise RuleValidationError("version must be a positive integer.")
    normalized["version"] = rule["version"]
    normalized["summary"] = _required_string(rule["summary"], "summary")
    normalized["status"] = _required_string(rule["status"], "status")
    if normalized["status"] not in VALID_STATUSES:
        raise RuleValidationError(f"status must be one of {sorted(VALID_STATUSES)}.")

    scope = rule["scope"]
    if not isinstance(scope, Mapping):
        raise RuleValidationError("scope must be a mapping.")
    _require_exact_fields(scope, SCOPE_FIELDS, "scope")
    normalized["scope"] = {
        field: _string_sequence(scope[field], f"scope.{field}") for field in SCOPE_FIELDS
    }

    normalized["condition_tag_ids"] = _string_sequence(
        rule["condition_tag_ids"], "condition_tag_ids", tag_ids=True
    )
    if not normalized["condition_tag_ids"]:
        raise RuleValidationError("condition_tag_ids must contain at least one tag ID.")

    action = rule["action"]
    if not isinstance(action, Mapping):
        raise RuleValidationError("action must be a mapping.")
    _require_exact_fields(action, ACTION_FIELDS, "action")
    dimension = _required_string(action["dimension"], "action.dimension")
    if dimension not in VALID_DIMENSIONS:
        raise RuleValidationError(f"action.dimension must be one of {sorted(VALID_DIMENSIONS)}.")
    delta = action["delta"]
    if isinstance(delta, bool) or not isinstance(delta, int) or delta == 0 or not -5 <= delta <= 5:
        raise RuleValidationError("action.delta must be a non-zero integer from -5 to 5.")
    normalized["action"] = {"dimension": dimension, "delta": delta}

    evidence_items = rule["evidence"]
    if not isinstance(evidence_items, list) or not evidence_items:
        raise RuleValidationError("evidence must be a non-empty list.")
    normalized_evidence = []
    for index, evidence in enumerate(evidence_items):
        where = f"evidence[{index}]"
        if not isinstance(evidence, Mapping):
            raise RuleValidationError(f"{where} must be a mapping.")
        _require_exact_fields(evidence, EVIDENCE_FIELDS, where)
        item = {
            "decision_path": _relative_path(evidence["decision_path"], f"{where}.decision_path"),
            "decision_id": _required_string(evidence["decision_id"], f"{where}.decision_id"),
            "session_id": _optional_string(evidence["session_id"], f"{where}.session_id"),
            "source_report_id": _optional_relative_path(
                evidence["source_report_id"], f"{where}.source_report_id"
            ),
            "candidate_id": _required_string(evidence["candidate_id"], f"{where}.candidate_id"),
            "decided_at": _parse_iso(
                evidence["decided_at"], f"{where}.decided_at", optional=True
            ),
        }
        if not item["decision_path"].startswith("decisions/"):
            raise RuleValidationError(
                f"{where}.decision_path must be inside the decisions/ directory."
            )
        if item["source_report_id"] is not None and not item["source_report_id"].startswith(
            "reports/"
        ):
            raise RuleValidationError(
                f"{where}.source_report_id must be null or a reports/ relative path."
            )
        normalized_evidence.append(item)
    decision_ids = [item["decision_id"] for item in normalized_evidence]
    if len(decision_ids) != len(set(decision_ids)):
        raise RuleValidationError("evidence decision_id values must be unique within a rule.")
    if len(normalized_evidence) < 3:
        raise RuleValidationError("evidence must contain at least 3 decision records.")
    session_ids = [item["session_id"] for item in normalized_evidence if item["session_id"]]
    if len(set(session_ids)) < 2:
        raise RuleValidationError("evidence must cover at least 2 independent session IDs.")
    normalized["evidence"] = normalized_evidence

    normalized["created"] = _parse_iso(rule["created"], "created")
    for field in ("confirmed_by", "revoked_by", "revoke_reason", "supersedes"):
        normalized[field] = _optional_string(rule[field], field)
    for field in ("confirmed_at", "revoked_at", "expires_at"):
        normalized[field] = _parse_iso(rule[field], field, optional=True)
    if normalized["supersedes"] and not RULE_ID_RE.fullmatch(normalized["supersedes"]):
        raise RuleValidationError("supersedes must be null or a stable rule_id.")
    if normalized["status"] == "proposed" and (
        normalized["confirmed_by"] is not None or normalized["confirmed_at"] is not None
    ):
        raise RuleValidationError("A proposed rule cannot have confirmation audit fields.")
    if normalized["status"] in {"active", "revoked", "expired", "superseded"} and (
        normalized["confirmed_by"] is None or normalized["confirmed_at"] is None
    ):
        raise RuleValidationError(f"A {normalized['status']} rule must retain confirmation audit fields.")
    if normalized["status"] == "revoked" and (
        normalized["revoked_by"] is None
        or normalized["revoked_at"] is None
        or normalized["revoke_reason"] is None
    ):
        raise RuleValidationError("A revoked rule requires revoked_by, revoked_at and revoke_reason.")
    if normalized["status"] == "expired" and normalized["expires_at"] is None:
        raise RuleValidationError("An explicitly expired rule requires expires_at.")
    return normalized


def validate_rules(rules: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Validate a rule collection and its immutable revision graph.

    A proposed successor is deliberately inert: it may point at the currently
    active predecessor without forcing that predecessor to become
    ``superseded``.  Once the successor is confirmed (or later becomes another
    confirmed inactive state), the predecessor must be ``superseded``.  This
    invariant is what lets the confirmer switch both revisions in one atomic
    profile write.
    """

    if isinstance(rules, (str, bytes)) or not isinstance(rules, Sequence):
        raise RuleValidationError("learned must be a sequence of rule mappings.")
    normalized = [validate_rule(rule) for rule in rules]
    ids = [rule["rule_id"] for rule in normalized]
    if len(ids) != len(set(ids)):
        raise RuleValidationError("rule_id values must be unique within learned.")
    by_id = {rule["rule_id"]: rule for rule in normalized}
    superseded_by: dict[str, str] = {}
    for rule in normalized:
        target = rule["supersedes"]
        if target is None:
            continue
        if target == rule["rule_id"]:
            raise RuleValidationError("A rule cannot supersede itself.")
        if target not in by_id:
            raise RuleValidationError(
                f"Rule {rule['rule_id']} supersedes unknown rule_id {target}."
            )
        if target in superseded_by:
            raise RuleValidationError(f"Rule {target} is superseded by more than one rule.")
        superseded_by[target] = rule["rule_id"]

    # Report graph cycles before checking version order. Strictly increasing
    # versions also make a cycle impossible, but an explicit graph error is
    # substantially more useful when a profile was edited by hand.
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(rule_id: str) -> None:
        if rule_id in visiting:
            raise RuleValidationError(f"Supersedes graph contains a cycle at {rule_id}.")
        if rule_id in visited:
            return
        visiting.add(rule_id)
        target = by_id[rule_id]["supersedes"]
        if target is not None:
            visit(target)
        visiting.remove(rule_id)
        visited.add(rule_id)

    for rule_id in by_id:
        visit(rule_id)

    confirmed_successors_by_target: dict[str, str] = {}
    for rule in normalized:
        target_id = rule["supersedes"]
        if target_id is None:
            continue
        predecessor = by_id[target_id]
        if rule["version"] <= predecessor["version"]:
            raise RuleValidationError(
                f"Rule {rule['rule_id']} version must be greater than superseded "
                f"rule {target_id} version."
            )
        if rule["status"] == "proposed":
            if predecessor["status"] != "active":
                raise RuleValidationError(
                    f"Proposed successor {rule['rule_id']} must point to an active predecessor."
                )
        else:
            confirmed_successors_by_target[target_id] = rule["rule_id"]

    for rule in normalized:
        has_confirmed_successor = rule["rule_id"] in confirmed_successors_by_target
        if rule["status"] == "superseded" and not has_confirmed_successor:
            raise RuleValidationError(
                f"Superseded rule {rule['rule_id']} must be referenced by a "
                "non-proposed newer rule."
            )
        if has_confirmed_successor and rule["status"] != "superseded":
            raise RuleValidationError(
                f"Rule {rule['rule_id']} has a non-proposed successor but is not superseded."
            )
    return normalized


def find_rule(rules: Sequence[Mapping[str, Any]], rule_id: str) -> dict[str, Any]:
    """Find a mutable original rule by stable ID; raise ``KeyError`` if absent.

    Validation happens before lookup, but the returned object is deliberately
    the dict in ``rules`` rather than a normalized copy so lifecycle CLIs can
    mutate it and then pass the same collection to :func:`save_rules`.
    """

    validate_rules(rules)
    for rule in rules:
        if rule["rule_id"] == rule_id:
            if not isinstance(rule, dict):
                raise RuleValidationError("find_rule requires mutable rule dictionaries.")
            return rule
    raise KeyError(rule_id)


def _now_datetime(now: dt.date | dt.datetime | str | None) -> dt.datetime:
    if now is None:
        return dt.datetime.now(dt.timezone.utc)
    if isinstance(now, str):
        try:
            if len(now) == 10:
                return dt.datetime.combine(dt.date.fromisoformat(now), dt.time.max, dt.timezone.utc)
            parsed = dt.datetime.fromisoformat(now.replace("Z", "+00:00"))
        except ValueError as exc:
            raise RuleValidationError("now must be an ISO date or datetime.") from exc
    elif isinstance(now, dt.datetime):
        parsed = now
    elif isinstance(now, dt.date):
        return dt.datetime.combine(now, dt.time.max, dt.timezone.utc)
    else:
        raise TypeError("now must be date, datetime, ISO string or None")
    return parsed.replace(tzinfo=parsed.tzinfo or dt.timezone.utc).astimezone(dt.timezone.utc)


def _expiry_datetime(value: str) -> dt.datetime:
    if len(value) == 10:
        return dt.datetime.combine(dt.date.fromisoformat(value), dt.time.max, dt.timezone.utc)
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.replace(tzinfo=parsed.tzinfo or dt.timezone.utc).astimezone(dt.timezone.utc)


def effective_status(rule: Mapping[str, Any], now: dt.date | dt.datetime | str | None = None) -> str:
    """Return status after applying expiry; only ``active`` can affect scores."""

    normalized = validate_rule(rule)
    expires_at = normalized["expires_at"]
    if normalized["status"] in {"proposed", "active"} and expires_at:
        if _expiry_datetime(expires_at) < _now_datetime(now):
            return "expired"
    return normalized["status"]


def active_rules(
    rules: Sequence[Mapping[str, Any]], now: dt.date | dt.datetime | str | None = None
) -> list[dict[str, Any]]:
    """Return validated rules whose effective status is exactly ``active``."""

    return [rule for rule in validate_rules(rules) if effective_status(rule, now) == "active"]


def normalize_platform_id(value: str | None) -> str | None:
    """Normalize a human/tool platform label to a stable comparison ID."""

    if value is None:
        return None
    token = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", value.strip().casefold()).strip("-")
    if not token:
        return None
    if token in PLATFORM_ID_ALIASES:
        return PLATFORM_ID_ALIASES[token]
    # Market/tool suffixes do not change the platform identity. Match the
    # longest aliases first so ``tik-tok-us`` resolves before a shorter token.
    for alias in sorted(PLATFORM_ID_ALIASES, key=len, reverse=True):
        if token.startswith(f"{alias}-"):
            return PLATFORM_ID_ALIASES[alias]
    return token


def normalize_market_id(value: str | None) -> str | None:
    """Normalize a human market label to a stable comparison ID."""

    if value is None:
        return None
    token = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", value.strip().casefold()).strip("-")
    if not token:
        return None
    return MARKET_ID_ALIASES.get(token, token)


def normalize_category_id(value: str | None) -> str | None:
    """Normalize a category label without inferring a broader taxonomy."""

    if value is None:
        return None
    token = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", value.strip().casefold()).strip("-")
    return token or None


def _normalized_scope_matches(
    allowed: Sequence[str],
    actual: str | None,
    normalizer,
) -> bool:
    if not allowed:
        return True
    actual_id = normalizer(actual)
    if actual_id is None:
        return False
    return actual_id in {normalizer(item) for item in allowed}


def _platform_scope_matches(allowed: Sequence[str], actual: str | None) -> bool:
    """Return whether one decision/candidate platform is inside rule scope."""

    return _normalized_scope_matches(allowed, actual, normalize_platform_id)


def _market_scope_matches(allowed: Sequence[str], actual: str | None) -> bool:
    return _normalized_scope_matches(allowed, actual, normalize_market_id)


def _category_scope_matches(allowed: Sequence[str], actual: str | None) -> bool:
    return _normalized_scope_matches(allowed, actual, normalize_category_id)


def _scope_matches(allowed: Sequence[str], actual: str | None) -> bool:
    if not allowed:
        return True
    if actual is None:
        return False
    normalized_actual = actual.strip().casefold()
    return normalized_actual in {item.strip().casefold() for item in allowed}


def apply_rules(
    candidate: Mapping[str, Any],
    scores: Mapping[str, int | float | None],
    rules: Sequence[Mapping[str, Any]],
    platform: str | None,
    market: str | None,
    category: str | None,
    now: dt.date | dt.datetime | str | None = None,
) -> dict[str, Any]:
    """Apply active structured rules and return scores, effects and inactive rules.

    Candidate conditions are read only from ``rule_tag_ids`` (or the legacy
    structured alias ``tag_ids``).  Text fields such as product name, risk
    description and rule summary are intentionally ignored.
    """

    normalized_rules = validate_rules(rules)
    candidate_tags_raw = candidate.get("rule_tag_ids", candidate.get("tag_ids", []))
    candidate_tags = set(_string_sequence(candidate_tags_raw, "candidate.rule_tag_ids", tag_ids=True))
    updated_scores = dict(scores)
    effects: list[dict[str, Any]] = []
    aggregates: list[dict[str, Any]] = []
    inactive: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    matched_by_dimension: dict[str, list[dict[str, Any]]] = {}
    candidate_id = str(candidate.get("candidate_id", candidate.get("id", "unknown")))

    for rule in normalized_rules:
        status = effective_status(rule, now)
        if status != "active":
            inactive.append(
                {
                    "rule_id": rule["rule_id"],
                    "status": status,
                    "reason": "only active rules participate in scoring",
                }
            )
            continue
        scope = rule["scope"]
        if not (
            _platform_scope_matches(scope["platforms"], platform)
            and _market_scope_matches(scope["markets"], market)
            and _category_scope_matches(scope["categories"], category)
        ):
            skipped.append({"rule_id": rule["rule_id"], "reason": "scope_mismatch"})
            continue
        required_tags = set(rule["condition_tag_ids"])
        if not required_tags.issubset(candidate_tags):
            skipped.append({"rule_id": rule["rule_id"], "reason": "condition_not_met"})
            continue
        dimension = rule["action"]["dimension"]
        before = updated_scores.get(dimension)
        if before is None or isinstance(before, bool) or not isinstance(before, (int, float)):
            skipped.append({"rule_id": rule["rule_id"], "reason": "score_unavailable"})
            continue
        matched_by_dimension.setdefault(dimension, []).append(rule)

    for dimension in sorted(matched_by_dimension):
        matched_rules = matched_by_dimension[dimension]
        before = updated_scores[dimension]
        aggregate_delta = sum(rule["action"]["delta"] for rule in matched_rules)
        after = max(0, min(5, before + aggregate_delta))
        updated_scores[dimension] = after
        rule_ids = sorted(rule["rule_id"] for rule in matched_rules)
        aggregates.append(
            {
                "dimension": dimension,
                "rule_ids": rule_ids,
                "total_delta": aggregate_delta,
                "before": before,
                "after": after,
            }
        )
        # Per-rule effects remain independently auditable. Their after value is
        # the isolated one-rule result; the actual final dimension result lives
        # in ``aggregates`` and clamps only once after summing every delta.
        for rule in sorted(matched_rules, key=lambda item: item["rule_id"]):
            isolated_after = max(0, min(5, before + rule["action"]["delta"]))
            effects.append(
                {
                    "rule_id": rule["rule_id"],
                    "candidate_id": candidate_id,
                    "dimension": dimension,
                    "delta": rule["action"]["delta"],
                    "before": before,
                    "after": isolated_after,
                    "effect_kind": "isolated_contribution",
                    "condition_tag_ids": list(rule["condition_tag_ids"]),
                }
            )
    return {
        "scores": updated_scores,
        "effects": effects,
        "aggregates": aggregates,
        "inactive": inactive,
        "skipped": skipped,
    }


def _field_value(text: str, labels: Sequence[str]) -> str | None:
    label_pattern = "|".join(re.escape(label) for label in labels)
    match = re.search(rf"(?m)^\s*-\s*(?:{label_pattern})\s*:\s*(.*?)\s*$", text)
    if not match:
        return None
    value = match.group(1).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1]
    return value


def _nullable_field(value: str | None) -> str | None:
    if value is None or value.strip().casefold() in _NULLISH:
        return None
    return value.strip()


def _tag_list(value: str | None) -> list[str]:
    if not value:
        return []
    raw = value.strip()
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1]
    tags = [item.strip().strip('"\'') for item in re.split(r"[,，]", raw) if item.strip()]
    return list(dict.fromkeys(tags))


def parse_decision(path: Path) -> dict[str, Any]:
    """Parse a Chinese structured decision Markdown file into stable fields.

    Explicit tag IDs take precedence.  Older Chinese labels are mapped through
    :data:`DECISION_TAG_ALIASES`; unknown prose labels are retained separately
    in ``tags`` and never become executable conditions.
    """

    path = Path(path)
    text = path.read_text(encoding="utf-8")
    heading = re.search(r"(?m)^#\s*(\d{4}-\d{2}-\d{2})\s*\|\s*(.+?)\s*$", text)
    heading_date = heading.group(1) if heading else None
    heading_candidate = heading.group(2).strip() if heading else None

    values = {
        field: _field_value(text, labels) for field, labels in _FIELD_LABELS.items()
    }
    decision_path = path.as_posix()
    marker = "/decisions/"
    if marker in decision_path:
        decision_path = "decisions/" + decision_path.split(marker, 1)[1]
    elif not decision_path.startswith("decisions/"):
        decision_path = f"decisions/{path.name}"

    record_type = (
        _nullable_field(values["record_type"]) or "recommendation_review"
    ).casefold()
    session_id = _nullable_field(values["session_id"])
    has_explicit_date_field = values["decided_at"] is not None or values["event_date"] is not None
    if has_explicit_date_field:
        decided_at = _nullable_field(values["decided_at"]) or _nullable_field(
            values["event_date"]
        )
    else:
        decided_at = heading_date
    if decided_at is None and not has_explicit_date_field:
        stem_match = re.match(r"(\d{4}-\d{2}-\d{2})", path.stem)
        decided_at = stem_match.group(1) if stem_match else None
    if decided_at is None and not (
        record_type == "historical_retrospective" and session_id is not None
    ):
        raise RuleValidationError(f"Decision {path.name} has no decision/event date.")
    decided_at = _parse_iso(decided_at, f"{path.name}.decided_at", optional=True)

    candidate_id = _nullable_field(values["candidate_id"]) or heading_candidate
    if candidate_id is None:
        candidate_id = re.sub(r"^\d{4}-\d{2}-\d{2}_?", "", path.stem)
    decision_id = _nullable_field(values["decision_id"]) or path.stem
    explicit_tag_ids = _tag_list(values["tag_ids"])
    for tag_id in explicit_tag_ids:
        if not TAG_ID_RE.fullmatch(tag_id):
            raise RuleValidationError(f"Decision {path.name} has invalid tag ID {tag_id!r}.")
    labels = _tag_list(values["tags"])
    legacy_mapped_tag_ids = list(
        dict.fromkeys(DECISION_TAG_ALIASES[tag] for tag in labels if tag in DECISION_TAG_ALIASES)
    )
    tag_ids = list(dict.fromkeys([*explicit_tag_ids, *legacy_mapped_tag_ids]))
    platform = _nullable_field(values["platform"])
    market = _nullable_field(values["market"])
    category = _nullable_field(values["category"])

    return {
        "decision_path": decision_path,
        "decision_id": _required_string(decision_id, f"{path.name}.decision_id"),
        "session_id": session_id,
        "source_report_id": _nullable_field(values["source_report_id"]),
        "candidate_id": _required_string(candidate_id, f"{path.name}.candidate_id"),
        "decided_at": decided_at,
        "decision": (_nullable_field(values["decision"]) or "").casefold(),
        "tag_ids": tag_ids,
        "explicit_tag_ids": explicit_tag_ids,
        "legacy_mapped_tag_ids": legacy_mapped_tag_ids,
        "tags": labels,
        "platform": platform,
        "platform_id": normalize_platform_id(platform),
        "market": market,
        "market_id": normalize_market_id(market),
        "category": category,
        "category_id": normalize_category_id(category),
        "record_type": record_type,
        "has_explicit_decision_id": _nullable_field(values["decision_id"]) is not None,
        "has_explicit_candidate_id": _nullable_field(values["candidate_id"]) is not None,
        "has_explicit_tag_ids": bool(explicit_tag_ids),
    }


def independent_session_key(record: Mapping[str, Any]) -> str:
    """Return an evidence-independence key from report/date or retrospective fallback.

    This permits a historical retrospective with no source report to count as
    a distinct session when it provides either an explicit session ID or a
    real event date. Normal report feedback is independent only when its source
    report or decision date differs; changing only a handwritten session ID
    cannot manufacture independence.
    """

    session_id = _nullable_field(record.get("session_id") if isinstance(record.get("session_id"), str) else None)
    prefixes = ("session:", "report-date:", "report:", "date:")
    is_persisted_evidence = "record_type" not in record
    if is_persisted_evidence and session_id and session_id.startswith(prefixes):
        return session_id
    source_report_id = _nullable_field(
        record.get("source_report_id") if isinstance(record.get("source_report_id"), str) else None
    )
    date_value = record.get("event_date") or record.get("decided_at")
    date_key: str | None = None
    if isinstance(date_value, str) and date_value:
        parsed = _parse_iso(date_value, "session fallback date")
        assert parsed is not None
        date_key = parsed[:10]
    if source_report_id and date_key:
        return f"report-date:{source_report_id}|{date_key}"
    if source_report_id:
        return f"report:{source_report_id}"
    record_type = str(record.get("record_type") or "").strip().casefold()
    if record_type == "historical_retrospective":
        if session_id:
            return session_id if session_id.startswith("session:") else f"session:{session_id}"
        if date_key:
            return f"date:{date_key}"
    raise RuleValidationError(
        "Normal evidence needs a source report; historical_retrospective needs "
        "an explicit session ID or event/decision date."
    )


def evidence_from_decision(decision: Mapping[str, Any]) -> dict[str, Any]:
    """Project a parsed decision into the exact learned-rule evidence schema."""

    return {
        "decision_path": decision["decision_path"],
        "decision_id": decision["decision_id"],
        "session_id": independent_session_key(decision),
        "source_report_id": decision.get("source_report_id"),
        "candidate_id": decision["candidate_id"],
        "decided_at": decision["decided_at"],
    }


def _safe_child(root: Path, relative: str, where: str) -> Path:
    candidate = (Path(root) / relative).resolve()
    try:
        candidate.relative_to(Path(root).resolve())
    except ValueError as exc:
        raise RuleValidationError(f"{where} escapes its allowed root: {relative}") from exc
    return candidate


def validate_contained_file(root: Path, path: Path, where: str) -> Path:
    """Return one real regular file contained below a non-symlink root."""

    root = Path(root)
    path = Path(path)
    if root.is_symlink() or not root.is_dir():
        raise RuleValidationError(f"{where} root must be a real directory: {root}")
    if path.is_symlink() or not path.is_file():
        raise RuleValidationError(f"{where} must be a real regular file: {path}")
    resolved = path.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise RuleValidationError(f"{where} escapes its allowed root: {path}") from exc
    return resolved


def safe_decision_paths(decision_dir: Path) -> list[Path]:
    """Enumerate top-level decision Markdown without following aliases."""

    decision_dir = Path(decision_dir)
    if decision_dir.is_symlink() or not decision_dir.is_dir():
        raise RuleValidationError(
            f"Decision directory must be a real directory: {decision_dir}"
        )
    return [
        validate_contained_file(decision_dir, path, "decision file")
        for path in sorted(decision_dir.glob("*.md"), key=lambda item: item.name)
    ]


def _decision_evidence_path(seller_root: Path, decision_path: str) -> Path:
    """Resolve evidence strictly below this seller's real decisions directory."""

    relative = PurePosixPath(decision_path)
    if len(relative.parts) < 2 or relative.parts[0] != "decisions":
        raise RuleValidationError(
            f"evidence path must be inside the decisions/ directory: {decision_path}"
        )
    # First prove that the decisions directory itself has not been redirected
    # outside the seller root, then resolve the evidence below that narrower
    # root. This rejects a decisions/link.md symlink into seller/archive even
    # though the target is still inside the broader seller directory.
    declared_decisions_root = Path(seller_root) / "decisions"
    if declared_decisions_root.is_symlink():
        raise RuleValidationError("decisions directory must not be a symlink.")
    decisions_root = _safe_child(seller_root, "decisions", "decisions directory")
    nested = PurePosixPath(*relative.parts[1:]).as_posix()
    return _safe_child(decisions_root, nested, "evidence path")


def _seller_report_path(
    repo_root: Path,
    seller_id: str,
    source_report_id: str,
) -> Path:
    """Resolve a report only inside ``reports/{seller_id}/``."""

    relative = PurePosixPath(source_report_id)
    expected_prefix = ("reports", seller_id)
    if len(relative.parts) < 3 or tuple(relative.parts[:2]) != expected_prefix:
        raise RuleValidationError(
            f"source_report_id must be inside reports/{seller_id}/: {source_report_id}"
        )
    report_root = Path(repo_root) / "reports" / seller_id
    if report_root.is_symlink():
        raise RuleValidationError(
            f"Seller report namespace must not be a symlink: reports/{seller_id}"
        )
    nested = PurePosixPath(*relative.parts[2:]).as_posix()
    return _safe_child(report_root, nested, "source report path")


def report_candidate_ids(report_path: Path) -> set[str]:
    """Return IDs from Markdown tables that explicitly declare candidate_id.

    Candidate IDs mentioned only in prose, notes or another table column do not
    satisfy source-report integrity.
    """

    lines = Path(report_path).read_text(encoding="utf-8").splitlines()
    candidate_ids: set[str] = set()
    index = 0
    while index < len(lines):
        if not lines[index].lstrip().startswith("|"):
            index += 1
            continue
        block: list[str] = []
        while index < len(lines) and lines[index].lstrip().startswith("|"):
            block.append(lines[index].strip())
            index += 1
        if len(block) < 2:
            continue
        header = [cell.strip().casefold() for cell in block[0].strip("|").split("|")]
        if "candidate_id" not in header:
            continue
        column = header.index("candidate_id")
        for row in block[2:]:
            cells = [cell.strip().strip("`") for cell in row.strip("|").split("|")]
            if len(cells) > column and cells[column] and cells[column] != "-":
                candidate_ids.add(cells[column])
    return candidate_ids


def validate_rule_evidence_files(
    rule: Mapping[str, Any],
    seller_root: Path,
    repo_root: Path,
) -> list[dict[str, Any]]:
    """Re-read evidence and reports before an active rule is trusted.

    This is the runtime counterpart to schema validation. It prevents a manual
    ``status: active`` edit from bypassing rejected-state, explicit-tag,
    session and source-report checks.
    """

    normalized = validate_rule(rule)
    evidence_items = normalized["evidence"]
    decision_paths = [item["decision_path"] for item in evidence_items]
    if len(decision_paths) != len(set(decision_paths)):
        raise RuleValidationError("Evidence decision_path values must be unique.")

    validated: list[dict[str, Any]] = []
    session_keys: set[str] = set()
    required_tags = set(normalized["condition_tag_ids"])
    allowed_platforms = normalized["scope"]["platforms"]
    allowed_markets = normalized["scope"]["markets"]
    allowed_categories = normalized["scope"]["categories"]
    seller_id = Path(seller_root).name
    for evidence in evidence_items:
        relative = evidence["decision_path"]
        evidence_path = _decision_evidence_path(seller_root, relative)
        if not evidence_path.is_file():
            raise RuleValidationError(f"Missing evidence file: {relative}")
        decision = parse_decision(evidence_path)
        for source_report_id in (
            evidence.get("source_report_id"),
            decision.get("source_report_id"),
        ):
            if source_report_id is not None:
                _seller_report_path(repo_root, seller_id, source_report_id)
        if not (
            decision["has_explicit_decision_id"]
            and decision["has_explicit_candidate_id"]
            and decision["has_explicit_tag_ids"]
        ):
            raise RuleValidationError(
                f"Evidence {relative} must contain explicit decision, candidate and tag IDs."
            )

        for field in ("decision_id", "candidate_id", "source_report_id", "decided_at"):
            expected = evidence.get(field)
            actual = decision.get(field)
            if expected != actual:
                raise RuleValidationError(
                    f"Evidence metadata mismatch for {relative}: {field} expected "
                    f"{expected!r}, found {actual!r}."
                )
        if decision["decision"] != "rejected":
            raise RuleValidationError(f"Evidence must be rejected: {relative}")
        if not _platform_scope_matches(allowed_platforms, decision["platform"]):
            platform_id = decision["platform_id"] or "missing"
            raise RuleValidationError(
                f"Evidence {relative} platform {platform_id!r} is outside rule "
                f"scope.platforms {allowed_platforms!r}."
            )
        if not _market_scope_matches(allowed_markets, decision["market"]):
            market_id = decision["market_id"] or "missing"
            raise RuleValidationError(
                f"Evidence {relative} market {market_id!r} is outside rule "
                f"scope.markets {allowed_markets!r}."
            )
        if not _category_scope_matches(allowed_categories, decision["category"]):
            category_id = decision["category_id"] or "missing"
            raise RuleValidationError(
                f"Evidence {relative} category {category_id!r} is outside rule "
                f"scope.categories {allowed_categories!r}."
            )
        explicit_tags = set(decision["explicit_tag_ids"])
        if not required_tags.issubset(explicit_tags):
            missing = ", ".join(sorted(required_tags - explicit_tags))
            raise RuleValidationError(
                f"Evidence {relative} is missing condition tag IDs: {missing}"
            )

        session_key = independent_session_key(decision)
        stored_session_key = independent_session_key(evidence)
        if stored_session_key != session_key:
            raise RuleValidationError(
                f"Evidence metadata mismatch for {relative}: session_id expected "
                f"{stored_session_key!r}, found {session_key!r}."
            )
        session_keys.add(session_key)

        source_report_id = decision["source_report_id"]
        if source_report_id:
            report_path = _seller_report_path(
                repo_root, seller_id, source_report_id
            )
            if not report_path.is_file():
                raise RuleValidationError(f"Missing source report: {source_report_id}")
            report_text = report_path.read_text(encoding="utf-8")
            report_market = _nullable_field(
                _field_value(report_text, _FIELD_LABELS["market"])
            )
            report_category = _nullable_field(
                _field_value(report_text, _FIELD_LABELS["category"])
            )
            if not _market_scope_matches(allowed_markets, report_market):
                raise RuleValidationError(
                    f"Source report {source_report_id} market is missing or outside "
                    f"rule scope.markets {allowed_markets!r}."
                )
            if not _category_scope_matches(allowed_categories, report_category):
                raise RuleValidationError(
                    f"Source report {source_report_id} category is missing or outside "
                    f"rule scope.categories {allowed_categories!r}."
                )
            if decision["candidate_id"] not in report_candidate_ids(report_path):
                raise RuleValidationError(
                    f"Candidate {decision['candidate_id']} from {relative} is absent from "
                    f"source report {source_report_id} candidate_id table."
                )
        elif decision["record_type"] != "historical_retrospective":
            raise RuleValidationError(
                f"Evidence {relative} has no source report; only historical_retrospective "
                "records may omit it."
            )
        validated.append(decision)

    if len(session_keys) < 2:
        raise RuleValidationError(
            "Evidence must cover at least 2 independent sessions after re-validation."
        )
    return validated


def aggregate_demo_rule(
    decision_paths: Iterable[Path],
    *,
    rule_id: str = DEMO_RULE_ID,
    summary: str | None = None,
    condition_tag_ids: Sequence[str] | None = None,
    scope: Mapping[str, Sequence[str]] | None = None,
    action: Mapping[str, Any] | None = None,
    created: str | None = None,
    platform: str = "tiktok",
    market: str | None = None,
    category: str | None = None,
) -> dict[str, Any] | None:
    """Aggregate the bounded demo rule, requiring 3 rejects and 2 sessions.

    The function returns ``None`` when the evidence threshold is not met.  It
    never derives conditions or actions from free-form user text.
    """

    required_tag_list = list(condition_tag_ids or DEMO_CONDITION_TAG_ORDER)
    required_tags = frozenset(required_tag_list)
    if scope is None:
        rule_scope = {
            "platforms": [platform] if platform else [],
            "markets": [market] if market else [],
            "categories": [category] if category else [],
        }
    else:
        if not isinstance(scope, Mapping):
            raise RuleValidationError("scope must be a mapping.")
        _require_exact_fields(scope, SCOPE_FIELDS, "scope")
        rule_scope = {
            field: _string_sequence(scope[field], f"scope.{field}") for field in SCOPE_FIELDS
        }
    qualifying: list[dict[str, Any]] = []
    seen_decisions: set[str] = set()
    seen_paths: set[str] = set()
    for path in sorted((Path(item) for item in decision_paths), key=lambda item: item.as_posix()):
        decision = parse_decision(path)
        if decision["decision"] != "rejected":
            continue
        if not _platform_scope_matches(rule_scope["platforms"], decision["platform"]):
            continue
        if not _market_scope_matches(rule_scope["markets"], decision["market"]):
            continue
        if not _category_scope_matches(rule_scope["categories"], decision["category"]):
            continue
        # Executable evidence must use explicit stable IDs.  parse_decision
        # retains legacy fallbacks for display/migration, but they cannot meet
        # the v2 aggregation gate on their own.
        if not (
            decision["has_explicit_decision_id"]
            and decision["has_explicit_candidate_id"]
            and decision["has_explicit_tag_ids"]
        ):
            continue
        if not required_tags.issubset(set(decision["explicit_tag_ids"])):
            continue
        if decision["decision_id"] in seen_decisions or decision["decision_path"] in seen_paths:
            continue
        seen_decisions.add(decision["decision_id"])
        seen_paths.add(decision["decision_path"])
        qualifying.append(decision)
    if len(qualifying) < 3:
        return None
    if len({independent_session_key(item) for item in qualifying}) < 2:
        return None

    evidence = [evidence_from_decision(item) for item in qualifying]
    created_value = created or dt.date.today().isoformat()
    rule = {
        "rule_id": rule_id,
        "version": 1,
        "summary": summary or "用户多次拒绝同款密度高且差异化空间小的候选，后续降低竞争维度评分。",
        "status": "proposed",
        "scope": rule_scope,
        "condition_tag_ids": required_tag_list,
        "action": dict(action) if action is not None else {"dimension": "competition", "delta": -1},
        "evidence": evidence,
        "created": created_value,
        "confirmed_by": None,
        "confirmed_at": None,
        "revoked_by": None,
        "revoked_at": None,
        "revoke_reason": None,
        "expires_at": None,
        "supersedes": None,
    }
    return validate_rule(rule)
