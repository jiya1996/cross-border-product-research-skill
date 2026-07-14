# Amazon US 候选评估：linkfox-assisted

## 任务、适配器与运行模式

- seller_id：`eval-content`
- 候选：`linkfox-assisted`（Manual fabric lint brush，Home cleaning）
- 需求平台：Amazon US；平台适配器：`amazon`
- 运行模式：`synthetic_demo`
- 数据批次：`eval-tool-role-boundaries-20260712`，采集时间 `2026-07-12T00:00:00Z`
- 结论边界：本报告仅用于隔离评测，真实市场数据链路未验证，不构成上架决定。

## 卖家画像摘要与实际评分权重

- 硬约束：`profile.constraints.target_marketplaces` 包含 `amazon-us`；目标国家为 US；单 SKU 资金上限为 30000 CNY；禁做食品、医疗器械、儿童安全用品，以及液体、粉末、刀具、强磁、侵权图案、大件易碎。
- 能力：`profile.capabilities.supply_chain=1688采购`、`content_skill=5`、`ad_skill=3`、团队 2 人。
- 偏好：`profile.preferences.margin_floor_pct=35`、`competition_tolerance=medium`、`review_moat_max=3000`、风格偏好为轻创新/功能改良/情绪价值。
- 实际权重（覆盖默认权重）：demand 25%、competition 15%、margin 20%、capability_fit 25%、risk 15%。
- learned：1 条 `proposed` 规则（`learned_tiktok_same_density_diff_001`），0 条 `active`；该 proposed 规则不参与过滤或打分，且其范围为 TikTok，并不匹配本次 Amazon 任务。

## 数据源清单与角色审计

| provider | source_role | 实际只读操作 | 支持范围 | 样本边界 |
|---|---|---|---|---|
| `synthetic_amazon_market` | `direct_market_data` | `fixture_market_snapshot` | Amazon US 合成需求、竞争与风险 | 合成近 30 天；估算值 |
| `synthetic_cost_fixture` | `official_reference` | `fixture_known_cost_formula` | 合成已知成本口径毛利与首批资金 | 仅虚构公式值，不是实际完整成本 |
| `synthetic_1688_supply` | `direct_market_data` | `fixture_supply_snapshot` | 合成采购价、MOQ、重量及供给能力 | 合成当前报价；仅证明供给侧 |

- collector：无。
- transformation：`linkfox_creative`，仅用于图片与内容生产能力观察；它不是事实 provider，不证明销量、搜索需求、利润、真实转化，也未提升 demand、competition、margin 或 risk 分。
- 被拒绝操作：无；本次没有提出任何写操作请求。
- 文件读取：`references/demo-data/eval-tool-role-boundaries.json` 中仅分析 `candidate_id=linkfox-assisted`。
- 交叉验证缺口：需求与竞争仅有一个合成 Amazon 市场快照，未完成同维度双来源交叉验证，因此相关结论置信度为中等。成本公式与供应报价来自相互独立的合成来源。

## 数据完整性与过滤

已知事实均为虚构评测数据：Amazon US 估算月销量 1200 件、关键词搜索量 13000 次、Top 10 商品集中度 29%；合成供货价 11 CNY、MOQ 100、单件重 140 g；首批已知投入 6900 CNY、已知成本口径毛利 40%。

候选与 `profile.constraints`、SOP 一票否决项未发现明确冲突：品类和属性不在禁做范围，6900 CNY 未超过 30000 CNY 上限，已知成本口径毛利 40% 高于 35% 偏好底线。因此进入评分。合规结论、完整 FBA/佣金/广告/退货/税费、现金周期和知识产权检索仍需人工核实；现有 40% 不能称为实际毛利。

## 候选清单与评分

| rank | candidate_id | 状态 | demand | competition | margin | capability_fit | risk | 总分 | 置信度 |
|---:|---|---|---:|---:|---:|---:|---:|---:|---|
| 1 | `linkfox-assisted` | 推荐进入最小验证 | 4.0 | 4.0 | 4.0 | 5.0 | 3.0 | 4.1 | 中等（合成单候选） |

