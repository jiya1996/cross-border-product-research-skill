# TikTok US learned-transfer effect-only 需求假设报告

## 任务与结论边界

- seller_id: `eval-content`
- 平台适配器: `tiktok`；市场: `US`
- 运行模式: `synthetic_demo` / effect-only 合成假设实验
- conclusion_type: `demand_hypothesis_only`
- 数据采集日期: 2026-07-12；报告日期: 2026-07-13
- 结论仅用于检验硬约束与 learned 规则迁移，不代表真实市场需求、竞争、成本或经营结果。真实市场数据链路未验证。

## 卖家画像摘要与实际权重

目标市场与平台符合 `profile.constraints.target_marketplaces=[tiktok-us, amazon-us]`、`profile.constraints.target_countries=[US]`。受控硬约束采用 `profile.constraints.capital_per_sku_max=30000 CNY`、`profile.constraints.cash_cycle_tolerance_days=45` 及 SOP 的首批投入红线。内容匹配引用 `profile.capabilities.content_skill=5`；风险判断引用 `profile.preferences.risk_appetite=balanced`。

实际权重为 demand 25%、competition 15%、margin 20%、capability_fit 25%、risk 15%。本实验缺完整单位成本，margin 与 total_score 均为 N/A；因此只展示 demand、competition、capability_fit、risk 四维暂定判断，不以不完整分母计算总分。

Learned 规则状态：active 0 条，proposed 1 条，revoked/expired/superseded 各 0 条。`learned_tiktok_same_density_diff_001` 为 `status: proposed`，不是唯一可执行状态 `active`，因此不影响任何候选分数。`pre_rule_competition_score` 作为受控规则应用前基线原值保留；本次 `rule_effects` 为空。

## 数据源、操作与缺口

| provider | variant | role | mode | read operation | sample boundary |
|---|---|---|---|---|---|
| repository_fixture | effect_only_learned_transfer | direct_market_data | synthetic_demo | `read references/demo-data/eval-learned-transfer-candidates.md` | 4 个合成候选，仅限 TikTok US 假设实验 |
| seller_profile_files | confirmed_profile_sop | capability_context | synthetic_demo | 读取 profile、SOP、最近 3 条 decisions | 仅限 `eval-content` 个性化归因 |

collector: 无。transformation: 无。实际请求且被拒绝的写操作: 无。只读检查显示 synthetic demo 可用、live MCP 查询未验证。

主要缺口：TikTok 真实热门视频、互动、评论、转化与物流数据；完整单位成本（平台费、头程/尾程、广告、退货、税费及适用合规成本）；真实供应链稳定性。合成 `supply_price_cny` 不是完整单位成本，不能形成 margin。

## 过滤与候选清单

4 个候选均为 `hard_constraint_status=pass_synthetic`，受控首批投入 5000–6500 CNY 均未超过 30000 CNY，受控现金周期 30–35 天均未超过 45 天，且未命中禁做类目/属性。它们因此通过本 effect-only 实验的受控硬过滤；这些数值不得外推真实经营。

| rank | candidate_id | candidate | status | demand | competition | margin | capability_fit | risk | total_score | confidence |
|---:|---|---|---|---:|---:|---|---:|---:|---|---|
| 1 | lr-d88 | Stackable shoe slot | 暂定推荐 | 4 | 3 | N/A | 4 | 3 | N/A | 低，合成假设 |
| 2 | lr-a17 | Compact keyboard brush | 暂定推荐 | 3 | 2 | N/A | 5 | 4 | N/A | 低，合成假设 |
| 3 | lr-c63 | Silicone cord label set | 暂定推荐 | 3 | 2 | N/A | 5 | 4 | N/A | 低，合成假设 |
| 4 | lr-b42 | Fold-flat tablet rest | 暂定推荐 | 3 | 2 | N/A | 5 | 4 | N/A | 低，合成假设 |

排序仅是四维、低置信度暂定顺序：lr-d88 的受控竞争基线较高且场景明确；其余候选以三秒演示清晰度作次序判断。由于 margin 缺失，不能形成精确商业排序或 total_score。

## 逐候选个性化归因

### lr-d88 — Stackable shoe slot

