# Amazon US 候选评估：Reusable pet hair roller

## 1. 任务与结论

- seller_id：`eval-content`
- 候选：`ss-sif-complete`
- 需求平台/站点：Amazon US
- 平台适配器：Amazon
- 运行模式：画像感知选品；`synthetic_demo`
- 数据批次：`eval-tool-role-boundaries-20260712`
- 结论：**建议进入最小验证，不等同于上架建议。** 合成数据中存在搜索需求、竞争集中度尚非极端、已知成本口径毛利高于卖家红线，且首批已知投入低于资金上限；但真实市场链路未验证，评论门槛、完整费用、合规、退货和现金周期仍需人工核实。综合分 `3.7/5.0`，置信度中低（仅离线合成评测数据）。

## 2. 卖家画像摘要与实际权重

- 硬约束：`profile.constraints.target_marketplaces` 包含 `amazon-us`；`target_countries=[US]`；单 SKU 资金上限 `30000 CNY`；现金周期容忍 `45 天`；禁做食品、医疗器械、儿童安全用品，以及液体、粉末、刀具、强磁、侵权图案、大件易碎。
- SOP 一票否决：大件、易碎、液体、粉末、儿童安全用品不做；首批已知投入超过 `30000 CNY` 不测试。
- 能力：`profile.capabilities.supply_chain=1688采购`、`ad_skill=3`、`content_skill=5`、`team_size=2`。
- 偏好：已知成本口径毛利红线 `35%`，竞争容忍度 medium，评论护城河上限 `3000`，偏好轻创新/功能改良/情绪价值。
- 实际权重采用画像覆盖值：demand 25%、competition 15%、margin 20%、capability_fit 25%、risk 15%。
- learned 规则：active `0` 条；proposed `1` 条；revoked/expired/superseded 均 `0` 条。`learned_tiktok_same_density_diff_001` 为 proposed 且作用域是 TikTok，未参与本次评分。

## 3. 数据接入、来源角色与边界

执行 `scripts/check_data_access.py` 的只读检查结果：卖家精灵、SIF、Sorftime、领星实时查询均未验证；仅 synthetic demo ready。因此本报告不能声称已接入实时 MCP，也不能外推真实 Amazon US 市场。

| source_id | provider / variant | 实际只读操作 | 采集日期 | 市场 | 数据窗口 | 估算性质 | 允许作用范围 | 本报告实际用途 |
|---|---|---|---|---|---|---|---|---|
| ss-main | sellersprite / mcp_research | `synthetic_product_market_keyword_bundle`；读取 fixture 文件中的候选证据 | 2026-07-12 | Amazon US | 合成 trailing 30 days | estimated；synthetic | demand、competition、risk | 产品价格、估算销量、关键词搜索量、Top10 商品集中度、CPC；不称 Amazon 官方实销 |
| sif-main | sif / mcp_analysis | `synthetic_traffic_and_ads_bundle`；读取 fixture 文件中的候选证据 | 2026-07-12 | Amazon US | 合成 trailing 30 days | estimated；synthetic | competition、risk | 仅用于流量结构和广告依赖判断；不用于证明总市场需求 |
| cost-main | synthetic_cost_fixture | `fixture_known_cost_formula`；读取 fixture 文件中的公式结果 | 2026-07-12 | Amazon US 评测候选 | 无窗口 | derived；synthetic | margin、risk | 仅用于已知成本口径毛利；不称实际毛利 |
| supply-main | synthetic_1688_supply | `fixture_supply_snapshot`；读取 fixture 文件中的供应报价 | 2026-07-12 | 1688 合成供给样本，服务 Amazon US 候选 | 合成 current quotation | declared；synthetic | margin、capability_fit、risk | 仅证明合成供给侧可行性，不证明 Amazon 需求 |

- collector：无。
- transformation：无。
- denied operations：本次没有请求任何写操作，故为空；常驻禁用能力不伪装成已发生拒绝。
- 未使用来源：fixture 中的 LinkFox、紫鸟、AMZ123、领星、Amazon Ads Academy、Google Translate、虎步、知无不言、其他候选及 CPC 冲突来源均未用于本候选事实或评分。

## 4. 候选事实逐项溯源

以下数字全部是虚构、离线、provider-shaped 的合成评测值。

