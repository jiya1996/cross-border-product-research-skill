# TikTok US effect-only learned transfer 合成实验

## 任务与结论边界

- seller_id：`eval-content`
- 平台适配器：TikTok US
- 运行模式：`synthetic_demo`，hypothesis-only 四维暂定推荐
- 结论边界：输入是 2026-07-12 的隔离合成 fixture，只用于检验 learned 规则迁移效果，不是实时市场、供应链或商业可行性验证。真实市场数据链路未验证。
- `controlled_initial_investment_cny`、`controlled_cash_cycle_days` 与 `hard_constraint_status` 仅用于本次受控硬约束判断，不外推真实经营。
- 完整单位成本缺失，因此所有候选的 `margin` 与 `total_score` 均为 `N/A`；本报告不输出最终商业机会分。

## 卖家画像摘要与实际权重

- 允许范围：`profile.constraints.target_marketplaces` 包含 `tiktok-us`，`profile.constraints.target_countries` 包含 `US`。
- 硬约束：`profile.constraints.capital_per_sku_max=30000 CNY`；`profile.constraints.cash_cycle_tolerance_days=45`；禁做类目和属性按 profile 与 SOP 执行。
- 能力：`profile.capabilities.content_skill=5`、`profile.capabilities.supply_chain=1688采购`、团队 2 人。
- 偏好：`profile.preferences.product_style=[轻创新, 功能改良, 情绪价值]`，风险偏好 balanced。
- 实际权重：demand 25%、competition 15%、margin 20%、capability_fit 25%、risk 15%，来自 `profile.preferences.scoring_weights`，覆盖默认权重。
- SOP 内容要求：TikTok 优先三秒内展示痛点和前后对比；同款过多时须有可感知差异。

## 数据源、操作与缺口

| provider | variant | role | read_operations | collected_at | market / window | boundary |
|---|---|---|---|---|---|---|
| repository_fixture | effect_only_learned_transfer | direct_market_data（仅合成实验） | 读取 `references/demo-data/eval-learned-transfer-candidates.md` | 2026-07-12 | TikTok US / 合成静态批次 | 仅支持需求、竞争、能力适配和风险假设；不支持真实经营决策 |
| seller profile / SOP | capability context | capability_context | 读取 profile、SOP 与最近 3 条 decisions | 2026-07-13 本次运行 | seller_id=eval-content | 只用于个性化约束与归因 |

- collector：无。
- transformation：无。
- 外部工具：无；执行 `python3 scripts/check_data_access.py --json`，结果为 synthetic demo ready，live query 未验证。
- 被拒绝写操作：无。本次没有请求平台写操作。
- 样本边界：4 个预设候选的便利合成样本，不代表 TikTok US 市场全貌。
- 主要缺口：完整单位成本、平台费、物流、广告、退货、税费、合规/认证、真实 TikTok 热门视频/评论/转化窗口、真实供应链与物流轨迹均需人工核实。

## Learned 规则状态与 effect 审计

画像共有 1 条 learned 规则：`learned_tiktok_same_density_diff_001`，状态为 `proposed`；`active=0`，`proposed=1`，其他状态均为 0。按 Skill，只有 `active` 可执行，所以该 proposed 规则**不影响任何分数**。即使 lr-a17、lr-b42、lr-c63 的 `rule_tag_ids` 满足该规则的两个结构化条件标签，也不应用 `delta=-1`。

`pre_rule_competition_score` 是本受控实验指定的规则应用前基线。因为没有 active effect，最终 competition 分与该基线完全相同：lr-a17=2、lr-b42=2、lr-c63=2、lr-d88=3。`rule_effects` 为空，不生成 active-rule 审计表。

## 过滤结果

四个候选的 `hard_constraint_status=pass_synthetic`；受控首批投入分别为 5200、5600、5000、6500 CNY，均不超过 `profile.constraints.capital_per_sku_max=30000 CNY`；受控现金周期分别为 30、35、30、35 天，均不超过 `profile.constraints.cash_cycle_tolerance_days=45`。输入未标记 profile/SOP 禁做类目或属性。因此无候选被过滤。

完整成本缺失在本 effect-only 实验中按明确任务约定进入人工核实，不把候选放入 `blocked_pending_data`。`blocked_pending_data` 为空。

## 候选清单与四维暂定排序

分数均为 0–5 的合成假设分。四维展示顺序仅用于暂定优先级；由于 margin 缺失，`total_score=N/A`，不能形成完整加权商业排名。

| 暂定顺序 | candidate_id | 候选 | demand | competition | margin | capability_fit | risk | total_score | 置信度 |
|---:|---|---|---:|---:|---|---:|---:|---|---|
| 1 | lr-a17 | Compact keyboard brush | 4 | 2 | N/A | 5 | 4 | N/A | 低（合成假设） |
| 2 | lr-b42 | Fold-flat tablet rest | 3 | 2 | N/A | 5 | 4 | N/A | 低（合成假设） |
| 3 | lr-c63 | Silicone cord label set | 3 | 2 | N/A | 5 | 4 | N/A | 低（合成假设） |
| 4 | lr-d88 | Stackable shoe slot | 3 | 3 | N/A | 4 | 3 | N/A | 低（合成假设） |

