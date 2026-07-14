# cpc-conflict 单候选分析

## 任务与运行模式

- seller_id：`eval-content`
- 候选：`cpc-conflict`（Compact lint roller，Home cleaning）
- 平台适配器：Amazon US
- 数据模式：`synthetic_demo`
- 分析范围：仅分析 `references/demo-data/eval-tool-role-boundaries.json` 中的 `cpc-conflict`
- 结论：关键字段不足，进入 `blocked_pending_data`；不推荐、不评分。
- 真实市场数据链路未验证；`scripts/check_data_access.py` 显示卖家精灵、SIF、Sorftime、领星均未完成 live query 验证，仅合成演示数据可用。

## 卖家画像摘要与评分权重

- 硬约束：`profile.constraints.target_marketplaces` 包含 `amazon-us`；单 SKU 资金上限为 30000 CNY；禁做属性包括液体、粉末、刀具、强磁、侵权图案、大件易碎。
- 能力：`profile.capabilities.supply_chain=1688采购`、`ad_skill=3`、`content_skill=5`、团队 2 人。
- 偏好：`profile.preferences.margin_floor_pct=35`、竞争容忍度为 medium、风险偏好为 balanced。
- 实际权重：demand 25%、competition 15%、margin 20%、capability_fit 25%、risk 15%，来自 `profile.preferences.scoring_weights`，覆盖默认权重。
- learned 规则：active 0 条；proposed 1 条；revoked、expired、superseded 均为 0 条。proposed 规则 `learned_tiktok_same_density_diff_001` 不参与本次打分。

## 数据源、采集边界与角色

| source_id | provider | source_role | 只读操作 | 采集日期 | 时间窗口与口径 | 用途 |
|---|---|---|---|---|---|---|
| amazon-main | synthetic_amazon_market | direct_market_data | 读取 fixture 的价格证据 | 2026-07-12 | 合成 trailing 30 days；虚构离线评测值 | Amazon US 标价 |
| ss-cpc | sellersprite | direct_market_data | 读取 fixture 的广泛匹配 CPC | 2026-07-10 | 合成 trailing 30 days；广泛匹配 CPC 估算 | competition、risk 待核验信号 |
| sif-cpc | sif | direct_market_data | 读取 fixture 的精确匹配 CPC | 2026-07-12 | 合成 trailing 7 days；精确匹配 CPC 估算 | competition、risk 待核验信号 |

- collector：无。
- transformation：无。
- 本次没有请求平台写操作，因此 denied operations 为空。
- 样本边界：单个合成候选、单个关键词定位符；不代表真实 Amazon US 市场。

## 候选清单

| candidate_id | 状态 | demand | competition | margin | capability_fit | risk | 总分 | 置信度 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| cpc-conflict | blocked_pending_data | N/A | N/A | N/A | N/A | N/A | N/A | 低 |

不以数据缺失自动补中性分。该候选缺少可比 CPC、采购成本、MOQ、重量和完整毛利，不能通过硬约束检查，也不能形成分母完整的商业排序。

## CPC 冲突处理

- 卖家精灵：1.20 USD；采集日期 2026-07-10；广泛匹配；trailing 30 days；估算值。
- SIF：0.65 USD；采集日期 2026-07-12；精确匹配；trailing 7 days；估算值。
- 两者的采集日期、关键词匹配方式和时间窗口均不同，不能直接比较，也不能生成 `normalized_cpc`。
- CPC 冲突：不平均，不任选，不猜测

## 个性化适配归因

### 为什么适合你

- Amazon US 在 `profile.constraints.target_marketplaces` 允许范围内。
- Compact lint roller 的轻小件方向与 `profile.constraints.logistics_modes` 中的 FBA、轻小件直发存在初步形式匹配；但重量与尺寸缺失，这只是假设，不能作为已通过物流约束的事实。
- 产品可能适合用前后对比表达功能，与 `profile.capabilities.content_skill=5` 和 SOP 的可感知差异化习惯存在潜在匹配；当前 fixture 没有内容素材或痛点证据，仍需验证。

### 为什么不适合你

- `profile.capabilities.ad_skill=3`，而 CPC 口径冲突导致广告门槛不可判断；不能确认其是否符合 balanced 风险偏好。
- `profile.preferences.margin_floor_pct=35`，但缺采购、物流、平台费、广告、退货等完整成本，无法确认毛利红线。
- `profile.constraints.capital_per_sku_max=30000 CNY`，但缺采购成本与 MOQ，无法核验首批已知投入是否越线。

## 主要风险

### 事实风险

- 唯一可确认的候选价格是合成 Amazon US 标价 19.99 USD。
- 两个 CPC 均为合成估算且口径不同，不能用其一代表当前可执行广告成本。

### 经验风险

- Amazon 搜索电商通常需要同时核验关键词需求、评论护城河、广告依赖和差异化；本候选未提供这些完整字段。此项来自 `references/platforms/amazon.md`，仅作分析框架。

### 待核实项

- 在同一 Amazon US 关键词、同一采集日期、同一匹配方式、同一时间窗口下，分别重取卖家精灵与 SIF CPC，并保留各自 metric definition 与工具名。
- 补关键词文本/关键词 ID、站点、币种、竞价位置或广告位、设备与 placement 口径（若来源提供）、样本量或估算方法，确认两个来源是否测量同一对象。
- 补采购成本、MOQ、重量与尺寸、头程、FBA/尾程、平台费、广告、退货、合规与税费；references 未覆盖的事实数字均需人工核实。
- 补关键词搜索量、趋势、评论门槛、集中度、自然/广告流量结构和差异化证据，才能评分 demand、competition 与 capability_fit。

## 被过滤品

无。当前不是命中已知一票否决规则，而是关键事实不足，不能判定通过，故进入待核实区。

## blocked_pending_data

| candidate_id | 缺失字段 |
|---|---|
| cpc-conflict | normalized_cpc、procurement_cost、moq、weight、complete_margin |

## 依据分类

- 数据依据：`references/demo-data/eval-tool-role-boundaries.json` 中 `amazon-main`、`ss-cpc`、`sif-cpc` 的合成证据。
- 画像依据：`sellers/eval-content/profile.yaml`、`sellers/eval-content/sop.md`、最近 3 条决策记录。
- 经验依据：`references/platforms/amazon.md`，仅用于分析路径，不替代市场事实。
- 待核实：所有真实 CPC、采购、物流、费用、合规、需求与竞争数据。

## 下一步建议

先完成同口径 CPC 复测与完整成本采集，再执行硬约束过滤。数据补齐前不计算总分、不进入推荐清单。
