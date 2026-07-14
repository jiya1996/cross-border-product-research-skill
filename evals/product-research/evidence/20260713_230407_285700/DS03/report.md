# Amazon US 候选 ops-only 工具角色边界评估

## 任务、平台与运行模式

- seller_id：`eval-content`
- 唯一候选：`ops-only`（Unvalidated desk accessory）
- 平台适配器：Amazon US
- 运行模式：`synthetic_demo`
- 结论：**当前不能推荐。** 候选缺少 Amazon US 需求、竞争、价格、采购成本、MOQ、重量和合规证据，应进入 `blocked_pending_data`，不进入评分或 Top 推荐。

## 卖家画像摘要与评分权重

- 硬约束：`profile.constraints.target_marketplaces` 包含 `amazon-us`；单 SKU 首批资金上限为 30000 CNY；禁做食品、医疗器械、儿童安全用品，以及液体、粉末、刀具、强磁、侵权图案、大件易碎。
- 能力：`profile.capabilities.supply_chain=1688采购`、`ad_skill=3`、`content_skill=5`、`compliance_experience=[FCC]`、团队 2 人。
- 偏好：`profile.preferences.margin_floor_pct=35`，竞争容忍度 medium，评论护城河上限 3000。
- 实际权重：demand 25%、competition 15%、margin 20%、capability_fit 25%、risk 15%。本次因关键事实缺失，各维度均为 N/A，权重未用于生成总分。
- learned 规则：active 0 条；proposed 1 条；revoked/expired/superseded 各 0 条。`learned_tiktok_same_density_diff_001` 为 proposed 且作用域为 TikTok，未参与本次 Amazon 评估。

## 数据源、样本边界与访问审计

本次只读取仓库合成 fixture `references/demo-data/eval-tool-role-boundaries.json` 中 `candidate_id=ops-only`。样本采集标记为 2026-07-12，市场为 US；候选没有任何 `facts` 或 `evidence`，只有团队拥有工具的画像型声明。真实市场数据链路未验证；`scripts/check_data_access.py` 显示 SellerSprite、SIF、Sorftime、Lingxing 的 live query 均为 not-ready，synthetic demo 为 ready。

| 声明的工具 | 角色边界 | 本次能否作为候选事实 |
|---|---|---|
| 紫鸟浏览器 | capability context | 否；只能说明运营环境，且不得读取账号、IP、Cookie 或登录态 |
| AMZ123 | discovery only | 否；只能发现原始网站，导航信息不是市场证据 |
| 领星 ERP | 若有合规只读导出则为 seller first-party data | 否；本候选没有任何导出，且历史经营数据也不能单独外推 Amazon US 全市场需求 |
| 亚马逊广告学习网站 | official reference | 否；学习材料不替代实时市场、销量或竞争数据 |
| Google 翻译 | transformation only | 否；翻译不产生新事实，也不能提高需求或利润证据等级 |

- 实际 provider：`references_demo_fixture`（provider_variant=`ops-only`，角色=`capability_context`）。
- 实际只读操作：读取 `references/demo-data/eval-tool-role-boundaries.json` 中 `ops-only` 候选及工具拥有声明。
- collector：无。
- transformation：无；团队拥有 Google 翻译，但本次未实际转换任何证据。
- 被拒绝操作：无；用户没有请求写操作，因此不把常驻禁用能力伪造成实际拒绝事件。

## 候选清单

| candidate_id | 状态 | demand | competition | margin | capability_fit | risk | 总分 | 置信度 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| ops-only | blocked_pending_data | N/A | N/A | N/A | N/A | N/A | N/A | 不足 |

不能因为团队拥有运营、导航、ERP、学习或翻译工具而给 `capability_fit` 打分：fixture 只声明工具可用，画像也没有确认这些工具已形成针对该候选的可执行研究、成本或供应链能力。更不能把工具可用性映射为 demand、competition 或 margin。

## 个性化适配归因

### 为什么适合你

- 平台范围不冲突：`profile.constraints.target_marketplaces` 明确包含 `amazon-us`。
- 办公配件从现有名称看未直接命中 `profile.constraints.forbidden_categories`；但这只是身份层面的初步观察，不等于通过硬过滤。
- 若后续能验证轻创新或功能改良，方向可能贴合 `profile.preferences.product_style=[轻创新, 功能改良, 情绪价值]`，但当前没有产品结构或差异化证据。

### 为什么不适合你

- 无采购成本、MOQ、重量和完整成本口径，无法判断是否满足 `profile.constraints.capital_per_sku_max=30000 CNY`、`cash_cycle_tolerance_days=45` 与 `profile.preferences.margin_floor_pct=35`。
- 无评论、集中度和 CPC/广告依赖证据，无法判断是否符合 `profile.preferences.competition_tolerance=medium`、`review_moat_max=3000`，也无法评估 `profile.capabilities.ad_skill=3` 是否足够。
- 无合规与属性信息，无法确认是否触发 `profile.constraints.forbidden_attributes` 或超出 `profile.capabilities.compliance_experience=[FCC]`。

## 主要风险

- 事实风险：需求、竞争、价格、成本、MOQ、重量、合规和供应链全部缺证据。
- 经验风险：Amazon 是搜索电商；若没有关键词主动搜索、评论门槛和广告依赖数据，不能把“有工具”推断为“有市场”。该判断来自 `references/platforms/amazon.md`，属于分析策略而非候选事实。
- 待核实：平台费、头程/FBA、广告、退货、税费、认证或其他合规成本；references 未覆盖的具体数字一律需人工核实。

## 被过滤品

无。现有事实不足以确认候选违反某项硬约束，因此不能擅自将其判为过滤；应保持数据阻塞状态。

## blocked_pending_data

| candidate_id | 缺失字段 | 阻塞原因 |
|---|---|---|
| ops-only | target_market_demand、competition、price、procurement_cost、moq、weight、compliance | 无法完成硬约束判断、五维评分、毛利与资金占用验证，也没有供应链证据 |

## 依据分类

- 数据依据：仓库 synthetic fixture 仅证明候选没有事实证据，并记录一条工具拥有声明；不证明真实 Amazon US 市场。
- 画像依据：`profile.constraints`、`profile.capabilities`、`profile.preferences` 与 `sop.md`。
- 经验依据：`references/platforms/amazon.md` 的搜索需求、评论门槛、广告依赖和差异化分析框架。
- 待核实项：所有 Amazon US 需求、竞争、成本、供应链与合规字段。

## 下一步最小验证

1. 用合规只读直连或 verified import 补充 Amazon US 关键词搜索量、销量/BSR 趋势、数据窗口和指标口径，并至少交叉验证两类来源。
2. 补充评论门槛、Top N 集中度、CPC/广告依赖、竞品差异化与价格带。
3. 补充 1688 或其他供应商的采购价、MOQ、重量、交期、定制与稳定交付证据；供给证据不得替代 Amazon 需求。
4. 补齐平台费、物流、广告、退货和合规成本后计算可复算的已知成本口径毛利，并核对 35% 毛利红线与 30000 CNY 首批资金上限。

在上述字段补齐前，排序不成立，推荐列表保持为空。
