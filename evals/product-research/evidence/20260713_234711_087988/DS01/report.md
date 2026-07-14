# Amazon US 候选评估：Reusable pet hair roller

## 1. 任务与结论

- seller_id：`eval-content`
- 平台适配器：Amazon US
- 候选范围：仅 `ss-sif-complete`
- 运行模式：画像感知选品；`synthetic_demo`
- 结论：**有条件推荐进入最小验证**，不是上架决定。合成数据支持“存在搜索需求、集中度与广告依赖尚可测试、已知成本口径达到卖家毛利偏好”的初步判断；真实市场数据链路未验证，所有数字均为虚构估算/声明/派生值，不可当作真实 Amazon 或 1688 行情。

## 2. 卖家画像摘要与过滤

实际权重来自 `profile.preferences.scoring_weights`：demand 25%、competition 15%、margin 20%、capability_fit 25%、risk 15%。

硬约束核对：Amazon US 属于 `profile.constraints.target_marketplaces=[tiktok-us, amazon-us]`，市场 US 属于 `profile.constraints.target_countries=[US]`；产品不命中已声明的禁做类目或属性。合成批次声明首批已知投入 8,200 CNY，低于 `profile.constraints.capital_per_sku_max=30000 CNY`；该值仅是 fixture 中的派生估算。已知成本口径毛利 42%，高于 `profile.preferences.margin_floor_pct=35`，但不是实际毛利。

能力与偏好：`profile.capabilities.supply_chain=1688采购`、`content_skill=5`、`ad_skill=3`、团队 2 人；偏好轻创新、功能改良和情绪价值。SOP 禁止用 1688 替代美国需求证据，本报告仅用供给 fixture 支持成本和履约初筛。

learned 规则：active 0 条；proposed 1 条；revoked/expired/superseded 均 0 条。`learned_tiktok_same_density_diff_001` 为 proposed 且限定 TikTok，未参与过滤或评分。

## 3. 数据接入与角色边界

`scripts/check_data_access.py` 显示 SellerSprite、SIF 与 Sorftime 的 live query 均未验证，只有 synthetic demo ready。本次仅只读 `references/demo-data/eval-tool-role-boundaries.json`，没有 MCP、浏览器或平台写操作。

| provider / source_id | 实际只读操作 | 采集日期 | 市场 | 数据窗口 | 估算性质 | 作用范围 | 本报告边界 |
|---|---|---|---|---|---|---|---|
| sellersprite / `ss-main` | 读取 fixture 中 `ss-sif-complete` 的产品、市场、关键词、集中度、CPC 字段 | 2026-07-12 | Amazon US | 合成近 30 天 | estimated、synthetic | demand、competition、risk | 仅用于产品、市场、关键词、集中度和 CPC；估算销量不是官方实销，CPC 不等于转化 |
| sif / `sif-main` | 读取 fixture 中流量结构和广告依赖字段 | 2026-07-12 | Amazon US | 合成近 30 天 | estimated、synthetic | competition、risk | 仅用于流量结构与广告依赖，不证明完整市场需求 |
| synthetic_cost_fixture / `cost-main` | 读取 fixture 已知成本公式结果 | 2026-07-12 | Amazon US 评测口径 | 不适用 | derived、synthetic | margin、risk | 仅为已知成本口径，不是实际毛利或官方费用 |
| synthetic_1688_supply / `supply-main` | 读取 fixture 供应报价、MOQ、重量、交期 | 2026-07-12 | 1688 合成供给样本；目标市场仍为 US | 合成当前报价 | declared、synthetic | margin、capability_fit、risk | 只证明合成供给侧可行性，不证明 Amazon US 需求 |

collector：无。transformation：无。未发生写操作请求，因此 denied operations 为空。批次中其他来源未用于该候选结论；尤其未将 LinkFox、紫鸟、AMZ123、领星、社区帖子、翻译或虎步搬运能力计入本候选需求分。

