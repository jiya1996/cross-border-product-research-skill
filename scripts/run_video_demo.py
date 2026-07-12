#!/usr/bin/env python3
"""Create a deterministic before/proposed/active demo for screen recording."""

from __future__ import annotations

import datetime as dt
import re
import subprocess
import sys
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SELLER_PREFIX = "video-demo-"
DEMO_RULE_ID = "learned_tiktok_same_density_diff_001"
OPENING_POSITIONING = ROOT / "references" / "demo-opening-positioning.md"
SOURCE_REPORT_NAMES = (
    "2026-07-06_tiktok-pet-products.md",
    "2026-07-06_tiktok-desk-accessories.md",
)
SOURCE_DECISION_NAMES = (
    "2026-07-06_foldable-phone-stand.md",
    "2026-07-06_glass-storage-jar.md",
    "2026-07-06_led-pet-collar.md",
    "2026-07-06_mini-desk-vacuum.md",
    "2026-07-06_silicone-cable-organizer.md",
)
SOURCE_PROFILE_REL = Path("references/demo-data/example-profile-baseline.yaml")
SOURCE_SOP_REL = Path("sellers/_example/sop.md")
SOURCE_DECISIONS_REL = Path("sellers/_example/decisions")
SOURCE_REPORTS_REL = Path("reports/_example")


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


def _rewrite_decision_source(text: str, seller_id: str) -> str:
    pattern = re.compile(
        r"(?m)^(?P<prefix>\s*-\s*(?:来源报告ID|来源报告|source_report_id)\s*:\s*)"
        r"reports/_example/(?P<name>[^\s]+)\s*$"
    )
    matches = list(pattern.finditer(text))
    if len(matches) != 1 or matches[0].group("name") not in SOURCE_REPORT_NAMES:
        raise SystemExit("Synthetic decision must contain exactly one approved source report.")
    return pattern.sub(
        lambda match: f"{match.group('prefix')}reports/{seller_id}/{match.group('name')}",
        text,
    )


def _rewrite_source_report(text: str, seller_id: str, name: str) -> str:
    seller_pattern = re.compile(r"(?m)^- seller_id:\s*`_example`\s*$")
    source_pattern = re.compile(
        rf"(?m)^- source_report_id:\s*`reports/_example/{re.escape(name)}`\s*$"
    )
    text, seller_count = seller_pattern.subn(f"- seller_id: `{seller_id}`", text)
    text, source_count = source_pattern.subn(
        f"- source_report_id: `reports/{seller_id}/{name}`", text
    )
    if seller_count != 1 or source_count != 1:
        raise SystemExit(f"Synthetic source report metadata is malformed: {name}")
    return text


def _validated_demo_parent(name: str) -> Path:
    parent = ROOT / name
    if ROOT.is_symlink() or parent.is_symlink() or not parent.is_dir():
        raise SystemExit(f"Synthetic demo parent must be a real directory: {parent}")
    try:
        parent.resolve().relative_to(ROOT.resolve())
    except ValueError as exc:
        raise SystemExit(f"Synthetic demo parent escapes repository root: {parent}") from exc
    return parent


def _git_managed_relative_paths() -> set[str] | None:
    """Return tracked/pending-public paths, or None for a release without Git."""

    completed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        capture_output=True,
    )
    if completed.returncode != 0:
        return None
    return {
        item.decode("utf-8")
        for item in completed.stdout.split(b"\0")
        if item
    }


def _validate_source_parent(path: Path, expected_relative: Path) -> Path:
    expected = ROOT / expected_relative
    if path.absolute() != expected.absolute():
        raise SystemExit(f"Synthetic source path is not approved: {path}")
    current = path
    while True:
        if current.is_symlink():
            raise SystemExit(f"Synthetic source parent must not be a symlink: {current}")
        if current.absolute() == ROOT.absolute():
            break
        if current.parent == current:
            raise SystemExit(f"Synthetic source parent escapes repository root: {path}")
        current = current.parent
    if not path.is_dir():
        raise SystemExit(f"Missing synthetic source directory: {expected_relative}")
    try:
        path.resolve().relative_to(ROOT.resolve())
    except ValueError as exc:
        raise SystemExit(f"Synthetic source directory escapes repository root: {path}") from exc
    return path


def _validate_source_file(
    path: Path,
    *,
    expected_relative: Path,
    approved_root: Path,
    managed_paths: set[str] | None,
) -> Path:
    expected = ROOT / expected_relative
    if path.absolute() != expected.absolute():
        raise SystemExit(f"Synthetic source file is not approved: {path}")
    if path.is_symlink() or not path.is_file():
        raise SystemExit(f"Synthetic source must be a regular non-symlink file: {path}")
    try:
        path.resolve().relative_to(approved_root.resolve())
    except ValueError as exc:
        raise SystemExit(f"Synthetic source escapes its approved root: {path}") from exc
    relative_text = expected_relative.as_posix()
    if managed_paths is not None and relative_text not in managed_paths:
        raise SystemExit(
            f"Synthetic source is ignored or outside the Git-managed fixture set: {relative_text}"
        )
    return path


