# TikTok 画像感知选品 · 合成数据演示

> 运行模式：`synthetic_demo`。本报告只证明流程与规则可运行，不构成真实市场、采购、利润或上架建议。实时卖家精灵/Sorftime MCP 尚需单独通过只读查询验证。

## 任务与平台适配器

- seller_id: `_example`
- 需求平台: TikTok US（推荐流量）
- 平台策略: `references/platforms/tiktok.md`
- 流程: 数据完整性检查 → constraints/SOP 过滤 → 五维评分 → 个性化归因

## 已读取的卖家记忆

- profile: `sellers/_example/profile.yaml`
- sop: `sellers/_example/sop.md`
- 最近决策（最多 10 条）: ['2026-07-06_silicone-cable-organizer.md', '2026-07-06_mini-desk-vacuum.md', '2026-07-06_led-pet-collar.md', '2026-07-06_glass-storage-jar.md', '2026-07-06_foldable-phone-stand.md']
- confirmed learned 规则数: 0

## 数据来源、样本边界与缺口

- 候选: `references/demo-data/tiktok-candidates.md`（15 条合成数据）
- 换算假设: `references/demo-data/demo-assumptions.md`（合成）
- 运费: `references/freight.md` 的演示线路
- 平台费: `references/platform-fees.md` 的演示公式
- 评分: `references/checklists/scoring-rubric.md`
- 缺口: 广告、退货、税费、认证、合规、尾程与资金成本均未覆盖，必须人工核实；因此下表只能写“已知演示成本口径毛利”。

## 实际评分权重

| demand | competition | margin | capability_fit | risk |
|---:|---:|---:|---:|---:|
| 0.25 | 0.18 | 0.20 | 0.22 | 0.15 |

## 候选清单

| product | demand | competition | margin | capability_fit | risk | 已知成本毛利* | total | 已应用画像规则 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Reusable lint remover | 4 | 3 | 5 | 4 | 3 | 67.1% | 3.87 | - |
| Shoe crease protector | 4 | 2 | 5 | 4 | 3 | 67.7% | 3.69 | - |
| Pet slow feeder mat | 4 | 3 | 4 | 4 | 3 | 57.6% | 3.67 | - |
| LED pet collar | 4 | 3 | 4 | 4 | 3 | 56.8% | 3.67 | - |
| Pet paw cleaner cup | 4 | 3 | 4 | 4 | 3 | 55.6% | 3.67 | - |
| Car seat gap filler | 3 | 3 | 5 | 4 | 3 | 65.8% | 3.62 | - |
| Mini label maker refill pack | 3 | 4 | 5 | 3 | 3 | 66.4% | 3.58 | - |
| Silicone cable organizer | 3 | 2 | 5 | 4 | 3 | 68.4% | 3.44 | - |

* 已知成本毛利仅含合成售价、采购、演示头程和演示平台费，不是实际毛利。

排序键：先按 `total` 降序，再按已知成本口径毛利降序打破同分。

## Top 候选逐项归因

### 1. Reusable lint remover (`tt-005`)

- 为什么适合你：`profile.capabilities.content_skill=4` 与该品的素材钩子“衣服/沙发除毛前后”匹配；`profile.preferences.product_style=['轻创新', '情绪价值', '礼品', '功能改良']` 支持用轻创新/功能改良方式测试。
- 为什么不适合你：`profile.preferences.competition_tolerance=medium` 会放大“中等”的竞争风险；且当前仅有已知演示成本口径，尚不能证明完整毛利高于 `profile.preferences.margin_floor_pct=35%`。
- 主要风险（合成候选字段）：刀片结构待核实。事实风险需用真实来源复核。
- 下一步最小验证：补齐真实目标平台需求、竞争数据、供应商报价/重量尺寸，以及广告、退货、合规和税费后重算。

### 2. Shoe crease protector (`tt-015`)

- 为什么适合你：`profile.capabilities.content_skill=4` 与该品的素材钩子“球鞋前后对比”匹配；`profile.preferences.product_style=['轻创新', '情绪价值', '礼品', '功能改良']` 支持用轻创新/功能改良方式测试。
- 为什么不适合你：`profile.preferences.competition_tolerance=medium` 会放大“同款中高”的竞争风险；且当前仅有已知演示成本口径，尚不能证明完整毛利高于 `profile.preferences.margin_floor_pct=35%`。
- 主要风险（合成候选字段）：尺码适配/退货。事实风险需用真实来源复核。
- 下一步最小验证：补齐真实目标平台需求、竞争数据、供应商报价/重量尺寸，以及广告、退货、合规和税费后重算。

### 3. Pet slow feeder mat (`tt-011`)

- 为什么适合你：`profile.capabilities.content_skill=4` 与该品的素材钩子“狗狗进食速度对比”匹配；`profile.preferences.product_style=['轻创新', '情绪价值', '礼品', '功能改良']` 支持用轻创新/功能改良方式测试。
- 为什么不适合你：`profile.preferences.competition_tolerance=medium` 会放大“中等”的竞争风险；且当前仅有已知演示成本口径，尚不能证明完整毛利高于 `profile.preferences.margin_floor_pct=35%`。
- 主要风险（合成候选字段）：食品接触材料待核实。事实风险需用真实来源复核。
- 下一步最小验证：补齐真实目标平台需求、竞争数据、供应商报价/重量尺寸，以及广告、退货、合规和税费后重算。

### 4. LED pet collar (`tt-001`)

