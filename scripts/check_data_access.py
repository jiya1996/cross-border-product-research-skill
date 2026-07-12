#!/usr/bin/env python3
"""Report product-research data-access readiness without exposing secrets."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CODEX_HOME = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))


PROVIDERS = {
    "sellersprite": ("SELLERSPRITE_MCP_URL", "SELLERSPRITE_MCP_API_KEY"),
    "sif": ("SIF_MCP_URL", "SIF_MCP_API_KEY"),
    "sorftime": ("SORFTIME_MCP_URL", "SORFTIME_MCP_API_KEY"),
    "lingxing": ("LINGXING_MCP_URL", "LINGXING_MCP_KEY"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check read-only MCP and demo-fixture readiness without printing values."
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument(
        "--require-live",
        action="store_true",
        help="Exit non-zero unless at least one live provider has URL, key and Codex config.",
    )
    return parser.parse_args()


def read_config_text() -> str:
    chunks = []
    for path in [CODEX_HOME / "config.toml", ROOT / ".codex" / "config.toml"]:
        if path.is_file():
            try:
                chunks.append(path.read_text(encoding="utf-8"))
            except OSError:
                continue
    return "\n".join(chunks)


def config_section(name: str, config_text: str) -> str:
    match = re.search(
        rf"(?ms)^\[mcp_servers\.{re.escape(name)}\]\s*$\n(.*?)(?=^\[|\Z)",
        config_text,
    )
    return match.group(1) if match else ""


def provider_status(name: str, url_var: str, key_var: str, config_text: str) -> dict:
    url_present = bool(os.environ.get(url_var))
    key_present = bool(os.environ.get(key_var))
    section = config_section(name, config_text)
    configured = bool(section)
    config_url_present = bool(re.search(r"(?m)^\s*url\s*=", section))
    config_key_binding_present = key_var in section
    ready = configured and config_url_present and key_present and config_key_binding_present
    return {
        "url_env_present": url_present,
        "key_env_present": key_present,
        "codex_config_present": configured,
        "codex_config_url_present": config_url_present,
        "codex_config_key_binding_present": config_key_binding_present,
        "credential_config_ready": ready,
        "live_tool_smoke_tested": False,
        "note": "需要在 Codex /mcp 中确认只读工具并执行一次最小查询" if ready else "未完成本地密钥与 MCP URL/绑定配置",
    }


def build_status() -> dict:
    config_text = read_config_text()
    providers = {
        name: provider_status(name, url_var, key_var, config_text)
        for name, (url_var, key_var) in PROVIDERS.items()
    }
    demo_files = [
        ROOT / "references" / "demo-data" / "tiktok-candidates.md",
        ROOT / "references" / "demo-data" / "demo-assumptions.md",
        ROOT / "references" / "freight.md",
        ROOT / "references" / "platform-fees.md",
    ]
    schema = ROOT / "references" / "schemas" / "candidate-batch.schema.json"
    demo_ready = all(path.is_file() for path in demo_files) and schema.is_file()
    live_ready = any(item["credential_config_ready"] for item in providers.values())
    return {
        "live_mcp": providers,
        "live_credential_config_ready": live_ready,
        "live_query_verified": False,
        "synthetic_demo_ready": demo_ready,
        "candidate_contract": str(schema.relative_to(ROOT)) if schema.is_file() else None,
        "safety": "只检查变量是否存在，不输出 URL、密钥或配置值",
    }


def print_human(status: dict) -> None:
    print("Data access readiness")
    for name, item in status["live_mcp"].items():
        state = "credential-config-ready" if item["credential_config_ready"] else "not-ready"
        print(f"- {name}: {state}; live query not yet verified")
    demo = "ready" if status["synthetic_demo_ready"] else "missing files"
    print(f"- synthetic demo: {demo}")
    print("- values and secrets were not printed")
    if not status["live_credential_config_ready"]:
        print("- next: configure one provider per config/mcp.md, then verify a read-only tool in /mcp")


def main() -> None:
    args = parse_args()
    status = build_status()
    if args.json:
        print(json.dumps(status, ensure_ascii=False, indent=2))
    else:
        print_human(status)
    if args.require_live and not status["live_credential_config_ready"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
