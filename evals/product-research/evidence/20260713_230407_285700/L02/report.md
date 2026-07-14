# TikTok US learned rule effect-only 合成选品报告

## 任务与结论边界

- seller_id：`eval-content`
- 平台适配器：TikTok US
- 运行模式：`synthetic_demo`、effect-only、hypothesis-only
- 结论类型：`not_applicable`（任务要求 hypothesis-only，但未显式指定枚举值 `demand_hypothesis_only` 或 `supply_validation_only`）
- 本报告只检验 active learned 规则能否从历史拒绝样本迁移到新候选；所有候选与数字均为合成输入，不构成真实经营建议。
- 真实 TikTok US 市场数据链路与 1688 供给链路均未验证。需求分、能力匹配分和风险分只是基于合成描述与已确认画像的暂定假设；`pre_rule_competition_score` 是受控的规则应用前基线，不是真实市场评分。

## 卖家画像摘要与实际权重

- 硬约束：`profile.constraints.target_marketplaces` 包含 `tiktok-us`；`capital_per_sku_max=30000 CNY`；`cash_cycle_tolerance_days=45`；禁做食品、医疗器械、儿童安全用品，以及液体、粉末、刀具、强磁、侵权图案、大件易碎。
- 能力：`profile.capabilities.content_skill=5`，`supply_chain=1688采购`，团队规模为 2。
- 偏好：`profile.preferences.product_style=[轻创新, 功能改良, 情绪价值]`，竞争容忍度为 medium，毛利底线为 35%。
- SOP：TikTok 优先三秒内展示痛点和前后对比；同款多时须有结构、套装或内容差异。
- 实际权重：demand 25%、competition 15%、margin 20%、capability_fit 25%、risk 15%，来自 `profile.preferences.scoring_weights`，覆盖默认权重。
- learned 状态：active 1 条；proposed/revoked/expired/superseded 均为 0 条。

## 数据源、样本边界与访问审计

| provider | variant | source_role | read operation | 采集日期 | 市场/窗口 | synthetic |
|---|---|---|---|---|---|---|
| repository_fixture | learned_transfer_candidates | direct_market_data | `read references/demo-data/eval-learned-transfer-candidates.md` | 2026-07-12 | TikTok US；单次 4 候选受控实验 | true |
| seller_profile_files | profile_sop_decisions | capability_context | 读取 profile、SOP、最近 3 条决策 | 2026-07-13 本次读取 | seller_id=eval-content | true |

- collector：无。
- transformation：无。
- 本次没有请求任何写操作，因此 denied operations 为空。
- 样本仅含 4 个合成候选，不代表 TikTok US 市场全貌；没有热门视频、真实互动/评论、转化、物流方案或 1688 供应商验证。

## 数据完整性与受控硬约束

四个候选的 `controlled_initial_investment_cny` 均低于 30000 CNY，`controlled_cash_cycle_days` 均不超过 45 天，且 `hard_constraint_status=pass_synthetic`。因此它们在本 effect-only 实验中均可进入暂定推荐，不进入 `blocked_pending_data`。这些字段只证明受控硬约束可判定，不外推真实经营。

完整单位成本缺失，包括平台费、头程/尾程、广告、退货、税费以及可能的合规成本；因此所有候选的 margin 与 total_score 均为 N/A。采购单价本身不足以计算完整毛利，也不用于毛利红线过滤。

四维假设口径：demand 依据合成需求描述暂记 3；capability_fit 依据三秒内容钩子与 `profile.capabilities.content_skill=5` 暂记 5；普通低风险描述暂记 risk=4，鞋槽尺码适配观察项暂记 risk=3；competition 只采用受控基线并执行 active learned delta。除 competition 的受控 effect 外，其余分值均是 hypothesis-only，不是市场事实评分。

## Active learned 规则证据复核

`learned_tiktok_same_density_diff_001` 状态为 active，作用域匹配 TikTok US，条件标签为 `same_product_density_high` 与 `differentiation_space_low`，动作仅为 competition `delta=-1`。其三条 evidence 均已重读：全部为 rejected、显式含两个条件标签、来自三个独立决策会话，来源报告路径与候选 ID 均可对应。规则只对子集匹配的当前候选生效。

| rule_id | candidate_id | dimension | delta | before | after |
|---|---|---|---:|---:|---:|
| learned_tiktok_same_density_diff_001 | lr-a17 | competition | -1 | 2 | 1 |
| learned_tiktok_same_density_diff_001 | lr-b42 | competition | -1 | 2 | 1 |
| learned_tiktok_same_density_diff_001 | lr-c63 | competition | -1 | 2 | 1 |

聚合说明：每个命中候选在 competition 维度仅命中这一条 active 规则，aggregate delta 均为 -1，先汇总后只 clamp 一次。`lr-d88` 缺少 `differentiation_space_low` 标签，不命中，competition 保持受控基线 3。

## 候选清单与四维暂定推荐

