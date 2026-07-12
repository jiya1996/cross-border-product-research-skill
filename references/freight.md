# 头程费率与体积重公式

本文件用于维护头程费率表、体积重/抛比计算公式和来源链接。

## 演示线路

> 以下仅用于 `_example` 演示, 不得用于真实报价或真实选品报告。

| 线路 | 国家 | 品类限制 | 演示计费规则 | 来源 |
|---|---|---|---|---|
| CN -> US 小包普货 | US | 不含带电、液体、粉末、强磁、易碎 | `billable_weight_kg = max(actual_weight_kg, length_cm * width_cm * height_cm / 6000)`; `freight_cny = billable_weight_kg * 58 + 8` | 合成演示数据 · 2026-07-06 |
| CN -> US 带电专线 | US | 仅用于含内置电池/小电属性的演示候选 | `billable_weight_kg = max(actual_weight_kg, length_cm * width_cm * height_cm / 6000)`; `freight_cny = billable_weight_kg * 75 + 12` | 合成演示数据 · 2026-07-06 |

使用纪律：

- 未在本文件记录并标注来源的运费数字，报告中必须写"需人工核实"。
- 真实报告不得引用"演示线路"作为事实。
- 新增费率时必须包含适用国家/线路、计费规则、生效日期和来源。
- 历史费率只增补或标注失效，不直接删除。
