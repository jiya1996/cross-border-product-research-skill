# CPC 冲突核验报告

## 任务与结论

- seller_id：`eval-content`
- 平台适配器：Amazon US
- 运行模式：`synthetic_demo`（隔离评测数据；真实市场数据链路未验证）
- 分析范围：仅 `candidate_id=cpc-conflict`
- 结论：候选进入 `blocked_pending_data`，不推荐、不评分、不排序。卖家精灵与 SIF 的 CPC 在采集日期、匹配方式和时间窗口上不同，不能合并成一个事实值。
- CPC 冲突：不平均，不任选，不猜测

## 卖家画像摘要与实际评分权重

- 允许市场：`profile.constraints.target_marketplaces=[tiktok-us, amazon-us]`，`profile.constraints.target_countries=[US]`。
- 资金红线：`profile.constraints.capital_per_sku_max=30000 CNY`；SOP 规定首批已知投入超过 30000 CNY 不进入测试。
- 禁做边界：`profile.constraints.forbidden_categories` 与 `profile.constraints.forbidden_attributes`；当前品类名称未直接命中，但商品属性和合规信息不足，尚不能完成硬过滤。
- 能力：`profile.capabilities.ad_skill=3`、`content_skill=5`、`supply_chain=1688采购`、`team_size=2`。
- 毛利偏好：`profile.preferences.margin_floor_pct=35`。
- 实际权重：demand 25%、competition 15%、margin 20%、capability_fit 25%、risk 15%，覆盖默认权重，因为画像提供了自定义权重。
- learned 规则：active 0 条；proposed 1 条；revoked/expired/superseded 各 0 条。`learned_tiktok_same_density_diff_001` 为 proposed 且范围为 TikTok，本次不参与评分。

## 数据源、样本边界与角色

本次读取 `references/demo-data/eval-tool-role-boundaries.json`，只采用指定候选及其三条直接证据。所有数值均为虚构评测数据，不代表真实市场。

| source_id | provider | source_role | 只读工具/操作 | 采集日期 | 窗口与口径 | 可用边界 |
|---|---|---|---|---|---|---|
| amazon-main | synthetic_amazon_market | direct_market_data | `fixture_market_snapshot`；读取候选价格 | 2026-07-12 | synthetic trailing 30 days；虚构离线评测值 | 仅支持价格证据 |
| ss-cpc | sellersprite | direct_market_data | `synthetic_keyword_cpc_broad`；读取 broad-match CPC | 2026-07-10 | synthetic trailing 30 days；Broad-match CPC estimate | 仅支持 competition/risk，且不可与不同口径 CPC 直接合并 |
| sif-cpc | sif | direct_market_data | `synthetic_keyword_cpc_exact`；读取 exact-match CPC | 2026-07-12 | synthetic trailing 7 days；Exact-match CPC estimate | 仅支持 competition/risk，且不可与不同口径 CPC 直接合并 |

- collector：无。
- transformation：无。
- 本次没有请求任何写操作，因此 `denied_operations` 为空；未调用上架、调价、广告、库存或 Listing 写能力。
- 数据接入自检：卖家精灵、SIF、Sorftime、领星实时查询均未验证；synthetic demo 可用。

## CPC 冲突证据

| provider | CPC | 匹配方式 | 采集日期 | 时间窗口 | 处理 |
|---|---:|---|---|---|---|
| sellersprite | 1.20 USD | broad match | 2026-07-10 | synthetic trailing 30 days | 原样保留，不作为统一 CPC |
| sif | 0.65 USD | exact match | 2026-07-12 | synthetic trailing 7 days | 原样保留，不作为统一 CPC |

两条记录测量的并非同一口径。`normalized_cpc` 保持缺失；不计算均值，不选择其中一个，也不推测“更可信”的值。当前只能确认“存在两个不可直接比较的 CPC 估算”，不能据此得出单一广告成本或精确广告门槛。

## 候选清单

| candidate_id | 商品 | 状态 | demand | competition | margin | capability_fit | risk | 总分 | 置信度 |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| cpc-conflict | Compact lint roller | blocked_pending_data | N/A | N/A | N/A | N/A | N/A | N/A | 低 |

缺少关键事实，不以 0 分或中性分代替，也不进入精确排序。

## 个性化适配与风险

### 为什么适合你

- Amazon US 在 `profile.constraints.target_marketplaces` 允许范围内。
- 若后续证实产品可做轻小件，可能与 `profile.constraints.logistics_modes=[FBA, 轻小件直发]` 及 `profile.capabilities.supply_chain=1688采购` 匹配；目前重量、MOQ 和采购成本缺失，所以这只是待验证的画像适配假设。

### 为什么不适合你

- `profile.capabilities.ad_skill=3`，而 CPC 尚无法归一，广告门槛不可判断；不能确认是否适合当前广告能力。
- `profile.preferences.margin_floor_pct=35`，但采购成本与完整成本毛利缺失，不能验证毛利红线。
- `profile.constraints.capital_per_sku_max=30000 CNY`，但 MOQ、采购成本与首批已知投入缺失，不能验证资金红线。

### 主要风险

- 事实风险：两个 CPC 的匹配方式、日期与窗口不同；重量、MOQ、采购成本、完整成本毛利、合规/敏感属性、首批投入均不足。
- 经验风险：Amazon 搜索电商需要同时验证关键词需求、评论护城河、广告依赖与差异化；平台策略只提供分析框架，不构成事实数字。
- 待核实：当前 19.99 USD 只是合成价格快照，不能推导真实利润或商业机会。

### 下一步最小验证

1. 对同一 Amazon US 关键词（并记录关键词文本）或同一 ASIN，在同一采集日补采卖家精灵与 SIF CPC。
2. 两边统一匹配方式（都为 broad 或都为 exact）、统一时间窗口（例如都为 7 天或都为 30 天）并记录指标定义。
3. 补充 CPC 的广告位置/placement、竞价策略、设备或流量范围、币种及观测/估算属性，确认两边是否测量同一对象。
4. 保存两边原始只读导出或响应及查询参数；即使统一口径后仍有差异，也继续并列展示，不自动平均。
5. 补齐采购成本、MOQ、重量、完整成本毛利；同时核验商品属性、合规、首批已知投入、关键词需求、评论数/评分、集中度和差异化证据。

## 被过滤品

无。当前不是命中已证实的一票否决，而是关键事实不足，故列入待核实区。

## blocked_pending_data

| candidate_id | 缺失字段 |
|---|---|
| cpc-conflict | normalized_cpc、procurement_cost、moq、weight、complete_margin |

此外，为完成硬过滤和完整商业判断，仍需人工核实商品属性/合规、首批已知投入、目标关键词需求、评论护城河、集中度与差异化。

## 依据分类

- 数据依据：指定 fixture 中 amazon-main、ss-cpc、sif-cpc 的候选证据；均为 synthetic。
- 画像依据：`sellers/eval-content/profile.yaml`、`sellers/eval-content/sop.md`。
- 经验依据：`references/platforms/amazon.md`，仅用于分析路径。
- 知识纪律：`references/knowledge-policy.md`；未覆盖或不可比的事实不补数。

## 下一步建议

先执行同口径 CPC 双源补采，再补成本、MOQ、重量、合规和需求竞争数据。完成前维持 `blocked_pending_data`，不输出推荐或商业机会分。
