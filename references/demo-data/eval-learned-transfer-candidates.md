# Learned rule transfer fixture

> 合成评测输入，采集日期 2026-07-12。候选 ID 与 learned evidence 中的历史候选不同，用于检验规则是否按结构化标签迁移，而不是按旧候选 ID 套答案。

| id | product | category | target_price_usd | supply_price_cny | moq | weight_g | volume_cm | content_hook | demand_signal | competition_signal | risk_flags | rule_tag_ids |
|---|---|---|---:|---:|---:|---:|---|---|---|---|---|---|
| lr-a17 | Compact keyboard brush | 桌面清洁 | 12.99 | 7 | 160 | 55 | 11x4x3 | 键盘缝隙清洁前后 | 办公桌清洁内容有稳定互动 | 同款密度高，价格带集中 | 常规普货，合成低风险 | [same_product_density_high, differentiation_space_low] |
| lr-b42 | Fold-flat tablet rest | 手机配件 | 15.99 | 9 | 120 | 95 | 13x8x2 | 展开收纳一镜到底 | 桌搭场景需求稳定 | 同款很多，结构差异小 | 常规普货，合成低风险 | [same_product_density_high, differentiation_space_low, price_competition] |
| lr-c63 | Silicone cord label set | 桌面收纳 | 9.99 | 4 | 240 | 35 | 8x5x2 | 线缆识别前后对比 | 收纳内容有稳定互动 | 同款密度高，外观差异小 | 常规普货，合成低风险 | [same_product_density_high, differentiation_space_low] |
| lr-d88 | Stackable shoe slot | 鞋服收纳 | 13.99 | 8 | 150 | 180 | 25x10x6 | 鞋柜空间对比 | 小户型收纳场景明确 | 同款密度高，但结构仍可差异化 | 尺码适配已列为观察项 | [same_product_density_high, returns_high] |

所有数值与信号均为合成输入，不得用于真实经营决策。