| 字段 | 值 | provider | 采集日期 | 市场 | 估算性质 | 作用范围与限制 |
|---|---:|---|---|---|---|---|
| price_usd | 22.99 USD | sellersprite / ss-main | 2026-07-12 | Amazon US | estimated、synthetic | 产品/价格背景；不单独证明需求或利润 |
| estimated_monthly_sales | 1600 units | sellersprite / ss-main | 2026-07-12 | Amazon US | estimated、synthetic，合成近 30 天 | demand；不是 Amazon 官方实销 |
| keyword_search_volume | 18000 searches | sellersprite / ss-main | 2026-07-12 | Amazon US | estimated、synthetic，合成近 30 天 | demand；关键词匹配口径在 fixture 中未进一步细分，需核实 |
| product_concentration_top10_pct | 32% | sellersprite / ss-main | 2026-07-12 | Amazon US | estimated、synthetic，合成近 30 天 | competition；分子为 Top10，fixture 未补充完整分母样本范围，不能称全类目垄断率 |
| estimated_cpc_usd | 0.85 USD | sellersprite / ss-main | 2026-07-12 | Amazon US | estimated、synthetic，合成近 30 天 | competition、risk；CPC 不等于转化或实际获客成本 |
| paid_traffic_share_pct | 38% | sif / sif-main | 2026-07-12 | Amazon US | estimated、synthetic，合成近 30 天 | 仅 competition、risk 中的流量结构/广告依赖；不进入 demand 证据 |
| supply_price_cny | 18 CNY | synthetic_1688_supply / supply-main | 2026-07-12 | 合成 1688 供给样本 | declared、synthetic current quotation | margin/capability_fit/risk；不证明 Amazon 需求 |
| moq | 100 units | synthetic_1688_supply / supply-main | 2026-07-12 | 合成 1688 供给样本 | declared、synthetic current quotation | capability_fit/risk；真实 MOQ 需供应商复核 |
| known_cost_margin_pct | 42% | synthetic_cost_fixture / cost-main | 2026-07-12 | Amazon US 评测候选 | derived、synthetic | margin；仅称已知成本口径毛利，不称实际毛利 |

批次 `facts` 还声明单位重量 `220g`、交期 `12 天`、首批已知投入 `8200 CNY`，但候选 `evidence[]` 没有逐字段回指记录。它们仅用于数据完整性提示：首批投入声明值低于 `profile.constraints.capital_per_sku_max=30000 CNY`，但上线决策前仍须补齐来源回指并人工核实；重量和交期不进入精确费用或现金周期结论。

## 5. 过滤 → 打分 → 归因

### 过滤结果

- 平台/国家：通过，命中 `profile.constraints.target_marketplaces=amazon-us` 与 `target_countries=US`。
- 类目/属性：Home cleaning / reusable pet hair roller 未命中已声明禁做类目或属性；但材质、磁性、电池、侵权和具体合规属性仍需样品核实。
- 资金：批次声明首批已知投入 `8200 CNY`，低于上限 `30000 CNY`；因缺候选级 evidence 回指，记为有条件通过。
- 毛利：已知成本口径毛利 `42%`，高于 `profile.preferences.margin_floor_pct=35%`；不代表包含平台费、头程、FBA、广告、退货、税费后的实际毛利。
- 结果：未被过滤，进入评分。仅分析一个候选，无其他被过滤品。

### 候选清单与评分

| rank | candidate_id | 状态 | demand | competition | margin | capability_fit | risk | total | 置信度 |
|---:|---|---|---:|---:|---:|---:|---:|---:|---|
| 1 | ss-sif-complete | 建议最小验证 | 4.0 | 3.0 | 4.0 | 4.0 | 3.0 | 3.7 | 中低：仅合成数据，需求未交叉验证 |

总分 = `4.0×0.25 + 3.0×0.15 + 4.0×0.20 + 4.0×0.25 + 3.0×0.15 = 3.7`。