def validate_video_sources() -> dict[str, object]:
    """Validate the entire synthetic source allowlist before creating targets."""

    managed_paths = _git_managed_relative_paths()
    demo_data_root = _validate_source_parent(
        ROOT / SOURCE_PROFILE_REL.parent, SOURCE_PROFILE_REL.parent
    )
    example_root = _validate_source_parent(
        ROOT / SOURCE_SOP_REL.parent, SOURCE_SOP_REL.parent
    )
    decisions_root = _validate_source_parent(
        ROOT / SOURCE_DECISIONS_REL, SOURCE_DECISIONS_REL
    )
    reports_root = _validate_source_parent(
        ROOT / SOURCE_REPORTS_REL, SOURCE_REPORTS_REL
    )

    profile = _validate_source_file(
        ROOT / SOURCE_PROFILE_REL,
        expected_relative=SOURCE_PROFILE_REL,
        approved_root=demo_data_root,
        managed_paths=managed_paths,
    )
    sop = _validate_source_file(
        ROOT / SOURCE_SOP_REL,
        expected_relative=SOURCE_SOP_REL,
        approved_root=example_root,
        managed_paths=managed_paths,
    )
    actual_decision_names = {
        path.name for path in decisions_root.iterdir() if path.name != ".DS_Store"
    }
    if actual_decision_names != set(SOURCE_DECISION_NAMES):
        raise SystemExit(
            "Synthetic decision directory must contain exactly the approved fixture files."
        )
    decisions = [
        _validate_source_file(
            decisions_root / name,
            expected_relative=SOURCE_DECISIONS_REL / name,
            approved_root=decisions_root,
            managed_paths=managed_paths,
        )
        for name in SOURCE_DECISION_NAMES
    ]
    reports = {
        name: _validate_source_file(
            reports_root / name,
            expected_relative=SOURCE_REPORTS_REL / name,
            approved_root=reports_root,
            managed_paths=managed_paths,
        )
        for name in SOURCE_REPORT_NAMES
    }
    return {"profile": profile, "sop": sop, "decisions": decisions, "reports": reports}


def prepare_seller() -> str:
    sources = validate_video_sources()
    source_profile = sources["profile"]
    source_sop = sources["sop"]
    source_decisions = sources["decisions"]
    source_reports = sources["reports"]
    assert isinstance(source_profile, Path)
    assert isinstance(source_sop, Path)
    assert isinstance(source_decisions, list)
    assert isinstance(source_reports, dict)
    sellers_parent = _validated_demo_parent("sellers")
    reports_parent = _validated_demo_parent("reports")
    seller_id = f"{SELLER_PREFIX}{uuid.uuid4().hex}"
    target = sellers_parent / seller_id
    target_reports = reports_parent / seller_id
    for path, parent in ((target, sellers_parent), (target_reports, reports_parent)):
        try:
            path.resolve().relative_to(parent.resolve())
        except ValueError as exc:
            raise SystemExit(f"Synthetic demo path escapes its parent: {path}") from exc
    for path in (target, target_reports):
        if path.exists() or path.is_symlink():
            raise SystemExit(f"Refusing to reuse existing synthetic demo path: {path}")
    target.mkdir(parents=False, exist_ok=False)
    target_reports.mkdir(parents=False, exist_ok=False)
    target_decisions = target / "decisions"
    target_decisions.mkdir(exist_ok=False)

    profile = source_profile.read_text(encoding="utf-8").replace(
        'seller_id: "_example"', f'seller_id: "{seller_id}"'
    )
    (target / "profile.yaml").write_text(profile, encoding="utf-8")
    sop = source_sop.read_text(encoding="utf-8").replace("# SOP — _example", f"# SOP — {seller_id}")
    (target / "sop.md").write_text(sop, encoding="utf-8")
    for source in source_decisions:
        assert isinstance(source, Path)
        rewritten = _rewrite_decision_source(
            source.read_text(encoding="utf-8"), seller_id
        )
        (target_decisions / source.name).write_text(rewritten, encoding="utf-8")
    for name in SOURCE_REPORT_NAMES:
        source = source_reports[name]
        assert isinstance(source, Path)
        rewritten = _rewrite_source_report(
            source.read_text(encoding="utf-8"), seller_id, name
        )
        (target_reports / name).write_text(rewritten, encoding="utf-8")
    return seller_id


def report_path(seller_id: str, label: str) -> Path:
    today = dt.date.today().isoformat()
    return ROOT / "reports" / seller_id / f"{today}_demo-run-{label}.md"


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