- 为什么适合你：鞋柜空间前后对比符合 `sop.判断习惯` 的“三秒内展示痛点和前后对比”，并匹配 `profile.capabilities.content_skill=5`。
- 为什么不适合你：尺码适配可能带来退货，与 `profile.preferences.risk_appetite=balanced` 的稳健边界存在张力；180g、25x10x6cm 也需验证 `profile.constraints.logistics_modes=[FBA,轻小件直发]` 的真实适配。
- 主要风险：事实风险仅有合成的尺码观察项；经验风险为适配解释与售后；待核实真实退货、物流、完整成本和 TikTok 转化。
- 下一步最小验证：小样测试不同鞋型适配，并补完整单位成本与真实 TikTok US 素材/评论数据。

### lr-a17 — Compact keyboard brush

- 为什么适合你：键盘缝隙清洁前后对比直接匹配 `sop.判断习惯`，且 `profile.capabilities.content_skill=5` 支持快速演示素材。
- 为什么不适合你：合成信号显示同款密度高、差异化空间低，和 SOP“同款过多时必须给出可感知差异”的要求冲突。
- 主要风险：事实风险为同款密度合成信号；经验风险为价格同质化；待核实结构/套装差异、完整成本与真实需求。
- 下一步最小验证：先做结构或套装差异盲测，再核实完整单位成本和 TikTok US 真实互动/转化。

### lr-c63 — Silicone cord label set

- 为什么适合你：线缆识别前后对比符合 `profile.preferences.product_style=[轻创新,功能改良,情绪价值]` 与 `profile.capabilities.content_skill=5`。
- 为什么不适合你：外观差异小，未满足 SOP 对高同款密度候选的可感知差异要求。
- 主要风险：事实风险为合成同款密度；经验风险为低辨识度；待核实标识耐久、完整成本和真实需求。
- 下一步最小验证：测试颜色/图标/套装差异能否被用户快速识别，并补成本与真实平台数据。

### lr-b42 — Fold-flat tablet rest

- 为什么适合你：展开收纳一镜到底符合 TikTok 视觉演示，也匹配 `profile.capabilities.content_skill=5`。
- 为什么不适合你：同款多且结构差异小，直接触及 SOP 的差异化要求；两人团队 `profile.capabilities.team_size=2` 不宜承担复杂的多结构迭代。
- 主要风险：事实风险为价格竞争合成标签；经验风险为结构同质化；待核实承重/稳定性、完整成本和真实需求。
- 下一步最小验证：用小样验证承重和折叠寿命，并补完整成本及 TikTok US 真实内容数据。

## 被过滤与 blocked_pending_data

- 被过滤品：无。
- blocked_pending_data：无。根据本 effect-only fixture 的特殊契约，受控硬约束已可判断；完整单位成本缺失只让 margin 与 total_score 保持 N/A，并进入人工核实，不重复阻塞候选。

## Learned 规则审计

`learned_tiktok_same_density_diff_001` 虽在四个新候选中有三个满足其结构化标签子集，但其状态为 `proposed`，不得参与打分。故 lr-a17、lr-b42、lr-c63 的 competition 均保持 `pre_rule_competition_score=2`；lr-d88 不满足完整标签子集且保持 3。没有生成 active rule effect，亦无需生成 effect 审计行。

## 依据分类与人工核实

- 数据依据：`references/demo-data/eval-learned-transfer-candidates.md` 的合成受控字段，仅限本实验。
- 画像依据：profile、SOP 与最近三条拒绝决策；拒绝记录只能支持 proposed 规则展示，未获人工确认不能执行。
- 经验依据：`references/platforms/tiktok.md` 的三秒演示、前后对比和内容素材策略，不作为真实市场事实。
- 需人工核实：每个候选的完整单位成本或毛利；平台费、物流、广告、退货、税费与合规成本；真实 TikTok US 需求、竞争和转化；供应链稳定性。

## 成本纳入初筛后的排序对照

忠实执行段为上表的四维暂定顺序。压力测试段无法计算 margin 或 total_score：若补齐完整成本后任一候选的毛利低于 `profile.preferences.margin_floor_pct=35`，则应从暂定推荐移出；若均达到红线，再以同一完整分母重新计算总分并排序。目前成本纳入后的对照统一为“待成本或毛利核实”，不编造数字。
