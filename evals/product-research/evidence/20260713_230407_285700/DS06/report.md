# 领星历史边界评估

## 任务、平台与运行模式

- seller_id：`eval-content`
- 唯一候选：`lingxing-history-only`
- 需求平台 / 站点：Amazon US
- 平台适配器：`amazon`
- 运行模式：画像感知选品；`synthetic_demo`
- 结论：**暂不能推荐，进入 `blocked_pending_data`。** 当前证据只有该虚构卖家过去 90 天的第一方经营历史，无法验证 Amazon US 全市场需求与竞争，也不足以完成当前候选的成本、资金和合规过滤。

## 卖家画像摘要与评分权重

- 硬约束：`profile.constraints.target_marketplaces` 包含 `amazon-us`；单 SKU 首批资金上限为 30000 CNY；现金周期容忍为 45 天；禁做食品、医疗器械、儿童安全用品及液体、粉末、刀具、强磁、侵权图案、大件易碎。
- 能力：`profile.capabilities.supply_chain=1688采购`、`ad_skill=3`、`content_skill=5`、合规经验仅列 `FCC`、团队 2 人。
- 偏好：`profile.preferences.margin_floor_pct=35`、风险偏好 balanced、竞争容忍 medium、评论护城河上限 3000。
- 实际权重（画像覆盖默认）：demand 25%、competition 15%、margin 20%、capability_fit 25%、risk 15%。
- learned：active 规则 0 条；proposed 规则 1 条；revoked / expired / superseded 均为 0 条。`learned_tiktok_same_density_diff_001` 为 proposed，且作用域为 TikTok，因此本次不参与评分。

## 数据源、样本边界与访问审计

| provider | provider_variant | source_role | actual read operation | collected_at | market | window | measurement | synthetic |
|---|---|---|---|---|---|---|---|---|
| lingxing | N/A | seller_first_party_data | 读取 `references/demo-data/eval-tool-role-boundaries.json` 中 `lingxing-own` 及 `candidate_id=lingxing-history-only` | 2026-07-12T00:00:00Z | US / Amazon | synthetic prior 90 days | observed | true |

- tool_name：`synthetic_seller_report_export`。
- account_scope_id：`eval_store_a`（虚构本地别名）。
- collector：无。
- transformations：无。
- 本次没有请求任何写操作，因此 `denied_operations=[]`；也没有调用上架、调价、广告、库存或订单写能力。
- `scripts/check_data_access.py` 显示真实领星链路未验证，只有 synthetic demo ready。本报告不声称已接入真实 MCP。
- 样本只代表虚构卖家过去 90 天历史，不代表 Amazon US 全市场，不构成未来预测。

## 数据完整性检查

### 已知事实（仅历史回测语境）

| 字段 | 值 | 可影响维度 | 边界 |
|---|---:|---|---|
| historical_gross_margin_pct | 31% | margin | 仅为过去 90 天历史毛利，不是当前候选完整成本毛利，更不是未来毛利预测 |
| historical_refund_rate_pct | 11% | risk / capability_fit | 仅为该卖家历史售后表现 |
| historical_inventory_turnover_days | 84 天 | risk / capability_fit | 超过 `profile.constraints.cash_cycle_tolerance_days=45`，提示历史资金周转不匹配，但尚不能证明当前候选必然如此 |
| historical_ad_spend_share_pct | 24% | margin / capability_fit / risk | 仅说明卖家历史广告结构，不证明全市场广告依赖或未来表现 |

上述数字均来自合成 fixture，并非真实经营或市场数据。

### 缺失字段

- Amazon US 目标市场需求：关键词搜索量、类目规模、销量 / BSR 趋势及数据窗口。
- Amazon US 目标市场竞争：评论门槛、品牌 / 商品 / 卖家集中度、同款密度、CPC 与自然 / 广告流量结构。
- 当前商业与供给：售价、当前采购成本、MOQ、头程、FBA、佣金、广告、退款、税费等完整成本口径，首批已知投入。
- 当前物流：单件重量、包装尺寸、物流方案及现金周期。
- 当前合规：明确材质、用途、敏感属性、认证 / 资质和侵权检查。
- 差异化与质量：结构、套装或内容差异化方案，以及与 11% 历史退款相关的原因拆解。