因 margin 缺失且 total_score 为 N/A，不能给出完整加权精确排名。以下仅按已知四维作暂定分组：`lr-d88` 的 competition 较高，列为暂定第 1；其余三项四维同分，并列暂定第 2。

| rank | candidate_id | product | demand | competition | margin | capability_fit | risk | total_score | 置信度 |
|---:|---|---|---:|---:|---|---:|---:|---|---|
| 1 | lr-d88 | Stackable shoe slot | 3 | 3 | N/A | 5 | 3 | N/A | 低；合成假设 |
| 2 | lr-a17 | Compact keyboard brush | 3 | 1 | N/A | 5 | 4 | N/A | 低；合成假设 |
| 2 | lr-b42 | Fold-flat tablet rest | 3 | 1 | N/A | 5 | 4 | N/A | 低；合成假设 |
| 2 | lr-c63 | Silicone cord label set | 3 | 1 | N/A | 5 | 4 | N/A | 低；合成假设 |

## 逐候选个性化归因

### lr-d88 — Stackable shoe slot

- 为什么适合你：鞋柜空间前后对比符合 SOP 的“三秒内展示痛点和前后对比”，也能发挥 `profile.capabilities.content_skill=5`；6500 CNY 与 35 天在受控实验中分别满足资金与现金周期上限。
- 为什么不适合你：`profile.preferences.competition_tolerance=medium`，而输入仍标记同款密度高；尺码适配会增加两人团队的说明和售后压力。
- 主要风险：事实风险为完整成本和真实物流数据缺失；经验风险为尺码适配可能造成退换；待核实真实 TikTok 需求、同款密度、尺寸/运费与退货率。
- 下一步最小验证：核实完整单位成本与毛利，并用小样测试不同鞋型适配和三秒空间对比素材。

### lr-a17 — Compact keyboard brush

- 为什么适合你：清洁前后对比匹配 SOP 的短视频判断习惯，且 `profile.capabilities.content_skill=5` 支持快速制作演示内容；5200 CNY 与 30 天通过受控硬约束。
- 为什么不适合你：同时命中同款密度高和差异化空间小，与 SOP“同款过多时必须有可感知差异”冲突，active learned 规则已将 competition 从 2 降至 1。
- 主要风险：事实风险为完整成本与真实市场数据缺失；经验风险为常规普货容易价格竞争；待核实真实互动、转化、物流成本和毛利。
- 下一步最小验证：先核实完整单位成本与毛利，再验证刷头结构或套装能否形成可感知差异。

### lr-b42 — Fold-flat tablet rest

- 为什么适合你：展开收纳一镜到底适配 `profile.capabilities.content_skill=5`，也符合 `profile.preferences.product_style` 中的功能改良；5600 CNY 与 35 天通过受控硬约束。
- 为什么不适合你：结构差异小且同款多，不满足 SOP 对同款差异化的要求；active learned 规则将 competition 从 2 降至 1，另有 price_competition 标签但没有对应 active 规则，未额外扣分。
- 主要风险：事实风险为单位经济与真实竞争数据缺失；经验风险为价格竞争；待核实承重、稳定性、物流、退货与毛利。
- 下一步最小验证：核实完整单位成本与毛利，并对折叠结构、承重和差异化镜头做小样测试。

### lr-c63 — Silicone cord label set

- 为什么适合你：线缆识别前后对比符合 SOP 的三秒内容逻辑，也贴合 `profile.preferences.product_style=[轻创新, 功能改良, 情绪价值]`；5000 CNY 与 30 天通过受控硬约束。
- 为什么不适合你：外观差异小且同款密度高，与 SOP 的差异化红线相悖；active learned 规则将 competition 从 2 降至 1。
- 主要风险：事实风险为完整成本与真实需求缺失；经验风险为低客单常规品容易同质化；待核实标签耐久性、真实互动、履约成本与毛利。
- 下一步最小验证：核实完整单位成本与毛利，并测试颜色编码、定制字样或套装组合是否能形成差异。

## 被过滤品与 blocked_pending_data

- 被过滤品：无。四个候选均通过本实验明确提供的受控硬约束。
- blocked_pending_data：无。按 effect-only 契约，完整单位成本缺失只使 margin 与 total_score 保持 N/A，并进入人工核实，不重复放入 blocked_pending_data。

## 依据分层与人工核实

- 数据依据：仅 `references/demo-data/eval-learned-transfer-candidates.md` 的合成 fixture。
- 画像依据：`sellers/eval-content/profile.yaml`、`sop.md` 与最近 3 条 decisions。
- 经验依据：`references/platforms/tiktok.md`，仅用于内容与风险分析框架。
- manual verification：核实每个候选的完整单位成本与毛利，至少覆盖采购、平台费、头程/尾程、广告、退货、税费及适用合规成本；并补真实 TikTok US 视频、互动、评论、转化、竞争及物流证据。

## 下一步建议

在真实市场与完整成本数据补齐前，不作上架决定。优先验证 `lr-d88` 的尺码适配与完整毛利；其余三个候选只有在找到结构、套装或内容层面的可感知差异后再进入小样测试。
