# 2026-07-14 交付状态

## 结论

今天可交付的是：**画像驱动的跨平台选品 Skill + 跨工具决策记忆定位页 + 合成数据演示 + 真人复盘入口 + 可复现测试包 + 黑盒评测器 + 脱敏 evidence + 录屏素材 + 公开安全最终评测版 ZIP**。

今天不能诚实宣称的是：**已经接入真实卖家精灵/SIF/Sorftime/领星数据、完成 90 天预测，或已证明推荐能提升利润**。当前环境没有相应 MCP 配置或密钥，`references/markets/` 也尚无目标国事实清单。

## 已完成

| 交付物 | 状态 | 证据 |
|---|---|---|
| 成品 `product-research` Skill | 完成 | `skills/product-research/SKILL.md` |
| Amazon/SHEIN/TikTok/DTC/Reddit/1688 策略路由 | 完成 | `references/platforms/` |
| 统一数据接入契约与 JSON Schema | 完成 | `references/data-sources/adapter-contract.md`、`references/schemas/candidate-batch.schema.json` |
| 十类工具角色注册表与能力级白名单 | 完成 | `references/data-sources/tool-role-registry.json`、`references/data-sources/ecosystem-tool-role-map.md` |
| 开场分层图、严谨定位与对外表述护栏 | 完成 | `references/demo-opening-positioning.md` |
| 最近一次真实选品复盘入口 | 完成 | `references/questions/recent-selection-retrospective.md`、`skills/intake-interview/SKILL.md` |
| 当时决定与后来结果分离写盘 | 完成 | `skills/recommendation-review/SKILL.md` |
| 领星 CSV/XLSX → MCP → OpenAPI 只读接入计划 | 完成设计，未接真实账号 | `references/data-sources/lingxing-readonly-plan.md` |
| 虎步受控报表投递边界与默认拒绝白名单 | 完成设计 | `references/data-sources/hubu-collector-boundary.md`、`config/hubu-rpa-allowlist.example.yaml` |
| HandsomeWang 上游审计与 clean-room 边界 | 完成 | `references/upstream/handsomewang-ai-skills-review.md` |
| 画像、SOP、结构化决策日志与 learned v2 状态机 | 完成 | `scripts/learned_rules.py`、`sellers/_example/`、四个 Skill |
| 合成 demo 的硬过滤、缺数据状态、逐候选归因 | 完成 | `scripts/run_demo.py` |
| 行为单测 | 137/137 通过 | `tests/test_learned_rules.py`、`tests/test_learned_cli.py`、`tests/test_eval_setup.py`、`tests/test_eval_runner_security.py`、`tests/test_evidence_export.py`、`tests/test_product_research_demo.py`、`tests/test_video_demo.py`、`tests/test_reset_demo.py`、`tests/test_build_release.py` |
| product-research 评测 case | 26 个 | `evals/product-research/cases.json` |
| 真人复盘验收 case | 4 个 | `evals/intake-retrospective/cases.json` |
| 100 分 rubric 与硬门禁 | 完成 | `evals/product-research/rubric.json` |
| Agent 全量评测 | 26/26 PASS | `evals/product-research/evidence/20260713_230407_285700/summary.json` |
| Agent 独立 P0 复跑 | 23/23 PASS | `evals/product-research/evidence/20260713_234711_087988/summary.json` |
| 平台路由 P01A/P01B | PASS | Amazon/TikTok 使用各自 canonical 路由 |
| learned 因果门 L01/L02 | PASS | proposed 不改排序，active 精确改变排序 |
| 压力测试 X01 | PASS | 忠实排序与成本压力排序发生预期反转 |
| 多租户与只读安全 W01/W02 | PASS | 零平台写调用，受禁止能力全部拒绝 |
| 数据角色 DS01–DS07 | PASS | provider、collector、transformation、历史经营数据边界均保持 |
| learned v2 录屏双断言与精准命中 | PASS | proposed 排名不变、active 排名变化；3 个完整命中被调整、Shoe 负例未误伤 |
| 一键录屏 | PASS | `scripts/run_video_demo.py` |
| 视频完整轨迹 | 每次使用唯一合成 seller 生成 | `reports/video-demo-<run-id>/YYYY-MM-DD_video-full-trace.md`，以控制台输出为准 |
| 公开安全 ZIP | 最终评测版，已通过 release manifest、ZIP 完整性和干净解压目录复验 | `dist/cross-border-product-research-skill-2026-07-14.zip` |

两次正式 Agent 运行均评测提交 `92e0a6040967e1c7ac9d7bc1a60ea61ec9d53996`，Codex 版本为 `codex-cli 0.144.2`，命令配置为 `codex_exec_ephemeral_workspace_write_v4`；公开 evidence 的三项元数据来源均为 `run_metadata`。

## 已验证命令

```bash
python3 scripts/verify_delivery.py
python3 scripts/run_video_demo.py
python3 scripts/run_product_research_evals.py --mode agent --suite all --timeout 600 --jobs 3
python3 scripts/run_product_research_evals.py --mode agent --priority P0 --timeout 600 --jobs 3
python3 scripts/build_release.py
```

## 当前真实数据状态

`python3 scripts/check_data_access.py` 的当前结果：

- synthetic demo：ready；
- SellerSprite：not-ready；
- SIF：not-ready；
- Sorftime：not-ready；
- Lingxing：not-ready；
- live query：未验证。

接入真实数据后的验收不是比较固定 Top 商品，而是检查：字段覆盖、来源、采集日期、缺失处理、candidate-batch 转换和零写操作。

当前公开 evidence 只包含上述全量与独立 P0 两次正式运行的脱敏副本。它们证明 learned v2 在合成 fixture 下通过流程、因果门和安全回归，不证明真实市场需求、推荐质量优于人工、利润提升或 90 天经营结果；`IR01–IR04` 仍需真人人工验收。

## 上游项目的使用结论

HandsomeWang/AI_SKILLS 可以作为 1688 供给研究的方法参考，但不能替代完整跨境选品判断。上游截至审计日没有许可证，本交付没有复制其代码、提示词或报告模板，只 clean-room 吸收关键词组合、样本边界、确定性数据与语义判断分层等通用思路。

## 录屏建议

按 `references/demo-script.md` 的 8–10 分钟分镜录制。三个必须展示的效果：

1. 易碎/强磁候选被画像与 SOP 过滤；
2. 每个 Top 候选都有“为什么适合你 / 为什么不适合你 / 主要风险”；
3. `status: proposed` 不改排序，只有 `status: active` 改变排名；完整标签命中会调整，部分标签命中不会误伤。

## 转为真实可用还差什么

1. 用户提供卖家精灵或 SIF 的只读 MCP 地址/令牌，或以 Sorftime 作替代；
2. 在 `/mcp` 核对真实工具名，完成一次最小只读 smoke；
3. 选择首个目标国家，补 `references/markets/{country}.md`；
4. 导入合作方真实运费、平台费、广告、退货与合规口径；
5. 用一个真实在售品跑模式 B，并由从业者核对隐性成本；
6. 按真人复盘问题库回放最近一次真实选品，并用 4 个 IR cases 人工验收；
7. 先导入一份脱敏、核实过的领星 CSV/XLSX 做历史回测，再决定是否开通受限 MCP；
8. 只有人工搬报表形成稳定痛点后，才评估虎步隔离采集器，始终保持零写操作。
