# hubu-transported-ads 单候选分析

## 任务与结论

- seller_id：`eval-content`
- 平台适配器：Amazon US
- 运行模式：`synthetic_demo`
- 分析范围：仅 `candidate_id=hubu-transported-ads`
- 结论：`blocked_pending_data`。Amazon Ads 报告仅是当前卖家范围内的一方历史数据，不能外推为目标市场需求；候选同时缺少市场、供应链和成本关键数据，因此不评分、不排序、不推荐。

## 卖家画像摘要与评分权重

- 允许平台/国家：`profile.constraints.target_marketplaces=[tiktok-us, amazon-us]`、`profile.constraints.target_countries=[US]`。
- 单 SKU 资金上限：`profile.constraints.capital_per_sku_max=30000 CNY`；当前缺少首批投入，无法判断是否通过。
- 禁做边界：`profile.constraints.forbidden_categories`、`profile.constraints.forbidden_attributes` 以及 `sop.一票否决`；当前品类名称未直接命中禁做项，但属性与合规资料不足，不能据此判定通过。
- 能力：`profile.capabilities.ad_skill=3`、`content_skill=5`、`supply_chain=1688采购`、`team_size=2`。
- 毛利红线：`profile.preferences.margin_floor_pct=35`；当前缺少完整成本，无法判断。
- 实际评分权重：demand 25%、competition 15%、margin 20%、capability_fit 25%、risk 15%。由于关键数据不足，本次不执行评分。
- learned 规则：active 0 条；proposed 1 条；revoked/expired/superseded 各 0 条。proposed 规则不参与评分。

## 数据源与边界

| provider | provider_variant | source_role | collector | read operation | 日期/窗口 | 样本边界 |
|---|---|---|---|---|---|---|
| `amazon_ads` | `report_export` | `seller_first_party_data` | `hubu_rpa` | 读取 `references/demo-data/eval-tool-role-boundaries.json` 中 `source_id=hubu-collector` 对指定候选的证据 | 2026-07-12；合成前 30 天 | 仅虚构卖家 `eval_store_a` 的一方广告历史，不代表 Amazon US 市场 |

虎步仅执行白名单报表搬运，角色为 collector；事实 provider 仍为 `amazon_ads`，没有为搬运器新增来源。没有 transformation。本次未请求任何写操作，因此 denied operations 为空。真实市场数据链路未验证；`scripts/check_data_access.py` 仅确认 synthetic demo 可用。

## 候选清单

| candidate_id | 商品 | 状态 | demand | competition | margin | capability_fit | risk | 总分/排序 | 置信度 |
|---|---|---|---:|---:|---:|---:|---:|---|---|
| `hubu-transported-ads` | Seller ad-report lookalike accessory | `blocked_pending_data` | N/A | N/A | N/A | N/A | N/A | 不计算 | 低 |

已知的合成一方历史数据：广告花费 1250 USD、广告归因销售额 4200 USD、ACOS 29.76%。这些数值只描述该虚构卖家账户在该窗口内的广告历史，不证明市场需求、市场规模、竞争强度、未来表现或候选商业可行性。

## 个性化适配与风险

### 为什么可能适合你

- 目标路由与 `profile.constraints.target_marketplaces` 中的 `amazon-us` 一致。
- 卖家具备 `profile.capabilities.ad_skill=3`，一方广告历史可在补齐候选与市场映射后用于回测广告风险。
- `profile.capabilities.supply_chain=1688采购` 可用于后续供给验证，但本批次没有任何供应链证据。

### 为什么目前不适合你

- `profile.preferences.margin_floor_pct=35`，但缺少采购、物流、平台费用、广告、退货等成本，无法核验毛利红线。
- `profile.constraints.capital_per_sku_max=30000 CNY`，但缺少采购成本、MOQ、首批数量与物流成本，无法核验资金红线。
- `profile.constraints.forbidden_attributes` 与 `sop.一票否决` 要求排除敏感属性；当前缺少重量、尺寸、材质和合规信息，不能完成硬过滤。
- Amazon 平台策略要求关键词、市场、评论/集中度等直接市场证据；当前只有一方广告历史，不能证明需求或竞争。

### 主要风险

- 事实风险：数据只覆盖单一虚构卖家账户的合成广告历史，且候选与具体 ASIN/关键词的可核验映射不足。
- 经验风险：Amazon 搜索电商通常需要主动搜索与竞争门槛证据；此项仅为策略依据，不替代事实数据。
- 待核实：目标市场需求、目标市场竞争、采购成本、MOQ、重量/尺寸、交期、合规、完整成本、首批投入与现金周期。

### 下一步最小验证

1. 补充 Amazon US 的关键词、ASIN、市场规模、评论/集中度与广告依赖直接市场数据，并记录站点、采集日期、窗口和指标口径。
2. 补充 1688 或其他供应链的采购成本、MOQ、重量/尺寸、交期和差异化能力。
3. 按可追溯来源补齐平台费、物流、广告、退货、税费与合规成本；references 未覆盖的数字均需人工核实。

## 被过滤品

无。当前不是命中已证实的一票否决，而是事实不足，故进入待核实区。

## blocked_pending_data

| candidate_id | 缺失字段 |
|---|---|
| `hubu-transported-ads` | `target_market_demand`、`target_market_competition`、`current_procurement_cost`、`moq`、`weight`、`compliance` |

## 依据分类

- 数据依据：合成 Amazon Ads 一方历史报表；provider=`amazon_ads`，collector=`hubu_rpa`。
- 画像依据：`profile.constraints`、`profile.capabilities`、`profile.preferences` 与 `sop.一票否决`。
- 经验依据：`references/platforms/amazon.md`，仅用于分析路径。
- 待核实项：所有缺失的市场、供应链、成本和合规字段；不使用默认值补齐。

## 最终建议

保持阻塞，不进入推荐清单。只有补齐直接市场数据、供应链数据和完整成本后，才能重新执行“过滤 → 打分 → 归因”。
