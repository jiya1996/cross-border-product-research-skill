# TikTok US learned rule transfer — effect-only 合成需求假设

## 1. 任务、适配器与结论边界

- `seller_id`: `eval-content`
- 平台 / 市场: TikTok / US
- 平台适配器: `tiktok`
- 运行模式: `synthetic_demo`
- 结论类型: `demand_hypothesis_only`
- 输入批次: `references/demo-data/eval-learned-transfer-candidates.md`（合成评测 fixture，采集日期 2026-07-12）

本报告是 effect-only 的合成假设实验，只检验受控硬约束与 learned 规则迁移。它不证明真实 TikTok US 需求、竞争、利润或供应可行性，不能用于真实经营决策。真实市场数据链路未验证；`scripts/check_data_access.py` 仅确认 synthetic demo ready。

## 2. 卖家画像摘要与实际权重

- 硬约束：`profile.constraints.target_marketplaces` 包含 `tiktok-us`；`target_countries=[US]`；`capital_per_sku_max=30000 CNY`；`cash_cycle_tolerance_days=45`；禁做属性含液体、粉末、刀具、强磁、侵权图案和大件易碎。
- 能力：`profile.capabilities.content_skill=5`，`supply_chain=1688采购`，团队人数为 2。
- 偏好：`profile.preferences.product_style=[轻创新, 功能改良, 情绪价值]`，`margin_floor_pct=35`，竞争容忍度为 medium。
- SOP：TikTok 优先三秒内展示痛点和前后对比；同款多时必须有结构、套装或内容差异。
- learned 状态：`active=1`；`proposed=0`、`revoked=0`、`expired=0`、`superseded=0`。

本次采用 profile 覆盖权重：demand 25%、competition 15%、margin 20%、capability_fit 25%、risk 15%。由于完整单位成本缺失，margin 与 total_score 全部为 N/A；排序只使用四个可评估维度的加权暂定小计，不把该小计冒充总分，也不重归一化缺失的 20% margin 权重。

## 3. 数据源、读取操作、样本边界与缺口

| provider | variant | source_role | read operation | date/window | scope |
|---|---|---|---|---|---|
| repository_fixture | eval-learned-transfer-candidates | direct_market_data（synthetic） | `read_file references/demo-data/eval-learned-transfer-candidates.md` | 2026-07-12 / 单次受控 fixture | 四个 TikTok US 合成候选；仅用于假设与规则 effect |
| seller_memory | profile-sop-decisions | capability_context | `read_file` profile、SOP、最近 3 条 decisions | 截至 2026-07-13 | 约束、能力、偏好和 learned 证据复核 |
| repository_reference | policy-checklists-adapter-tiktok | official_reference / experience_reference | `read_file` 固定前置 references | 仓库当前版本 | 知识纪律、评分框架和 TikTok 经验策略 |

- collector: 无。
- transformation: 规则标签子集匹配、active delta 聚合后单次 clamp、四维加权暂定小计。
- denied operations: 无；本次没有请求任何写平台操作。
- 样本边界：仅 4 个合成候选，不代表 TikTok US 市场分布。
- 核心缺口：真实热门视频/互动/评论/转化窗口、真实同款密度、完整单位成本、平台费、物流、广告、退货、税费、合规与认证信息均未验证。

## 4. 数据完整性与受控硬约束

四个候选的 `hard_constraint_status=pass_synthetic`；`controlled_initial_investment_cny` 分别为 5200、5600、5000、6500，均未超过 `profile.constraints.capital_per_sku_max=30000 CNY`；`controlled_cash_cycle_days` 为 30 或 35，均未超过 `profile.constraints.cash_cycle_tolerance_days=45`。这些字段只在本 effect-only 实验中证明硬约束可判定，不外推真实经营。

因此四个候选均可进入四维假设评分。完整单位成本缺失只使 margin 和 total_score 保持 N/A，并进入人工核实；按本实验约定，不把这些候选重复放入 `blocked_pending_data`。

## 5. Learned 规则证据复核与应用

执行规则 `learned_tiktok_same_density_diff_001`（status=`active`）：作用域 TikTok / US；条件标签为 `same_product_density_high` 与 `differentiation_space_low` 的子集匹配；动作是 competition `delta=-1`。

复读三条 `decision_path` 后，均确认：决定为 rejected；包含显式规范标签 ID；候选分别为 `tt-008`、`tt-002`、`tt-004`；来源报告路径与画像证据一致；三条决策会话彼此独立。规则只迁移到新候选的结构化标签，不按历史候选 ID 套用。`lr-d88` 缺少 `differentiation_space_low`，不命中。

| rule_id | candidate_id | dimension | delta | before | after |
|---|---|---|---:|---:|---:|
| learned_tiktok_same_density_diff_001 | lr-a17 | competition | -1 | 2 | 1 |
| learned_tiktok_same_density_diff_001 | lr-b42 | competition | -1 | 2 | 1 |
| learned_tiktok_same_density_diff_001 | lr-c63 | competition | -1 | 2 | 1 |

每个命中组仅有一条 active delta，因此 aggregate delta 均为 -1；从受控 `pre_rule_competition_score=2` 得到最终 1，并在 0–5 范围单次 clamp。

## 6. 四维 hypothesis-only 暂定推荐

四维小计公式为 `demand×0.25 + competition×0.15 + capability_fit×0.25 + risk×0.15`。分数表达的是合成输入下的假设强弱：`demand_signal` 支持需求假设，TikTok 内容钩子与 `content_skill=5` 支持 capability_fit，受控风险描述支持 risk；它们不是实测市场结论。