- 为什么适合你：`profile.capabilities.content_skill=4` 与该品的素材钩子“夜跑前后对比、宠物安全情绪”匹配；`profile.preferences.product_style=['轻创新', '情绪价值', '礼品', '功能改良']` 支持用轻创新/功能改良方式测试。
- 为什么不适合你：`profile.preferences.competition_tolerance=medium` 会放大“同款中等, 可做颜色/充电差异”的竞争风险；且当前仅有已知演示成本口径，尚不能证明完整毛利高于 `profile.preferences.margin_floor_pct=35%`。
- 主要风险（合成候选字段）：带电, 宠物安全待核实。事实风险需用真实来源复核。
- 下一步最小验证：补齐真实目标平台需求、竞争数据、供应商报价/重量尺寸，以及广告、退货、合规和税费后重算。

### 5. Pet paw cleaner cup (`tt-007`)

- 为什么适合你：`profile.capabilities.content_skill=4` 与该品的素材钩子“泥脚清洁前后”匹配；`profile.preferences.product_style=['轻创新', '情绪价值', '礼品', '功能改良']` 支持用轻创新/功能改良方式测试。
- 为什么不适合你：`profile.preferences.competition_tolerance=medium` 会放大“中等”的竞争风险；且当前仅有已知演示成本口径，尚不能证明完整毛利高于 `profile.preferences.margin_floor_pct=35%`。
- 主要风险（合成候选字段）：食品/宠物接触材料待核实。事实风险需用真实来源复核。
- 下一步最小验证：补齐真实目标平台需求、竞争数据、供应商报价/重量尺寸，以及广告、退货、合规和税费后重算。

### 6. Car seat gap filler (`tt-013`)

- 为什么适合你：`profile.capabilities.content_skill=4` 与该品的素材钩子“掉东西痛点演示”匹配；`profile.preferences.product_style=['轻创新', '情绪价值', '礼品', '功能改良']` 支持用轻创新/功能改良方式测试。
- 为什么不适合你：`profile.preferences.competition_tolerance=medium` 会放大“中等”的竞争风险；且当前仅有已知演示成本口径，尚不能证明完整毛利高于 `profile.preferences.margin_floor_pct=35%`。
- 主要风险（合成候选字段）：车型适配差异。事实风险需用真实来源复核。
- 下一步最小验证：补齐真实目标平台需求、竞争数据、供应商报价/重量尺寸，以及广告、退货、合规和税费后重算。

### 7. Mini label maker refill pack (`tt-012`)

- 为什么适合你：`profile.capabilities.content_skill=4` 与该品的素材钩子“收纳标签化”匹配；`profile.preferences.product_style=['轻创新', '情绪价值', '礼品', '功能改良']` 支持用轻创新/功能改良方式测试。
- 为什么不适合你：`profile.preferences.competition_tolerance=medium` 会放大“依赖设备兼容”的竞争风险；且当前仅有已知演示成本口径，尚不能证明完整毛利高于 `profile.preferences.margin_floor_pct=35%`。
- 主要风险（合成候选字段）：兼容/售后风险。事实风险需用真实来源复核。
- 下一步最小验证：补齐真实目标平台需求、竞争数据、供应商报价/重量尺寸，以及广告、退货、合规和税费后重算。

### 8. Silicone cable organizer (`tt-004`)

- 为什么适合你：`profile.capabilities.content_skill=4` 与该品的素材钩子“凌乱线缆整理前后”匹配；`profile.preferences.product_style=['轻创新', '情绪价值', '礼品', '功能改良']` 支持用轻创新/功能改良方式测试。
- 为什么不适合你：`profile.preferences.competition_tolerance=medium` 会放大“同款高”的竞争风险；且当前仅有已知演示成本口径，尚不能证明完整毛利高于 `profile.preferences.margin_floor_pct=35%`。
- 主要风险（合成候选字段）：低客单。事实风险需用真实来源复核。
- 下一步最小验证：补齐真实目标平台需求、竞争数据、供应商报价/重量尺寸，以及广告、退货、合规和税费后重算。

## 已应用 confirmed learned 规则的候选

- 无。`confirmed: false` 的规则未参与过滤或打分。

## 被过滤品及原因

| product | reason |
|---|---|
| Glass storage jar | 命中 profile.constraints.forbidden_attributes: 大件易碎; 命中 sop.md 一票否决规则: 易碎 |
| Magnetic spice jars | 命中 profile.constraints.forbidden_attributes: 强磁 |

## blocked_pending_data

- 本合成 fixture 的五维演示字段齐全；真实运行不得据此假设数据同样齐全。

## profile-update 候选规则（不自动生效）

- 用户连续拒绝同款过多且差异化不足的 TikTok 品，后续应降低同款密度高且内容记忆点弱的候选权重。 evidence: 2026-07-06_silicone-cable-organizer.md, 2026-07-06_mini-desk-vacuum.md, 2026-07-06_foldable-phone-stand.md

## 依据分类

- 画像依据：本卖家的 profile、SOP、最近 10 条决策。
- 数据依据：合成候选、演示换算、演示运费与演示平台费。
- 经验依据：TikTok 推荐流量与素材可拍性策略。
- 需人工核实：所有真实价格、需求、竞争、供应链、物流、平台费用、广告、退货、合规、认证和税费。

## 下一步建议

1. 先按 `config/mcp.md` 接入并验证一个只读数据源；
2. 将真实返回归一化为 `references/schemas/candidate-batch.schema.json`；
3. 对本轮 Top 候选补 1688 供应链验证与完整成本，再运行模式 B 压力测试；
4. 用户反馈必须通过 recommendation-review 记录，不在本 Skill 中修改画像。
