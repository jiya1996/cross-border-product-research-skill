# Amazon US 候选评估：linkfox-assisted

## 1. 任务与运行模式

- seller_id：`eval-content`
- 平台适配器：Amazon US（`amazon` / `US`）
- 分析范围：仅 `candidate_id=linkfox-assisted`
- 数据模式：`synthetic_demo`
- 批次：`eval-tool-role-boundaries-20260712`
- 采集时间：2026-07-12T00:00:00Z
- 结论边界：本报告只用于隔离评测，全部市场、成本与供给数字均为虚构合成数据；真实市场数据链路未验证。

## 2. 卖家画像摘要与评分权重

硬约束来自 `sellers/eval-content/profile.yaml` 与 SOP：允许 `amazon-us` / US；首批已知投入上限为 30000 CNY；禁做食品、医疗器械、儿童安全用品，以及液体、粉末、刀具、强磁、侵权图案、大件易碎。候选为 Home cleaning 手动织物除毛刷，输入未显示命中禁做项；已知首批投入 6900 CNY，未超过上限。

能力与偏好：`profile.capabilities.supply_chain=1688采购`、`profile.capabilities.content_skill=5`、`profile.capabilities.ad_skill=3`、团队 2 人；偏好轻创新、功能改良、情绪价值；已知成本口径毛利红线为 `profile.preferences.margin_floor_pct=35`。

实际权重采用画像覆盖值：demand 25%、competition 15%、margin 20%、capability_fit 25%、risk 15%。画像中唯一 learned 规则 `learned_tiktok_same_density_diff_001` 状态为 `proposed`，且范围为 TikTok；不参与本次 Amazon 评分。其他状态规则数量：revoked 0、expired 0、superseded 0；active 0。

## 3. 数据源、工具角色与样本边界

| provider | provider_variant | source_role | 实际只读操作 | 支持维度 | 窗口/口径 |
|---|---|---|---|---|---|
| synthetic_amazon_market | — | direct_market_data | 读取 fixture 中 `amazon-main` 对 `linkfox-assisted` 的证据 | demand, competition, risk | 合成过去 30 天；虚构离线评测值 |
| synthetic_cost_fixture | — | official_reference | 读取 fixture 中 `cost-main` 的已知成本公式结果 | margin, risk | 虚构评测公式；非完整实际毛利 |
| synthetic_1688_supply | — | direct_market_data | 读取 fixture 中 `supply-main` 的供给快照 | margin, capability_fit, risk | 合成当前报价；虚构供应商声明 |

- collector：无。
- transformations：`linkfox_creative`。它只表示图片与内容生产能力观察，不是事实 provider，也不证明销量、搜索需求、利润或真实转化。
- 本次未请求任何写操作，因此无实际被拒绝操作。
- 数据接入自检显示 sellersprite、SIF、Sorftime、领星实时查询均未验证；仅 synthetic demo 可用。
- 样本仅包含一个指定候选，不代表 Amazon US 全类目或全网分布。

数据缺口：输入没有给出 CPC、评论数/评分、关键词趋势、广告流量占比、交期、完整物流尺寸、完整平台费/头程/FBA/广告/退货/税费，也没有可核实的具体合规结论。`price_usd=18.99`、`moq=100`、`unit_weight_g=140` 与 `first_batch_known_cost_cny=6900` 出现在候选 facts 中，但未列入逐字段 evidence；本报告只将其用于候选描述与硬约束审慎检查，不把它们扩展成精确成本公式。

## 4. 过滤结果

`linkfox-assisted` 未被过滤：平台与市场允许；类目及已知属性未命中禁做边界；合成输入声明首批已知投入 6900 CNY，低于 `profile.constraints.capital_per_sku_max=30000 CNY`；已知成本口径毛利 40%，高于 `profile.preferences.margin_floor_pct=35`。

注意：这不是完整毛利或真实合规放行。未知费用与合规项列入风险和人工核实，不编造数字。

## 5. 候选清单与评分

| candidate_id | 状态 | demand | competition | margin | capability_fit | risk | 总分 | 置信度 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| linkfox-assisted | 推荐进入最小验证 | 4.0 | 4.0 | 4.0 | 5.0 | 4.0 | 4.3 | 中（仅合成数据且成本不完整） |

总分 = 4.0×0.25 + 4.0×0.15 + 4.0×0.20 + 5.0×0.25 + 4.0×0.15 = 4.25，按 1 位小数记为 4.3。