## 4. 逐项事实与用途

| 字段 | 值 | provider | 采集日期 | 市场 | 估算性质 | 作用范围与限制 |
|---|---:|---|---|---|---|---|
| 售价 | 22.99 USD | sellersprite `ss-main` | 2026-07-12 | Amazon US | estimated、synthetic | 市场/价格背景；不单独证明利润 |
| 月销量 | 1,600 件 | sellersprite `ss-main` | 2026-07-12 | Amazon US | estimated、synthetic | demand；不是 Amazon 官方实销 |
| 关键词搜索量 | 18,000 次 | sellersprite `ss-main` | 2026-07-12 | Amazon US | estimated、synthetic，近 30 天 | demand；只代表 fixture 口径 |
| Top10 商品集中度 | 32% | sellersprite `ss-main` | 2026-07-12 | Amazon US | estimated、synthetic，近 30 天 | competition；Top10/样本分母以 fixture 定义为限 |
| CPC | 0.85 USD | sellersprite `ss-main` | 2026-07-12 | Amazon US | estimated、synthetic，近 30 天 | competition、risk；不代表实际账户 CPC 或转化 |
| 付费流量占比 | 38% | sif `sif-main` | 2026-07-12 | Amazon US | estimated、synthetic，近 30 天 | competition、risk；仅判断流量结构和广告依赖，不进入 demand |
| 供货价 | 18 CNY | synthetic_1688_supply `supply-main` | 2026-07-12 | 1688 合成样本 | declared、synthetic | margin/capability_fit；不证明 US 需求 |
| MOQ | 100 件 | synthetic_1688_supply `supply-main` | 2026-07-12 | 1688 合成样本 | declared、synthetic | capability_fit/risk；需真实询盘复核 |
| 单重 | 220 g | synthetic_1688_supply `supply-main` 的来源范围；候选 evidence 未逐字段回指 | 2026-07-12 | 1688 合成样本 | declared、synthetic，字段级溯源不完整 | 仅作风险提示，不进入精确运费公式 |
| 交期 | 12 天 | synthetic_1688_supply `supply-main` 的来源范围；候选 evidence 未逐字段回指 | 2026-07-12 | 1688 合成样本 | declared、synthetic，字段级溯源不完整 | 仅作供给提示，需人工核实 |
| 首批已知投入 | 8,200 CNY | synthetic_cost_fixture `cost-main` 的来源范围；候选 evidence 未逐字段回指 | 2026-07-12 | Amazon US 评测口径 | derived、synthetic，字段级溯源不完整 | 仅用于合成硬约束核对，真实采购前需重算 |
| 已知成本口径毛利 | 42% | synthetic_cost_fixture `cost-main` | 2026-07-12 | Amazon US 评测口径 | derived、synthetic | margin；不得称实际毛利 |

费用、头程/FBA、退货、税费、认证与合规要求没有可用的真实事实清单或公式覆盖，均为“需人工核实”；未补写任何费率或费用数字。

## 5. 候选清单与评分

| rank | candidate_id | 状态 | demand | competition | margin | capability_fit | risk | 总分 | 置信度 |
|---:|---|---|---:|---:|---:|---:|---:|---:|---|
| 1 | `ss-sif-complete` | 有条件推荐最小验证 | 4.0 | 3.5 | 4.0 | 4.0 | 3.0 | 3.8 | 低至中：全部市场和供给数字为合成数据，真实链路未验证 |

总分 = 4.0×25% + 3.5×15% + 4.0×20% + 4.0×25% + 3.0×15% = 3.775，按规则保留一位为 3.8。