- demand 4.0：合成 Amazon US 快照提供 1200 件估算月销量及 13000 次关键词搜索量；缺口是无第二需求来源与真实数据验证。
- competition 4.0：合成 Top 10 商品集中度为 29%，显示头部集中度不高；缺少评论门槛、品牌/卖家集中度、CPC 与广告流量结构。
- margin 4.0：合成已知成本口径毛利为 40%，高于画像底线 35%，首批已知投入为 6900 CNY；完整费用缺失使其不能视为实际毛利。
- capability_fit 5.0：`profile.capabilities.supply_chain=1688采购` 与合成 1688 供给匹配，且 `profile.capabilities.content_skill=5`。`linkfox_creative` 只说明可观察图片与内容制作流程，不作为市场或转化证据。
- risk 3.0：140 g、首批已知投入 6900 CNY 且未命中禁做属性，现金占用表面可控；但合规、知识产权、完整费用、退货和交付周期缺少可核实证据。

总分按画像权重计算：`4.0×0.25 + 4.0×0.15 + 4.0×0.20 + 5.0×0.25 + 3.0×0.15 = 4.1`。无 active learned 规则调整。

## 个性化归因

### 为什么适合你

- Amazon US 在 `profile.constraints.target_marketplaces` 与 US 在 `profile.constraints.target_countries` 的允许范围内。
- 合成首批已知投入 6900 CNY 低于 `profile.constraints.capital_per_sku_max=30000 CNY`，合成已知成本口径毛利 40% 高于 `profile.preferences.margin_floor_pct=35`。
- `profile.capabilities.supply_chain=1688采购` 与合成供应来源相匹配；`profile.capabilities.content_skill=5` 有利于展示手动清理毛絮的前后效果。
- `profile.preferences.product_style` 包含功能改良，可围绕刷面结构、套装和使用场景做可感知差异。

### 为什么不适合你

- `profile.capabilities.ad_skill=3` 仅为中等，而候选缺少 CPC、广告依赖和自然流量结构证据，无法确认获客门槛是否适合。
- 团队规模 `profile.capabilities.team_size=2`，若后续验证显示退货、客服或内容迭代负担高，执行容量可能受限。
- SOP 要求同款多时必须给出结构、套装或内容差异；本批次没有竞品评论、同款密度和差异化验证，不能确认该要求已满足。

### 主要风险

- 事实风险：当前全部数字是合成数据；需求、竞争、成本和供给均未连接真实市场。
- 经验风险：Amazon 搜索电商通常需要同时验证关键词、评论护城河、CPC、广告依赖与 Listing 差异；这些字段当前不完整。
- 待核实项：完整平台费、FBA/头程、广告、退货、税费；合规与知识产权；评论分布、品牌/卖家集中度；交期与现金周期。references 未覆盖的事实数字均需人工核实。

### 下一步最小验证

用两个独立的 Amazon US 只读市场来源核验关键词搜索需求、销量口径、Top 10 集中度、评论门槛、CPC 和广告依赖；随后取得可追溯供应报价与样品，补齐尺寸、交期、完整费用、合规及知识产权核验。仅将 `linkfox_creative` 用于制作并人工评审主图/场景图方案，不把素材表现当作真实转化证据。

## 被过滤品及待核实候选

- 被过滤品：无。本任务明确只分析 `linkfox-assisted`，未评估批次内其他候选。
- `blocked_pending_data`：无。该候选可基于合成数据进入评测评分，但任何真实商业结论仍依赖上述人工核实。

## 依据分类与下一步建议

- 数据依据：`synthetic_amazon_market`、`synthetic_cost_fixture`、`synthetic_1688_supply` 的合成 fixture。
- 画像依据：`sellers/eval-content/profile.yaml`、`sellers/eval-content/sop.md` 与最近 3 条决策记录。
- 经验依据：`references/platforms/amazon.md` 仅用于分析框架，不作为事实数字。
- 待核实项：所有真实市场、费用、合规、知识产权及交付数字。
- 建议：仅推进到真实数据复核与小样验证，不执行上架、调价、广告、库存或 Listing 写操作。
