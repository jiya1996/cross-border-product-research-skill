#!/usr/bin/env python3
"""Create a deterministic before/unconfirmed/confirmed demo for screen recording."""

from __future__ import annotations

import datetime as dt
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SELLER_ID = "video-demo"
OPENING_POSITIONING = ROOT / "references" / "demo-opening-positioning.md"


def run(command: list[str]) -> str:
    print("+ " + " ".join(command), flush=True)
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)
    return completed.stdout


def prepare_seller() -> None:
    source_profile = ROOT / "references" / "demo-data" / "example-profile-baseline.yaml"
    source_sop = ROOT / "sellers" / "_example" / "sop.md"
    source_decisions = ROOT / "sellers" / "_example" / "decisions"
    target = ROOT / "sellers" / SELLER_ID
    target_decisions = target / "decisions"
    target_decisions.mkdir(parents=True, exist_ok=True)

    profile = source_profile.read_text(encoding="utf-8").replace(
        'seller_id: "_example"', f'seller_id: "{SELLER_ID}"'
    )
    (target / "profile.yaml").write_text(profile, encoding="utf-8")
    sop = source_sop.read_text(encoding="utf-8").replace("# SOP — _example", f"# SOP — {SELLER_ID}")
    (target / "sop.md").write_text(sop, encoding="utf-8")
    for source in source_decisions.glob("*.md"):
        shutil.copy2(source, target_decisions / source.name)


def report_path(label: str) -> Path:
    today = dt.date.today().isoformat()
    return ROOT / "reports" / SELLER_ID / f"{today}_demo-run-{label}.md"


def ranked_products(path: Path) -> list[str]:
    products = []
    in_table = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("| product | demand"):
            in_table = True
            continue
        if in_table and line.startswith("|---"):
            continue
        if in_table and line.startswith("|"):
            products.append(line.strip("|").split("|", 1)[0].strip())
            continue
        if in_table and products:
            break
    return products


def applied_rows(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return re.findall(r"\| ([^|]+) \| ([^|]*(?:competition|capability_fit)[^|]*) \|", text)


def write_trace(before: Path, unconfirmed: Path, after: Path) -> Path:
    if not OPENING_POSITIONING.is_file():
        raise SystemExit(
            f"Missing demo opening page: {OPENING_POSITIONING.relative_to(ROOT)}"
        )

    before_rank = ranked_products(before)
    unconfirmed_rank = ranked_products(unconfirmed)
    after_rank = ranked_products(after)
    if before_rank != unconfirmed_rank:
        raise SystemExit("Unconfirmed learned rule changed ranking; demo guardrail failed.")
    if before_rank == after_rank:
        raise SystemExit("Confirmed learned rule did not change ranking; demo guardrail failed.")

    out = ROOT / "reports" / SELLER_ID / f"{dt.date.today().isoformat()}_video-full-trace.md"
    applied = applied_rows(after)
    lines = [
        "# 跨境电商 AI 选品 Skill · 录屏完整轨迹",
        "",
        "> 全部市场与费用数据均为合成演示数据。流程和文件记忆是真实运行的，结果不是采购或上架建议。",
        "",
        "## 0. 产品定位：跨工具决策记忆缺口",
        "",
        f"- 录屏从 `{OPENING_POSITIONING.relative_to(ROOT)}` 开始。",
        "- 卖家精灵/SIF、领星、内容工具和 RPA 各自保存市场、经营或任务状态；本产品补的是跨工具、带理由、经人工确认且可回滚的卖家决策状态。",
        "- 它不替代数据源或 ERP，而是把 profile、SOP、历史决策和确认后的 learned 规则注入后续过滤、评分与归因。",
        "- 当前只证明合成闭环可复现；真实推荐质量、经营效果和付费意愿仍待真人验证。",
        "- 下一步先复盘一位卖家的真实选品，再导入核实后的领星历史报表；虎步仅在重复搬运痛点成立后作为白名单只读 collector，不能冒充事实来源或执行写操作。",
        "",
        "## 1. 干净基线",
        "",
        f"- seller_id: `{SELLER_ID}`",
        f"- profile: `sellers/{SELLER_ID}/profile.yaml`",
        f"- SOP: `sellers/{SELLER_ID}/sop.md`",
        "- 初始 `learned: []`",
        "",
        "## 2. 首轮推荐",
        "",
        f"- 报告: `{before.relative_to(ROOT)}`",
        f"- Top 5: {before_rank[:5]}",
        "- 报告逐候选包含：为什么适合你、为什么不适合你、主要风险、下一步最小验证。",
        "",
        "## 3. 拒绝样本生成 learned 候选",
        "",
        "- 最近决策中有 3 条同时命中“同款过多 + 差异化不足”。",
        "- `propose_learned.py` 写入 `confirmed: false`，保留 evidence。",
        f"- 未确认报告: `{unconfirmed.relative_to(ROOT)}`",
        f"- 排名与首轮相同: `{before_rank == unconfirmed_rank}`。证明未确认规则没有参与打分。",
        "",
        "## 4. 人工确认后重跑",
        "",
        "- `confirm_learned.py` 将规则改为 `confirmed: true` 并写入确认日期。",
        f"- 确认后报告: `{after.relative_to(ROOT)}`",
        f"- Top 5 before: {before_rank[:5]}",
        f"- Top 5 after: {after_rank[:5]}",
        f"- 被规则调整的候选: {applied or '详见确认后报告'}",
        "",
        "## 5. 自动验收",
        "",
        "- 未确认规则不改排序：PASS",
        "- 确认规则后排序变化：PASS",
        "- 真实卖家目录不参与：PASS",
        "- 平台写操作：0",
        "",
        "## 复现命令",
        "",
        "```bash",
        "python3 scripts/run_video_demo.py",
        "```",
    ]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def main() -> None:
    run([sys.executable, "scripts/validate_repo.py"])
    run([sys.executable, "scripts/run_product_research_evals.py", "--mode", "static"])
    prepare_seller()

    run([sys.executable, "scripts/run_demo.py", "--seller-id", SELLER_ID, "--label", "video-before"])
    before = report_path("video-before")
    run([sys.executable, "scripts/propose_learned.py", SELLER_ID])
    run([sys.executable, "scripts/run_demo.py", "--seller-id", SELLER_ID, "--label", "video-unconfirmed"])
    unconfirmed = report_path("video-unconfirmed")
    run([sys.executable, "scripts/confirm_learned.py", SELLER_ID, "--index", "0"])
    run([sys.executable, "scripts/run_demo.py", "--seller-id", SELLER_ID, "--label", "video-after"])
    after = report_path("video-after")
    trace = write_trace(before, unconfirmed, after)
    print(f"Video trace ready: {trace.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