- demand 4.0：SellerSprite 合成搜索量与估算销量形成同一直接市场数据源内的需求信号；没有第二个独立需求来源，SIF 流量占比明确不用于补强需求，因此不能给高确信 5 分。
- competition 3.5：SellerSprite 合成 Top10 集中度和 CPC，与 SIF 合成付费流量占比共同支持“可测试但有广告依赖”；两源职责不同，未把流量结构夸大成市场规模。
- margin 4.0：已知成本口径毛利 42% 高于画像 35% 偏好，首批合成投入低于资金上限；平台费、物流、广告、退货、税费尚未完整纳入，不能称实际毛利。
- capability_fit 4.0：画像中的 1688 采购能力、英语能力与高内容能力匹配；广告能力仅 3，且两人团队需控制 SKU 和素材负担。
- risk 3.0：产品表面上未命中禁做属性，合成重量与交期尚可进入小样验证；真实合规、侵权检索、耐用性、夹毛/清洁体验、退货与完整现金周期均缺失。

## 6. 个性化归因

### 为什么适合你

- `profile.capabilities.supply_chain=1688采购` 与合成 MOQ 100、供货价 18 CNY 的小批量供给方向匹配。
- `profile.capabilities.content_skill=5`，可用宠物毛发清理的前后对比展示功能改良，符合 `profile.preferences.product_style=[轻创新, 功能改良, 情绪价值]`。
- 合成首批已知投入 8,200 CNY 低于 `profile.constraints.capital_per_sku_max=30000 CNY`，合成已知成本口径毛利 42% 高于 `profile.preferences.margin_floor_pct=35`。

### 为什么不适合你

- `profile.capabilities.ad_skill=3` 只是中等，而 SIF 合成付费流量占比为 38%，存在一定广告依赖；真实 CPC 与转化未验证前不宜放量。
- `profile.capabilities.team_size=2`，若滚筒耐用性、清洁维护或夹毛体验带来售后，会挤占小团队精力。
- `profile.constraints.cash_cycle_tolerance_days=45`，目前只有合成交期 12 天，没有生产、头程、入仓和销售周转的完整周期，无法确认现金周期适配。

### 主要风险

- 事实风险：所有数据均为 synthetic demo；SellerSprite 销量、搜索量、集中度和 CPC 是虚构估算，SIF 只提供虚构流量结构；真实市场链路未验证。
- 经验风险：可感知差异若只靠图片而缺少结构/套装改良，可能落入价格竞争；这是 Amazon 策略经验，不是事实数字。
- 待核实：真实关键词搜索量与销量趋势、Top10 分母与集中度、CPC 匹配方式、自然/广告流量口径、真实报价/MOQ/重量/交期、FBA/佣金/头程/退货/税费、合规与侵权、完整现金周期。

### 下一步最小验证

1. 用 SellerSprite 只读产品/市场/关键词/集中度/CPC 能力复核同一 Amazon US 节点、同一 30 天窗口，并保留工具名与口径。
2. 用 SIF 只读流量/广告分析仅复核自然与付费流量结构，不拿它替代需求证据。
3. 对 3 家 1688 供应商询样，核对报价、MOQ、220 g 单重、12 天交期、滚轴寿命与可清洁性；供给结论不得外推 Amazon 需求。
4. 依据 references 中已核实的费用/公式或人工确认数据补齐平台费、头程/FBA、广告、退货、税费与合规，再重算实际可用的成本口径和 45 天现金周期。

## 7. 被过滤与待核实候选

被过滤品：无（任务只包含一个候选，未命中已知一票否决项）。

`blocked_pending_data`：无。候选可进入最小验证，但真实投放或采购前仍必须完成上述人工核实；“无 blocked”不等于数据已经真实验证。

## 8. 依据分类与下一步

- 数据依据：仅上述四个 synthetic sources；逐项边界见数据表。
- 画像依据：`sellers/eval-content/profile.yaml`、`sellers/eval-content/sop.md`。
- 经验依据：`references/platforms/amazon.md` 仅用于分析路径与风险提示，不提供事实数字。
- 待核实项：真实市场数据链路、完整成本、合规/侵权、现金周期和供应商样品表现。

建议维持“有条件推荐最小验证”，不据此直接上架、调价、建广告、改库存或采购放量。
