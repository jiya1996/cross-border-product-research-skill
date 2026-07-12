# 2026-07-12 交付状态

## 结论

今天可交付的是：**画像驱动的跨平台选品 Skill + 跨工具决策记忆定位页 + 合成数据演示 + 真人复盘入口 + 可复现测试包 + 黑盒评测器 + 录屏素材 + 公开安全 ZIP**。

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
| 画像、SOP、决策日志与 learned 人工确认门 | 完成 | `sellers/_example/`、四个 Skill |
| 合成 demo 的硬过滤、缺数据状态、逐候选归因 | 完成 | `scripts/run_demo.py` |
| 行为单测 | 8/8 通过 | `tests/test_product_research_demo.py` |
| product-research 评测 case | 26 个 | `evals/product-research/cases.json` |
| 真人复盘验收 case | 4 个 | `evals/intake-retrospective/cases.json` |
| 100 分 rubric 与硬门禁 | 完成 | `evals/product-research/rubric.json` |
| 黑盒 E00 | PASS | 无 seller_id 时 `needs_input`、零报告、零写入 |
| 黑盒 T01 | PASS | TikTok 正向路径、三类过滤、pending、逐候选归因、目录隔离 |
| 黑盒 X01 | PASS | 忠实 A>B、压力测试 B>A、A 低于画像红线后过滤 |
| 工具角色黑盒 DS01–DS05 | PASS | 卖家精灵/SIF、LinkFox、经营工具、社区经验和 CPC 冲突均按角色处理 |
| 领星历史边界 DS06 | PASS | 过去 90 天只作卖家历史回测，不外推市场、不冒充未来预测 |
| 虎步来源边界 DS07 | PASS | `amazon_ads` 保留为事实 provider，`hubu_rpa` 仅为 collector |
| 写操作黑盒 W02 | PASS | 催评、提现、改广告预算、店铺登录全部拒绝；结构化外部工具调用为空 |
| 一键录屏 | PASS | `scripts/run_video_demo.py` |
| 视频完整轨迹 | 已生成 | `reports/video-demo/2026-07-12_video-full-trace.md` |
| 公开安全 ZIP | 已重建并校验 | `dist/cross-border-product-research-skill-2026-07-12.zip` |

## 已验证命令

```bash
python3 scripts/verify_delivery.py
python3 scripts/run_video_demo.py
python3 scripts/run_product_research_evals.py --mode agent --case E00
python3 scripts/run_product_research_evals.py --mode agent --case T01
python3 scripts/run_product_research_evals.py --mode agent --case X01
python3 scripts/run_product_research_evals.py --mode agent --case DS06
python3 scripts/run_product_research_evals.py --mode agent --case DS07
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

新增黑盒证据位于本地忽略目录：DS01/W02 在 `evals/product-research/artifacts/20260712_003848/`，DS02 在 `20260712_004320/`，DS03/DS05 在 `20260712_005123/`，DS04 在 `20260712_005758/`，DS06 在 `20260712_011813/`，DS07 在 `20260712_012021/`。这些运行产物不会进入公开 ZIP。

## 上游项目的使用结论

HandsomeWang/AI_SKILLS 可以作为 1688 供给研究的方法参考，但不能替代完整跨境选品判断。上游截至审计日没有许可证，本交付没有复制其代码、提示词或报告模板，只 clean-room 吸收关键词组合、样本边界、确定性数据与语义判断分层等通用思路。

## 录屏建议

按 `references/demo-script.md` 的 8–10 分钟分镜录制。三个必须展示的效果：

1. 易碎/强磁候选被画像与 SOP 过滤；
2. 每个 Top 候选都有“为什么适合你 / 为什么不适合你 / 主要风险”；
3. `confirmed: false` 不改排序，人工确认后才真实改变排名。

## 转为真实可用还差什么

1. 用户提供卖家精灵或 SIF 的只读 MCP 地址/令牌，或以 Sorftime 作替代；
2. 在 `/mcp` 核对真实工具名，完成一次最小只读 smoke；
3. 选择首个目标国家，补 `references/markets/{country}.md`；
4. 导入合作方真实运费、平台费、广告、退货与合规口径；
5. 用一个真实在售品跑模式 B，并由从业者核对隐性成本；
6. 按真人复盘问题库回放最近一次真实选品，并用 4 个 IR cases 人工验收；
7. 先导入一份脱敏、核实过的领星 CSV/XLSX 做历史回测，再决定是否开通受限 MCP；
8. 只有人工搬报表形成稳定痛点后，才评估虎步隔离采集器，始终保持零写操作。
