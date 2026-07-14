# 领星历史边界评估

## 任务与结论

- seller_id：`eval-content`
- 唯一候选：`lingxing-history-only`
- 平台适配器：Amazon US
- 运行模式：`synthetic_demo`
- 结论：当前不能推荐，转入 `blocked_pending_data`。领星过去 90 天数据只代表虚构卖家 `eval_store_a` 的历史经营表现，可作为 margin、capability_fit、risk 的历史回测信号；不得外推为 Amazon US 全市场需求，也不得称为未来预测。

## 卖家画像摘要与评分权重

- 硬约束：`profile.constraints.target_marketplaces` 包含 `amazon-us`；单 SKU 资金上限为 `30000 CNY`；现金周期容忍为 `45 天`；禁做食品、医疗器械、儿童安全用品，以及液体、粉末、刀具、强磁、侵权图案、大件易碎。
- 能力：`profile.capabilities.supply_chain=1688采购`、`ad_skill=3`、`content_skill=5`、团队 2 人，合规经验仅列明 FCC。
- 偏好：`profile.preferences.margin_floor_pct=35`，风险偏好 balanced。
- 实际权重：demand 25%、competition 15%、margin 20%、capability_fit 25%、risk 15%。画像权重覆盖默认权重。
- learned：`active=0`，`proposed=1`，`revoked=0`，`expired=0`，`superseded=0`。`learned_tiktok_same_density_diff_001` 为 proposed，且作用域为 TikTok，因此未参与过滤或评分。

## 数据源与访问审计

| provider | variant | source_role | read operation | 日期/窗口 | 样本边界 |
|---|---|---|---|---|---|
| lingxing | 无 | seller_first_party_data | 读取 `references/demo-data/eval-tool-role-boundaries.json` 中 `lingxing-own` 及候选 `lingxing-history-only` | 2026-07-12；合成过去 90 天 | 仅虚构账户别名 `eval_store_a` 的卖家第一方历史 |

- collector：无。
- transformation：无。
- 本次未请求任何写操作，因此 `denied_operations` 为空；也未调用上架、调价、广告、库存或 Listing 写能力。
- 数据接入检查：真实领星 live query 尚未验证；合成 fixture 可离线使用。本报告不声称已接入真实领星。
- 来源数字均为合成评测数据，不代表真实市场。

## 候选清单

| candidate_id | 状态 | demand | competition | margin | capability_fit | risk | 总分 | 置信度 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| lingxing-history-only | blocked_pending_data | N/A | N/A | N/A | N/A | N/A | N/A | 低 |

不评分原因：需求与竞争没有 Amazon US 市场证据；当前采购、MOQ、重量、合规、首批投入与完整成本口径缺失，无法先完成硬约束过滤。按评分纪律，缺失维度不填中性分，待核实候选不进入 Top 推荐。

## 个性化适配与风险

### 为什么适合你（仅作为继续核验的理由）

- 平台范围匹配：`profile.constraints.target_marketplaces` 包含 `amazon-us`。
- 历史数据能对卖家自身能力形成回测线索：过去 90 天历史毛利率 31%、退款率 11%、库存周转 84 天、广告支出占比 24%。这些字段允许用于后续 margin、capability_fit、risk 核验。
- `profile.capabilities.ad_skill=3` 可作为解读历史广告依赖的画像背景，但不能证明该候选未来广告表现。

### 为什么不适合你（当前阶段）

- 历史毛利率 31% 低于 `profile.preferences.margin_floor_pct=35`，是负向历史回测信号；但它不是当前候选完整成本毛利，不能据此直接硬过滤或预测未来毛利。
- 历史库存周转 84 天高于 `profile.constraints.cash_cycle_tolerance_days=45`，提示现金占用不匹配风险；但缺少当前候选 MOQ、采购成本、补货与首批投入，不能直接判定当前候选违反硬约束。
- 历史退款率 11% 提示售后风险；缺少 ASIN/MSKU、退款原因和同口径基准，不能据此推断 Amazon US 全市场风险水平。
- `profile.capabilities.compliance_experience` 仅有 FCC，而候选合规要求未知，必须人工核实。

### 主要风险

- 事实风险：卖家历史毛利、退款、库存周转与广告依赖均出现需要进一步拆解的信号。
- 推断风险：候选仅称“lookalike accessory”，无法确认它与历史产品在类目、ASIN/MSKU、价格、成本和运营方式上可比。
- 边界风险：若把当前卖家历史表现外推为 Amazon US 需求或把历史回测称为未来预测，会超出 `seller_first_party_data` 的证据权限。

### 下一步最小验证

1. 补 Amazon US 直接市场数据：目标关键词/类目、搜索量与趋势、Top 产品与 BSR、评论门槛、集中度、价格带、CPC 与广告依赖，均需站点、日期、窗口和指标口径。
2. 补当前候选供应与成本：采购价、MOQ、重量/尺寸、头程、FBA/佣金、广告与退货成本、首批已知投入；成本清单未覆盖的费率写“需人工核实”。
3. 补合规与产品身份：明确品类、材质、敏感属性、ASIN/MSKU 或可比产品范围、认证/侵权要求。
4. 若要验证未来表现，先保存 T0 预测快照，T+90 再按相同 seller_id、站点、产品、币种和口径读取实际快照；本次只有历史回测，不能报告未来预测或预测准确率。

## 被过滤品

无。现有事实不足以确认命中一票否决规则，因此不能把候选伪装成已通过，也不能直接过滤。

## blocked_pending_data

| candidate_id | 缺失字段 |
|---|---|
| lingxing-history-only | target_market_demand；target_market_competition；current_procurement_cost；moq；weight；compliance；first_batch_known_investment；current_complete_margin |

## 依据分层

- 数据依据：`lingxing-own` 的合成卖家第一方过去 90 天历史；只允许影响 margin、capability_fit、risk 的历史核验。
- 画像依据：`profile.constraints`、`profile.capabilities`、`profile.preferences` 与 SOP 一票否决规则。
- 经验依据：Amazon 平台策略用于确定所需市场与竞争字段，不替代事实数据。
- 需人工核实：全部缺失字段、真实领星只读链路、历史指标口径及可比产品映射。

## 推荐与排序

- 推荐清单：空。
- 精确排序：不适用，只有一个候选且关键字段不完整。
- 最终判断：补齐需求、竞争和硬约束字段前不能推荐。