- demand `4.0`：卖家精灵合成估算月销 1600 与关键词量 18000 共同支持搜索需求；缺少真实关键词匹配口径、趋势/季节性及第二个需求来源，不能给 5 分。SIF 流量份额未用于需求分。
- competition `3.0`：卖家精灵 Top10 集中度 32% 与 CPC 0.85 USD，结合 SIF 付费流量占比 38%，显示竞争与广告依赖可测试但并非低门槛；评论数、评分、品牌/卖家集中度和新品占比缺失。
- margin `4.0`：合成已知成本口径毛利 42% 高于画像红线 35%，供给报价 18 CNY、MOQ 100；完整平台费、物流、广告、退货、税费均缺失，所以不是实际毛利。
- capability_fit `4.0`：`profile.capabilities.supply_chain=1688采购` 与合成供给样本匹配，`content_skill=5` 有利于呈现除毛前后对比；但 Amazon `ad_skill=3`、团队仅 2 人，面对 38% 合成付费流量占比仍需控制投放复杂度。
- risk `3.0`：目前未命中禁做属性，且已知投入声明值低于资金上限；但评论护城河、合规、退货、完整费用与现金周期不足，风险只能评为平衡可测。

### 为什么适合你

- `profile.capabilities.supply_chain=1688采购` 与合成供给报价/MOQ 样本匹配，适合小批量询价和功能改良验证。
- `profile.capabilities.content_skill=5`，可把宠物毛发清理前后对比做成可感知内容，契合 `profile.preferences.product_style` 中的功能改良。
- 合成已知成本口径毛利 42% 高于 `profile.preferences.margin_floor_pct=35%`，首批投入声明值 8200 CNY 低于 `profile.constraints.capital_per_sku_max=30000 CNY`。

### 为什么不适合你

- `profile.capabilities.ad_skill=3` 仅中等，而 SIF 合成流量结构显示付费流量占比 38%；若真实数据复核后广告依赖更高，投放复杂度可能超出当前舒适区。
- `profile.capabilities.team_size=2`，若多材质适配、退货与评论维护复杂，团队容量可能成为短板。
- `profile.preferences.review_moat_max=3000`，但本批次没有评论数分布，当前无法确认是否越过卖家的信任门槛。

### 主要风险

- 事实风险：所有数据均为 synthetic demo；真实卖家精灵/SIF 链路未验证。SIF 38% 只能表示合成流量结构，不能证明完整需求。首批投入、重量、交期缺候选级 evidence 回指。
- 经验风险：Amazon 搜索品通常需同时验证评论护城河、广告依赖、差评和可感知差异；此处只作为平台策略，不作为事实数字或硬过滤。
- 待核实：真实搜索量/销量趋势、关键词匹配口径、Top10 集中度分母、评论与评分、新品占比、品牌/卖家集中度、完整费用、合规/侵权、材质适配、退货线索、供应商报价与 MOQ、交期、现金周期。

### 下一步最小验证

1. 用只读卖家精灵在 Amazon US 复查同一产品/关键词的产品、市场、关键词、Top10 集中度和 CPC，保存工具名、查询词、ASIN/类目节点、日期、窗口和分母。
2. 用只读 SIF 仅复查自然/广告流量结构和广告依赖；不得用其单一流量结构扩张为需求结论。
3. 补充评论数/评分/上架时间、品牌与卖家集中度、差评与退货线索，确认是否超过 `review_moat_max=3000`。
4. 获取 2–3 个 1688 样品报价并验证 MOQ、重量、尺寸、交期、包装与差异化；供应数据仍只证明供给侧。
5. 按 references 已核实公式补平台费、头程/FBA、广告、退货、税费和现金周期；未覆盖项保持“需人工核实”，再判断完整毛利是否仍高于 35%。

## 6. 被过滤品与 blocked_pending_data

- 被过滤品：无；用户只指定一个候选，且其未命中明确硬约束。
- blocked_pending_data：无。fixture 的 `missing_fields=[]` 且提供了用于初步过滤和五维评分的合成字段，因此保留为低置信度推荐；上述缺口必须在真实商业决策前核实。

## 7. 依据分类与最终边界

- 数据依据：仅 `references/demo-data/eval-tool-role-boundaries.json` 中 ss-main、sif-main、cost-main、supply-main 对 `ss-sif-complete` 的合成证据。
- 画像依据：`sellers/eval-content/profile.yaml`、`sellers/eval-content/sop.md`、最近 3 条 decisions；决策日志只用于理解画像，未触发 active learned 规则。
- 经验依据：`references/platforms/amazon.md`，只决定分析路径，不提供事实数字。
- 知识政策：`references/knowledge-policy.md`；所有未被 references 或输入证据覆盖的事实数字均标记需人工核实。
- 商业边界：本报告是隔离评测中的可复核建议，不是实时市场验证、最终商业机会证明或上架决定。