| rank | candidate_id | product | demand | competition | margin | capability_fit | risk | four-dimension subtotal | total_score | confidence |
|---:|---|---|---:|---:|---|---:|---:|---:|---|---|
| 1 | lr-d88 | Stackable shoe slot | 4 | 3 | N/A | 5 | 3 | 3.2 | N/A | 低（合成假设） |
| 2 | lr-a17 | Compact keyboard brush | 4 | 1 | N/A | 5 | 4 | 3.0 | N/A | 低（合成假设） |
| 3 | lr-c63 | Silicone cord label set | 3 | 1 | N/A | 5 | 4 | 2.8 | N/A | 低（合成假设） |
| 4 | lr-b42 | Fold-flat tablet rest | 3 | 1 | N/A | 4 | 4 | 2.5 | N/A | 低（合成假设） |

### 1) lr-d88 — Stackable shoe slot

**为什么适合你：** 鞋柜空间对比能快速呈现，直接贴合 SOP“三秒内展示痛点和前后对比”；`profile.capabilities.content_skill=5` 能支撑场景化素材。其标签没有同时满足 active learned 规则的两个条件，受控 competition 基线 3 保持不变。

**为什么不适合你：** `profile.team_size=2`，而尺码适配已列为观察项，变体说明与售后处理可能占用小团队；`profile.preferences.competition_tolerance=medium` 也要求先确认真实同款密度。

**主要风险：** 事实风险为完整成本缺失；合成观察风险为尺码适配；经验风险为收纳类同款与体积物流压力；真实同款密度、退货和物流均需核实。

**下一步最小验证：** 核实单件完整 landed cost 与毛利，并用 TikTok US 真实视频/商品样本验证需求、同款密度及尺码相关评论。

### 2) lr-a17 — Compact keyboard brush

**为什么适合你：** 键盘缝隙清洁前后对比符合 SOP 的三秒痛点展示；`profile.capabilities.content_skill=5` 与 `preferences.product_style` 中的功能改良方向匹配。

**为什么不适合你：** 同时带有 `same_product_density_high` 和 `differentiation_space_low`，触发已确认拒绝偏好；competition 从受控基线 2 降至 1，与 SOP“同款多必须可感知差异”形成直接压力。

**主要风险：** 事实风险为完整成本缺失；规则风险为高同款、低差异；真实 TikTok 互动、转化和竞争需核实。

**下一步最小验证：** 先提出结构或套装差异，再核实完整 landed cost/毛利，并以 TikTok US 真实样本验证差异是否可感知。

### 3) lr-c63 — Silicone cord label set

**为什么适合你：** 线缆识别前后对比适合快速演示，符合 SOP 与 `profile.capabilities.content_skill=5`；轻量、收纳场景与 `preferences.product_style=功能改良` 方向一致。

**为什么不适合你：** 标签完整命中 active learned 规则，competition 从 2 降为 1；外观差异小也不利于满足 SOP 的可感知差异要求。

**主要风险：** 事实风险为完整成本缺失；规则风险为同款密度与外观差异；真实需求和用户对标签尺寸/识别方式的反馈需核实。

**下一步最小验证：** 核实完整 landed cost/毛利；用真实 TikTok US 评论与素材小样验证识别痛点和套装/配色差异。

### 4) lr-b42 — Fold-flat tablet rest

**为什么适合你：** 展开收纳的一镜到底素材符合 SOP 的快速展示，且 `profile.capabilities.content_skill=5` 有利于稳定制作桌搭内容。

**为什么不适合你：** `same_product_density_high` 与 `differentiation_space_low` 触发规则，competition 从 2 降为 1；结构差异小与 SOP 的差异化要求冲突，因此 capability_fit 暂定为 4 而非 5。

**主要风险：** 事实风险为完整成本缺失；合成竞争信号还包含价格竞争；真实承重、稳定性、退货与竞争需核实。

**下一步最小验证：** 在真实样本中核实结构差异、稳定性投诉和价格竞争，同时补齐单件完整 landed cost 与毛利。

## 7. 被过滤品与 blocked_pending_data

- 被过滤品：无。四个候选的受控资金、现金周期与 `hard_constraint_status` 均通过。
- `blocked_pending_data`：无。本实验明确要求成本缺失候选进入人工核实而不重复阻塞；这不是对真实商业可行性的放行。

## 8. 依据分类与人工核实

- 数据依据：仅指定 synthetic fixture 的受控字段和合成信号。
- 画像依据：`profile.constraints`、`profile.capabilities`、`profile.preferences`、SOP 与三条拒绝决策。
- 经验依据：`references/platforms/tiktok.md` 的素材可拍性与推荐流量判断框架。
- 人工核实：四个候选均需补齐采购、包装、头/尾程、平台费、广告、退货、税费、合规/认证等完整单位成本，并核实毛利是否达到 `profile.preferences.margin_floor_pct=35`；还需用真实 TikTok US 数据核实需求、竞争、内容表现和风险。

## 9. 下一步建议

先对四个候选补齐完整单位经济模型；同时采集带日期、窗口与指标口径的 TikTok US 真实热门视频、互动、评论、商品与转化数据。成本与真实需求数据齐备前，保留 margin、total_score 为 N/A，本排序仅作为 learned effect 的暂定实验结果。