lr-b42 与 lr-c63 的四个已评分维度相同，顺序只用于展示，不代表可复算的商业优劣。所有 demand 信号都是 fixture 中的合成描述，未由真实 TikTok 数据交叉验证。

## 逐候选归因

### 1. lr-a17 — Compact keyboard brush

**为什么适合你：** 键盘缝隙清洁前后对比符合 SOP“三秒内展示痛点和前后对比”，也匹配 `profile.capabilities.content_skill=5`；桌面清洁属于功能改良方向，贴合 `profile.preferences.product_style`。

**为什么不适合你：** 合成输入明确标记同款密度高、差异化空间低，与 SOP“同款过多时必须有可感知差异”冲突；因此 competition 仅为基线 2。proposed learned 规则没有进一步扣分。

**主要风险：** 事实风险：完整成本与真实市场数据缺失。经验风险：常规清洁普货可能陷入同质内容与价格竞争。待核实：单位落地成本、真实同款密度、内容转化和知识产权。

**下一步最小验证：** 核实一套完整单位经济模型，并用少量真实 TikTok 素材样本验证三秒钩子与可感知结构/套装差异。

### 2. lr-b42 — Fold-flat tablet rest

**为什么适合你：** 展开收纳一镜到底适配 `profile.capabilities.content_skill=5` 和 SOP 的快速演示要求；结构改良符合 `profile.preferences.product_style=[轻创新, 功能改良, 情绪价值]`。

**为什么不适合你：** 输入标记同款很多且结构差异小，直接触碰 SOP 的差异化要求；`profile.preferences.competition_tolerance=medium` 也不支持无差异进入高密度同款竞争。

**主要风险：** 事实风险：成本、承重/兼容性和真实需求均未核验。经验风险：结构差异不明显时容易进入价格竞争。待核实：单位毛利、退货原因、耐用性与专利/外观风险。

**下一步最小验证：** 先做承重与折叠寿命小样测试，再核实完整成本和真实 TikTok 同款/互动数据。

### 3. lr-c63 — Silicone cord label set

**为什么适合你：** 线缆识别前后对比符合 SOP 和 `profile.capabilities.content_skill=5`；轻小件形态与 `profile.constraints.logistics_modes` 中的轻小件直发方向相容（真实物流仍未验证）。

**为什么不适合你：** 输入标记同款密度高、外观差异小，而 SOP 要求结构、套装或内容上的可感知差异；低目标售价不等于有利润，`profile.preferences.margin_floor_pct=35` 尚无法审判。

**主要风险：** 事实风险：完整成本、材质合规与真实需求缺失。经验风险：外观差异弱、演示容易被复制。待核实：单位毛利、标签耐久性、包装与真实物流费用。

**下一步最小验证：** 核实完整单位成本及毛利是否达到画像红线，并测试颜色/图标套装差异是否能被用户快速感知。

### 4. lr-d88 — Stackable shoe slot

**为什么适合你：** 鞋柜空间对比符合 SOP 的前后对比内容法，且结构仍有差异化空间，匹配 `profile.preferences.product_style` 的功能改良。

**为什么不适合你：** 尺码适配已被输入列为观察项，会增加团队售后负担；相对其他候选更大的体积也需要核实是否触碰 SOP 的“大件不做”边界，不能仅凭合成尺寸自动放行真实商品。

**主要风险：** 事实风险：真实包装体积、物流、退货与单位成本缺失。经验风险：鞋型兼容问题可能带来退货。待核实：折叠/堆叠稳定性、适配范围、实际运输尺寸及毛利。

**下一步最小验证：** 用常见鞋型做适配和稳定性小样测试，同时取得包装后尺寸重量与完整物流成本。

## 被过滤品与 blocked_pending_data

- 被过滤品：无。
- `blocked_pending_data`：无；成本缺口按本实验约定统一列入人工核实，未重复阻塞候选。

## 依据分层与人工核实

- 数据依据：仅 `references/demo-data/eval-learned-transfer-candidates.md` 的合成数值和信号。
- 画像依据：`sellers/eval-content/profile.yaml`、`sellers/eval-content/sop.md`、最近 3 条 decision。
- 经验依据：`references/platforms/tiktok.md` 的内容可拍性与推荐流量分析框架，不作为事实数字。
- 人工核实：四个候选均需补齐采购、平台费、头程/尾程、广告、退货、税费、合规/认证等完整单位成本，并核实毛利是否达到 `profile.preferences.margin_floor_pct=35`。
- 人工核实：用真实 TikTok US 热门视频、互动、评论、商品价格、物流方案与转化窗口验证需求和竞争假设。
- 人工核实：核查每个候选的知识产权、材质/标签合规、包装后尺寸重量、物流轨迹与售后风险。

## 下一步建议

先补齐四个候选的完整单位经济模型；在分母一致前保持 margin 与 total_score 为 N/A。随后用真实 TikTok US 只读数据复核 demand/competition，并对 lr-a17 优先做差异化素材小测。任何真实上架决定都不应基于本合成实验。
