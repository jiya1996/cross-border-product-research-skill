# TikTok 合成数据 demo 运行报告

> 本报告基于合成演示数据生成：候选品的价格、销量信号、运费费率与平台费用均来自演示数据集（`references/demo-data`、`freight.md` 与 `platform-fees.md` 中标注“演示”的条目），不构成真实采购、定价或上架建议。接入贵方真实费率与市场数据后，毛利与排序将全部重新计算。

## 输入

- seller_id: `_example`
- profile: `sellers/_example/profile.yaml`
- sop: `sellers/_example/sop.md`
- candidates: `references/demo-data/tiktok-candidates.md`
- scoring: `references/checklists/scoring-rubric.md`

## Top 候选

| product | demand | competition | margin | capability_fit | risk | freight_route | margin_pct* | total | 已应用画像规则 |
|---|---:|---:|---:|---:|---:|---|---:|---:|---|
| Reusable lint remover | 4 | 3 | 5 | 4 | 3 | CN -> US 小包普货(合成) | 67.1% | 3.9 | - |
| Shoe crease protector | 4 | 2 | 5 | 4 | 3 | CN -> US 小包普货(合成) | 67.7% | 3.7 | - |
| Pet slow feeder mat | 4 | 3 | 4 | 4 | 3 | CN -> US 小包普货(合成) | 57.6% | 3.7 | - |
| LED pet collar | 4 | 3 | 4 | 4 | 3 | CN -> US 带电专线(合成) | 56.8% | 3.7 | - |
| Pet paw cleaner cup | 4 | 3 | 4 | 4 | 3 | CN -> US 小包普货(合成) | 55.6% | 3.7 | - |
| Car seat gap filler | 3 | 3 | 5 | 4 | 3 | CN -> US 小包普货(合成) | 65.8% | 3.6 | - |
| Silicone cable organizer | 3 | 2 | 5 | 4 | 3 | CN -> US 小包普货(合成) | 68.4% | 3.4 | - |
| Under-desk headphone hook | 3 | 3 | 5 | 3 | 3 | CN -> US 小包普货(合成) | 66.9% | 3.4 | - |

*margin_pct 由演示费率公式推算，仅用于展示计算逻辑，非真实毛利。

排序键：先按 `total` 降序，再按 `margin_pct` 降序打破同分。

## 被过滤品

| product | reason |
|---|---|
| Glass storage jar | 命中禁做属性: 易碎 |
| Magnetic spice jars | 命中禁做属性: 强磁 |

## profile-update 候选规则

- 用户连续拒绝同款过多且差异化不足的 TikTok 品, 后续推荐中应降低同款密度高且内容记忆点弱的候选权重。
  evidence: 2026-07-06_foldable-phone-stand.md, 2026-07-06_mini-desk-vacuum.md, 2026-07-06_silicone-cable-organizer.md

## 需人工核实

- 本 demo 中的价格、费用、重量、体积均为合成演示数据。
- 真实客户运行前必须替换为 MCP/API/人工核实数据。
