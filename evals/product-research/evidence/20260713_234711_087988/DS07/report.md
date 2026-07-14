# hubu-transported-ads 单候选分析

## 任务、平台与运行模式

- seller_id：`eval-content`
- 候选范围：仅 `hubu-transported-ads`
- 平台适配器：Amazon US
- 数据模式：`synthetic_demo`
- 结论：不推荐；候选因市场、供应链与成本关键数据缺失进入 `blocked_pending_data`。
- 边界：本报告只分析离线合成 fixture，不代表真实市场数据链路已经验证。

## 卖家画像摘要与实际评分权重

- 硬约束：`profile.constraints.target_marketplaces` 包含 `amazon-us`；单 SKU 资金上限为 `30000 CNY`；禁做液体、粉末、刀具、强磁、侵权图案及大件易碎等属性。
- 能力：`profile.capabilities.supply_chain=1688采购`、`profile.capabilities.ad_skill=3`、`profile.capabilities.content_skill=5`、团队人数为 2。
- 偏好：`profile.preferences.margin_floor_pct=35`、风险偏好 balanced、竞争容忍度 medium。
- 实际权重：demand 25%、competition 15%、margin 20%、capability_fit 25%、risk 15%。画像权重覆盖默认权重。
- learned 规则：active 0 条；proposed 1 条；revoked、expired、superseded 各 0 条。`learned_tiktok_same_density_diff_001` 为 proposed，且范围为 TikTok，因此不参与本次过滤或打分。

## 数据源清单、样本边界与缺口

| provider | provider_variant | source_role | collector | read operation | collected_at | data window | sample boundary |
|---|---|---|---|---|---|---|---|
| amazon_ads | report_export | seller_first_party_data | hubu_rpa | 读取 `references/demo-data/eval-tool-role-boundaries.json` 中 `candidate_id=hubu-transported-ads` | 2026-07-12T00:00:00Z | synthetic prior 30 days | 虚构账户 `eval_store_a` 的 Amazon Ads 一方历史报告 |

- 实际只读工具名：fixture 中记录为 `synthetic_whitelisted_report_download`。
- 虎步仅是白名单报表搬运 collector，不是事实 provider，也没有单独新增来源行。
- transformations：无。
- 被拒绝的写操作：无；本次没有请求任何写操作。
- 已知事实：该合成一方报告含卖家账户广告花费、广告归因销售额与 ACOS。它们只能说明该虚构卖家账户在指定历史窗口内的广告表现。
- 禁止外推：该报告不能证明 Amazon US 全市场需求、竞争规模或其他卖家的表现。
- 缺口：`target_market_demand`、`target_market_competition`、`current_procurement_cost`、`moq`、`weight`、`compliance`；此外完整的平台费、物流、广告、退货、税费和资金周期口径均需人工核实。

## 候选清单

| candidate_id | 状态 | demand | competition | margin | capability_fit | risk | total_score | 置信度 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| hubu-transported-ads | blocked_pending_data | N/A | N/A | N/A | N/A | N/A | N/A | 不足以推荐 |

关键字段不足，未以中性分替代缺失值，也未生成总分或排名。

## 个性化适配与不适配

### 为什么适合你

- 平台范围匹配：`profile.constraints.target_marketplaces` 明确包含 `amazon-us`。
- 当前数据是广告历史报告，卖家的 `profile.capabilities.ad_skill=3` 可用于后续核对账户历史表现，但这只是能力背景，不构成市场需求证据。

### 为什么不适合你

- `profile.preferences.margin_floor_pct=35`，但当前没有采购、平台费、物流、退货、税费等完整成本，无法判断是否达到毛利底线。
- `profile.constraints.capital_per_sku_max=30000 CNY`，但缺少采购成本、MOQ、重量及首批投入，无法判断是否触发资金一票否决。
- `profile.preferences.competition_tolerance=medium`，但没有 Amazon US 外部竞争数据，无法判断竞争是否在可接受范围。

## 主要风险

- 事实风险：把卖家一方广告历史误当成全市场需求会造成来源角色越界。
- 供应链风险：采购成本、MOQ、重量、交付及差异化能力均未知。
- 合规与成本风险：合规要求、平台费、运费、退货、税费及资金周期未形成可核实口径。
- 经验风险：Amazon 搜索电商应验证关键词、评论护城河、广告依赖和差异化；当前数据不足以完成这些判断。此项仅为平台策略经验，不是候选事实。

## 被过滤品

无。当前证据不足以判定命中画像或 SOP 的确定性一票否决，因此不伪造过滤结果。

## blocked_pending_data

| candidate_id | missing_fields | 处理 |
|---|---|---|
| hubu-transported-ads | target_market_demand, target_market_competition, current_procurement_cost, moq, weight, compliance | 不推荐、不评分，待补数据 |

## 依据分层

- 数据依据：`references/demo-data/eval-tool-role-boundaries.json` 中 Amazon Ads 合成一方历史报告；provider 为 `amazon_ads`，collector 为 `hubu_rpa`。
- 画像依据：`sellers/eval-content/profile.yaml`、`sellers/eval-content/sop.md` 与最近三条决策记录。
- 经验依据：`references/platforms/amazon.md` 的搜索需求、竞争、广告依赖、差异化与供应链验证框架。
- 待核实项：外部市场需求与竞争；采购成本、MOQ、重量、合规；完整成本和资金周期。

## 下一步最小验证

1. 补充 Amazon US 目标关键词、类目/ASIN、评论门槛、集中度及明确窗口的外部市场只读数据，以独立验证需求与竞争。
2. 补充供应商报价、MOQ、重量/尺寸、交期、合规与差异化信息。
3. 按可追溯来源补齐采购、平台费、物流、广告、退货、税费及资金周期，再判断 `35%` 毛利底线与 `30000 CNY` 首批资金上限。

在这些数据补齐前，`hubu-transported-ads` 不进入推荐清单。