def applied_rows(path: Path) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    in_table = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line == "| product | 已应用规则及分值变化 | total |":
            in_table = True
            continue
        if not in_table:
            continue
        if line.startswith("|---"):
            continue
        if not line.startswith("|"):
            break
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) == 3:
            rows.append((cells[0], cells[1]))
    return rows


def write_trace(before: Path, proposed: Path, after: Path, seller_id: str) -> Path:
    if not OPENING_POSITIONING.is_file():
        raise SystemExit(
            f"Missing demo opening page: {OPENING_POSITIONING.relative_to(ROOT)}"
        )

    before_rank = ranked_products(before)
    proposed_rank = ranked_products(proposed)
    after_rank = ranked_products(after)
    if before_rank != proposed_rank:
        raise SystemExit("Proposed learned rule changed ranking; demo guardrail failed.")
    if before_rank == after_rank:
        raise SystemExit("Active learned rule did not change ranking; demo guardrail failed.")
    proposed_text = proposed.read_text(encoding="utf-8")
    if f"| {DEMO_RULE_ID} | proposed |" not in proposed_text:
        raise SystemExit("Proposed rule was not rendered in the inactive-rules audit section.")

    out = ROOT / "reports" / seller_id / f"{dt.date.today().isoformat()}_video-full-trace.md"
    after_text = after.read_text(encoding="utf-8")
    if (
        f"| Shoe crease protector | {DEMO_RULE_ID} | condition_not_met |"
        not in after_text
    ):
        raise SystemExit("Active-rule non-match reason was not rendered for the shoe control.")
    applied = applied_rows(after)
    applied_products = {product.strip() for product, _ in applied}
    expected_products = {
        "Mini desk vacuum",
        "Silicone cable organizer",
        "Foldable phone stand",
    }
    if not expected_products.issubset(applied_products):
        missing = sorted(expected_products - applied_products)
        raise SystemExit(f"Active rule missed tagged demo candidates: {missing}")
    if "Shoe crease protector" in applied_products:
        raise SystemExit("Partial tag match misapplied rule to Shoe crease protector.")
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
        f"- seller_id: `{seller_id}`",
        f"- profile: `sellers/{seller_id}/profile.yaml`",
        f"- SOP: `sellers/{seller_id}/sop.md`",
        "- 初始 `learned: []`",
        "",
        "## 2. 首轮推荐",
        "",
        f"- 报告: `{before.relative_to(ROOT)}`",
        f"- 本报告展示的 Top 8: {before_rank}",
        "- 报告逐候选包含：为什么适合你、为什么不适合你、主要风险、下一步最小验证。",
        "",
        "## 3. 拒绝样本生成 learned 候选",
        "",
        "- 三条拒绝证据跨两个独立会话，并同时命中 `same_product_density_high + differentiation_space_low`。",
        f"- `propose_learned.py` 写入 `{DEMO_RULE_ID}`，状态为 `proposed`，并保留结构化 evidence。",
        f"- proposed 报告: `{proposed.relative_to(ROOT)}`",
        f"- 排名与首轮相同: `{before_rank == proposed_rank}`。证明 proposed 规则没有参与打分。",
        "",
        "## 4. 模拟已授权操作者确认后重跑",
        "",
        "- 脚本为合成验收模拟一位已授权操作者；`video-demo-operator` 不是现实真人授权记录。",
        "- `confirm_learned.py` 按 `rule_id` 将规则改为 `active`，并写入该模拟操作者和日期。",
        f"- 确认后报告: `{after.relative_to(ROOT)}`",
        f"- Top 8 before: {before_rank}",
        f"- Top 8 after: {after_rank}",
        f"- 被规则调整的候选: {applied or '详见确认后报告'}",
        "",
        "## 5. 自动验收",
        "",
        "- proposed 规则不改排序：PASS",
        "- active 规则后排序变化：PASS",
        "- 三个完整标签命中候选被调整：PASS",
        "- `Shoe crease protector` 仅部分标签命中且未被误伤：PASS",
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
    seller_id = prepare_seller()

    run([sys.executable, "scripts/run_demo.py", "--seller-id", seller_id, "--label", "video-before"])
    before = report_path(seller_id, "video-before")
    run([sys.executable, "scripts/propose_learned.py", seller_id])
    run([sys.executable, "scripts/run_demo.py", "--seller-id", seller_id, "--label", "video-proposed"])
    proposed = report_path(seller_id, "video-proposed")
    run(
        [
            sys.executable,
            "scripts/confirm_learned.py",
            seller_id,
            "--rule-id",
            DEMO_RULE_ID,
            "--confirmed-by",
            "video-demo-operator",
        ]
    )
    run([sys.executable, "scripts/run_demo.py", "--seller-id", seller_id, "--label", "video-after"])
    after = report_path(seller_id, "video-after")
    trace = write_trace(before, proposed, after, seller_id)
    print(f"Video trace ready: {trace.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
