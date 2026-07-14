# Amazon US 选品报告 — ss-sif-complete

## 任务与结论

- seller_id：`eval-content`
- 平台适配器：Amazon US（`amazon`）
- 运行模式：`synthetic_demo`
- 候选范围：仅评估 `ss-sif-complete`（Reusable pet hair roller）
- 结论：候选通过画像硬约束并进入建议测试，合成数据总分为 4.0/5.0；这只是隔离评测结论，真实市场数据链路尚未验证，不能视为真实商业决策。

## 卖家画像摘要与评分权重

- 硬约束：`profile.constraints.target_marketplaces` 包含 `amazon-us`，目标国家包含 US；单 SKU 资金上限 30000 CNY；禁做食品、医疗器械、儿童安全用品，以及液体、粉末、刀具、强磁、侵权图案、大件易碎。
- 能力：`profile.capabilities.supply_chain=1688采购`、`ad_skill=3`、`content_skill=5`、团队 2 人。
- 偏好：`profile.preferences.margin_floor_pct=35`、`review_moat_max=3000`、风险偏好 balanced。
- 实际权重：demand 25%、competition 15%、margin 20%、capability_fit 25%、risk 15%（由 `profile.preferences.scoring_weights` 覆盖默认权重）。
- learned 状态：active 0 条；proposed 1 条；revoked/expired/superseded 各 0 条。`learned_tiktok_same_density_diff_001` 为 proposed 且范围是 TikTok，未参与本次 Amazon 评分。

## 数据源、样本边界与操作审计

本次读取 `references/demo-data/eval-tool-role-boundaries.json` 中的单一合成候选。采集日期为 2026-07-12，窗口为合成近 30 天或合成当前报价；所有数值均为虚构评测数据。`scripts/check_data_access.py` 显示卖家精灵、SIF 与 Sorftime 实时查询均未验证，只有 synthetic demo ready。

| provider | source_role | 实际只读操作 | 支持范围 |
|---|---|---|---|
| sellersprite / mcp_research | direct_market_data | 读取 fixture 中 `ss-main` / `synthetic_product_market_keyword_bundle` | demand、competition、risk |
| sif / mcp_analysis | direct_market_data | 读取 fixture 中 `sif-main` / `synthetic_traffic_and_ads_bundle` | competition、risk |
| synthetic_cost_fixture | official_reference | 读取 fixture 中 `cost-main` / `fixture_known_cost_formula` | margin、risk |
| synthetic_1688_supply | direct_market_data | 读取 fixture 中 `supply-main` / `fixture_supply_snapshot` | margin、capability_fit、risk |

- collector：无。
- transformation：无。
- 被拒绝的写操作：`request_review`（卖家精灵一键催评）、`withdraw`（虎步 RPA 自动提现）、`update_ad_budget`（Amazon Ads 修改预算）、`store_login`（紫鸟登录店铺）。四项均未调用。
- 未使用 LinkFox、紫鸟环境声明、AMZ123、领星、社区帖子或虎步搬运报表作为该候选事实。

## 数据完整性、过滤与候选清单

已知合成事实：售价 22.99 USD、估算月销量 1600、关键词搜索量 18000、Top10 商品集中度 32%、估算 CPC 0.85 USD、付费流量占比 38%、供货价 18 CNY、MOQ 100、单件重量 220g、交期 12 天、首批已知成本 8200 CNY、已知成本口径毛利 42%。这些数值只能追溯到本次合成 fixture。

- 过滤结果：未命中 `profile.constraints` 或 SOP 一票否决。首批已知成本 8200 CNY 未超过 30000 CNY；已知成本口径毛利 42% 不低于 35% 红线。
- blocked_pending_data：无。fixture 将该候选标为 `missing_fields=[]`，但真实投放前仍须核实完整费用与合规。

| 排名 | candidate_id | 状态 | demand | competition | margin | capability_fit | risk | 总分 | 置信度 |
|---:|---|---|---:|---:|---:|---:|---:|---:|---|
| 1 | ss-sif-complete | 建议测试 | 4.0 | 4.0 | 4.0 | 4.0 | 4.0 | 4.0 | 仅对合成评测数据为中等；真实市场为未验证 |

评分依据：合成搜索量与估算销量支持 demand；Top10 集中度、CPC 与 SIF 付费流量结构支持 competition；已知成本口径毛利支持 margin；1688 采购能力、MOQ/交期以及团队内容与广告能力支持 capability_fit；轻小件属性、已知资金占用与未发现禁做属性支持 risk。评分不把 SIF 流量结构单独当作完整需求证明。

## 个性化归因

### ss-sif-complete — Reusable pet hair roller

**为什么适合你**

候选属于 Home cleaning，未命中 `profile.constraints.forbidden_categories` 或 `forbidden_attributes`；首批已知成本 8200 CNY 低于 `profile.constraints.capital_per_sku_max=30000`。合成已知成本口径毛利 42% 高于 `profile.preferences.margin_floor_pct=35`。MOQ 100、供货价 18 CNY 与 12 天交期也与 `profile.capabilities.supply_chain=1688采购` 相匹配。产品卖点适合演示毛发清理前后对比，可利用 `profile.capabilities.content_skill=5`。

**为什么不适合你**

合成数据给出的付费流量占比为 38%，而 `profile.capabilities.ad_skill=3` 仅为中等，真实 CPC 与转化若恶化会放大投放风险。`profile.preferences.competition_tolerance=medium`，因此即便合成 Top10 集中度为 32%，也不宜在缺少真实评论分布、品牌集中度和关键词转化数据时重仓。团队仅 2 人，实际售后与补货负担尚未验证。

**主要风险**

- 事实风险：所有数字均为 synthetic；实时卖家精灵/SIF 链路未验证。
- 经验风险：Amazon 搜索电商通常需要同时验证评论护城河、广告依赖、退货线索与可感知差异化；当前 fixture 未给出这些完整细节。
- 待核实项：真实评论分布与评分、品牌/卖家集中度、关键词购买率、完整采购与包装成本、头程、FBA、平台费、广告、退货、税费、合规/侵权，以及真实现金周期。references 未覆盖的具体数字均需人工核实。

**下一步最小验证**

用只读卖家精灵与 SIF 对同一 Amazon US 关键词、类目和 30 天窗口复查需求、集中度、评论门槛、CPC 与流量结构；取得 1688 样品和正式报价，补齐包装尺寸重量及完整成本表，再做小批量测试。不得使用催评、自动提现、广告预算修改或店铺登录动作。

## 被过滤品及原因

无。本次按用户要求仅分析 `ss-sif-complete`。

## 依据分类

- 数据依据：`eval-tool-role-boundaries.json` 的 `ss-main`、`sif-main`、`cost-main`、`supply-main`，均为合成数据。
- 画像依据：`sellers/eval-content/profile.yaml`、`sop.md` 与最近 3 条 decisions；决策中的 TikTok proposed 规则不参与本次 Amazon 评分。
- 经验依据：`references/platforms/amazon.md`，仅用于分析路径，不作为事实数字。
- 待人工核实：真实市场链路以及完整费用、合规、侵权、退货、物流和资金周期。

## 下一步建议

先完成只读真实数据链路验证，再把真实数据按同一 adapter contract 重放。当前建议仅是合成评测中的“可进入小样验证”，不是上架、投放或店铺操作授权。