费用、运费、税费、认证费用在现有输入中未覆盖，均为“需人工核实”，未补编任何数字。

## 过滤、打分与候选清单

流程先执行硬约束过滤。平台与国家范围匹配；品名和类目暂未直接命中禁做项。但首批投入、物流属性、现金周期、完整成本毛利和合规均缺失，不能判定通过硬约束，因此候选进入待核实区，不进入推荐或精确排名。

| candidate_id | 状态 | demand | competition | margin | capability_fit | risk | total | confidence |
|---|---|---:|---:|---:|---:|---:|---:|---|
| lingxing-history-only | blocked_pending_data | N/A | N/A | N/A | N/A | N/A | N/A | 低 |

没有以“缺数据=中性分”补分。历史 31% 毛利、11% 退款、84 天周转和 24% 广告占比是负向或待解释信号，但在缺少当前候选口径时不足以生成可复核的维度分。

## 个性化适配理由

### 为什么适合你

- 目标站点 Amazon US 在 `profile.constraints.target_marketplaces` 和 `profile.constraints.target_countries` 允许范围内。
- 卖家有 `profile.capabilities.supply_chain=1688采购`，若后续补齐当前供给报价，可执行小批量供给验证。
- `profile.capabilities.content_skill=5` 与偏好中的“功能改良、轻创新”可支持后续构建可感知差异化，但当前输入没有产品结构或内容卖点证据，不能据此提升市场需求结论。

### 为什么不适合你

- 历史周转 84 天高于 `profile.constraints.cash_cycle_tolerance_days=45`，说明同类经营历史与现金周期容忍存在明显张力；这只是历史风险提示，不是对未来的断言。
- 历史毛利 31%低于 `profile.preferences.margin_floor_pct=35`，但它不是当前候选的完整成本毛利，故只能触发补数据，不能直接作为当前候选的一票否决。
- 历史退款率 11%需要拆解退款原因；对 balanced 风险偏好和 2 人团队而言，售后复杂度可能形成执行压力。
- `profile.capabilities.ad_skill=3`，而历史广告花费占比 24%提示需要核实候选实际广告依赖；不得将该历史占比外推为 Amazon US 类目竞争事实。

## 主要风险

- 事实风险：历史毛利低于画像毛利偏好；历史库存周转长于现金周期容忍；历史退款需要原因拆解。
- 经验风险：Amazon 搜索电商在缺少关键词、评论护城河、集中度和 CPC 时，无法判断新品获客门槛。
- 待核实风险：合规、侵权、重量尺寸、完整成本、MOQ、首批投入、现金周期、差异化和质量改良方案。

## 被过滤品及原因

无候选被事实充分支持的一票否决规则直接过滤。唯一候选因关键事实缺失而阻塞，不归入 `filtered`。

## blocked_pending_data

| candidate_id | missing_fields |
|---|---|
| lingxing-history-only | target_market_demand；target_market_competition；current_selling_price；current_procurement_cost；moq；weight_and_dimensions；complete_cost_margin；first_batch_known_cost；cash_cycle；compliance；differentiation；refund_reason_breakdown |

## 事实依据、画像依据、经验依据和需人工核实项

- 事实依据：合成领星第一方历史报表，只允许支持历史 margin、capability_fit、risk 语境。
- 画像依据：`profile.constraints.*`、`profile.capabilities.*`、`profile.preferences.*` 与 SOP 一票否决 / 判断习惯。
- 经验依据：`references/platforms/amazon.md` 仅用于选择需验证的 Amazon 数据字段，不作为事实数字。
- 需人工核实：上述全部缺失字段，特别是目标市场需求 / 竞争、完整成本、资金占用、物流与合规。

## 下一步最小验证

1. 用 Amazon US 的只读直接市场数据补关键词搜索量、BSR / 销量趋势、评论分布、集中度和 CPC，并保留站点、日期、窗口和指标口径。
2. 获取当前候选的售价、采购价、MOQ、重量尺寸、首批投入，以及平台费、物流、广告、退款、税费的可追溯完整成本口径；未覆盖项继续标“需人工核实”。
3. 核实材质、用途、敏感属性、侵权及认证要求，并将 11% 历史退款拆到具体原因。
4. 仅在上述关键字段补齐、硬约束通过后再评分。领星 90 天历史继续作为回测参考，不称为未来预测。