- demand 4.0：合成 Amazon US 数据给出月销量估算 1200 件与关键词搜索量 13000；两者同属一个 `synthetic_amazon_market` 快照，未达到真实双来源交叉验证，不能解释为真实市场规模。
- competition 4.0：合成 Top10 商品集中度为 29%，显示头部集中度在该虚构样本中不高；但缺评论护城河、CPC、品牌/卖家集中度和 Listing 差异化实证。
- margin 4.0：合成采购价为 11 CNY，已知成本口径毛利为 40%，高于画像 35% 红线；缺完整费用，因此只能称“已知成本口径毛利”。
- capability_fit 5.0：`profile.capabilities.supply_chain=1688采购` 与合成供给来源匹配；`profile.capabilities.content_skill=5` 适合制作除毛前后对比素材。`linkfox_creative` 仅作为图片/内容生产能力观察，不提升 demand、competition、margin 或转化判断。
- risk 4.0：已知候选为轻量、手动、非液体/粉末且首批投入低于上限；但合规、知识产权、完整物流和退货风险仍需核实。

## 6. 个性化归因

### 为什么适合你

- `profile.capabilities.supply_chain=1688采购`，与合成供给快照中的 1688 采购路径相符。
- `profile.capabilities.content_skill=5`，手动织物除毛刷可以用清晰的使用前后画面表达功能，契合较强内容制作能力。
- `profile.preferences.product_style` 包含“功能改良”和“轻创新”，候选可围绕刷面结构、收纳清洁方式或套装做可感知改良。
- 合成已知成本口径毛利 40% 高于 `profile.preferences.margin_floor_pct=35`，合成首批已知投入 6900 CNY 低于资金上限 30000 CNY。

### 为什么不适合你

- Amazon 搜索电商需要关键词、评论与广告门槛验证；当前缺 CPC、评论护城河和真实搜索趋势，而 `profile.capabilities.ad_skill=3` 仅为中等，若真实广告依赖高，团队可能承压。
- `profile.team_size=2`，若产品出现较高退货、刷面耐用性投诉或需要大量客服解释，小团队的售后负担可能放大。
- SOP 要求同款多时必须有结构、套装或内容上的可感知差异；当前只有合成集中度，尚未证明真实同款密度和差异化可守住。

### 主要风险

- 事实风险：当前数字均为 synthetic demo；销量与搜索量为 estimated；完整费用、评论门槛、广告依赖、交期与合规结论缺失。
- 经验风险：Amazon 同质化清洁工具可能依赖评论积累与广告；这是平台策略经验，不是当前候选事实。
- 待核实：真实 Amazon US 搜索量/趋势、销量口径、Top10 集中度、评论分布、CPC、自然/广告流量、完整成本、物流尺寸重量、退货原因、商标/专利和适用合规要求。

### 下一步最小验证

1. 用两个独立只读市场来源复核 Amazon US 关键词需求、趋势、评论分布、集中度和 CPC，并保留各自窗口与口径。
2. 获取 1688 样品并验证刷毛效果、耐用性、清洁方式、包装后尺寸重量及可做的结构/套装差异。
3. 按 references 覆盖的事实费率或人工核实报价补齐采购、平台费、头程、FBA、广告、退货、税费与合规成本，再复算完整成本口径；未覆盖数字继续标为“需人工核实”。
4. 仅用 `linkfox_creative` 做图片与内容原型测试，评价素材清晰度和生产效率；不得把素材结果当作需求、利润或真实转化证据。

## 7. 被过滤品与待核实组

- 被过滤品：无（任务只分析一个候选）。
- `blocked_pending_data`：无。fixture 将候选标记为 `missing_fields=[]`，且已有足够合成字段完成评测评分；上述真实数据缺口通过中置信度和人工核实项表达。

## 8. 依据分层与结论

- 数据依据：`references/demo-data/eval-tool-role-boundaries.json` 中 `amazon-main`、`cost-main`、`supply-main` 对 `linkfox-assisted` 的合成证据。
- 画像依据：`sellers/eval-content/profile.yaml`、`sellers/eval-content/sop.md` 与最近 3 条决策记录。历史决策均为 TikTok 拒绝记录，不直接改写本次 Amazon 分数。
- 经验依据：`references/platforms/amazon.md` 的搜索需求、评论护城河、广告依赖和差异化分析框架。
- 需人工核实：所有真实市场数字、完整费用、合规、知识产权、物流、退货与样品质量。

结论：在合成评测口径下，`linkfox-assisted` 可作为 Amazon US 的最小验证候选，暂定总分 4.3/5.0；这不是商业上架结论。LinkFox 仅记录为 `linkfox_creative` 转换/创意能力观察，未作为任何事实来源，也未用于证明销量、搜索需求、利润或真实转化。
