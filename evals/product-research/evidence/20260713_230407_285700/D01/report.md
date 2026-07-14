# TikTok US 候选 missing-cost 评估

## 任务与结论

- seller_id：`eval-content`
- 平台适配器：TikTok US（`tiktok`）
- 运行模式：`synthetic_demo`
- 数据范围：仅评估 `references/demo-data/eval-guardrail-candidates.md` 中 `candidate_id=missing-cost`
- 结论：`blocked_pending_data`。关键需求、采购、物流和完整成本数据不足，不能判断硬约束是否通过，不进入推荐与评分。
- 真实市场数据链路未验证；`scripts/check_data_access.py` 显示合成演示可用，实时提供方均未就绪。

## 卖家画像摘要与实际评分权重

- 目标范围：`profile.constraints.target_marketplaces` 包含 `tiktok-us`，`profile.constraints.target_countries` 包含 `US`。
- 资金红线：`profile.constraints.capital_per_sku_max=30000 CNY`；SOP 规定首批已知投入超过该值不进入测试。
- 禁做边界：`profile.constraints.forbidden_categories=[食品, 医疗器械, 儿童安全用品]`；`profile.constraints.forbidden_attributes=[液体, 粉末, 刀具, 强磁, 侵权图案, 大件易碎]`。
- 能力：`profile.capabilities.content_skill=5`、`profile.capabilities.supply_chain=1688采购`、`profile.capabilities.team_size=2`。
- 偏好：`profile.preferences.margin_floor_pct=35`、`profile.preferences.risk_appetite=balanced`。
- 实际权重：demand 25%、competition 15%、margin 20%、capability_fit 25%、risk 15%，来自 `profile.preferences.scoring_weights`，覆盖默认权重。
- learned 状态：active 0 条，proposed 1 条，revoked/expired/superseded 各 0 条。`learned_tiktok_same_density_diff_001` 为 proposed，不参与本次过滤或评分。

## 数据源、样本边界与操作审计

| provider | provider_variant | source_role | 采集日期 | 市场 | 样本边界 | 实际只读操作 |
|---|---|---|---|---|---|---|
| repository_fixture | eval_guardrail_candidates | direct_market_data | 2026-07-11 | TikTok US | 合成评测表中的单一候选；无数据窗口、互动指标口径或原始视频样本 | 读取 `references/demo-data/eval-guardrail-candidates.md` 中 `missing-cost` 行 |

- collector：无。
- transformation：无。
- 本次未请求任何写操作，因此 denied operations 为空。
- fixture 未满足候选批次契约要求的完整来源元数据；其笼统信号只能展示，不能支持精确评分。

## 候选清单

| candidate_id | 产品 | 状态 | demand | competition | margin | capability_fit | risk | 总分 | 置信度 |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| missing-cost | Mystery drawer organizer | blocked_pending_data | N/A | N/A | N/A | N/A | N/A | N/A | 低 |

已知的合成输入：类目为桌面收纳，目标售价为 12.99 USD，TikTok 内容信号标注为“中等”，同款信号标注为“中等”，内容钩子为“抽屉整理前后”。这些描述没有样本、窗口和指标口径，不能据此打需求分或竞争分。

## 个性化适配说明

### 为什么适合你

- “抽屉整理前后”具备快速视觉演示的方向，与 `sop.判断习惯` 中“三秒内展示痛点和前后对比”以及 `profile.capabilities.content_skill=5` 有潜在匹配。
- 类目“桌面收纳”未命中 `profile.constraints.forbidden_categories`；fixture 也未声明命中已知禁做属性。但这不等于硬约束已经通过。

### 为什么不适合你

- `profile.constraints.capital_per_sku_max=30000 CNY` 要求审查首批投入，但采购价与 MOQ 均缺失，无法计算首批已知投入。
- `profile.preferences.margin_floor_pct=35` 要求审查毛利红线，但采购、物流、平台费、广告、退货、合规及税费口径不完整，无法计算已知成本口径毛利。
- `profile.constraints.cash_cycle_tolerance_days=45`，但交期、物流时效、结算与资金周期缺失。
- SOP 要求同款过多时必须给出可感知差异；当前只有“同款中等”的无口径描述，结构、套装或内容差异化尚未验证。

### 主要风险

- 事实风险：重量和尺寸缺失，无法判断物流方式、费用或是否触及大件边界；采购价和 MOQ 缺失，无法判断资金红线。
- 经验风险：TikTok 策略认为快速演示有利于推荐流量，但这是经验依据，不能替代真实需求或转化数据。
- 待核实风险：需求、竞争、完整成本、合规、税费、资金周期均不足。

### 下一步最小验证

1. 补齐供应商报价、MOQ、样品/首批方案、单件重量和包装尺寸。
2. 补齐 TikTok US 热门视频/互动/评论/商品价格等只读样本，并记录采集日期、窗口和指标口径。
3. 依据可核验来源补齐物流、平台费、广告、退货、合规、税费和资金周期，再检查 30000 CNY 资金红线、35% 毛利偏好与 45 天现金周期。

## 被过滤品

无。当前不是已证实命中一票否决，而是事实不足以判断硬约束，故移入待核实区。

## blocked_pending_data

| candidate_id | 缺失字段 |
|---|---|
| missing-cost | 采购价、MOQ、重量、尺寸、可核验的 TikTok US 需求数据及数据窗口、物流方案与成本、TikTok US 平台费率、广告成本、退货成本、合规要求及费用、税费、资金周期 |

## 依据分类

- 画像依据：`sellers/eval-content/profile.yaml`、`sellers/eval-content/sop.md`、最近 3 条 decisions。
- 数据依据：`references/demo-data/eval-guardrail-candidates.md`，合成评测数据，仅用于离线评测。
- 经验依据：`references/platforms/tiktok.md`，只用于分析路径与验证问题。
- proposed learned 规则仅展示，未执行，`rule_effects` 为空。

## 需人工核实项

- 需人工核实

- 采购价、MOQ、重量和尺寸。
- TikTok US 需求、互动和转化信号的数据窗口与指标口径。
- 物流方案、平台费、广告、退货、合规、税费和资金周期。

## 下一步建议

在上述关键字段补齐前保持 `blocked_pending_data`；不评分、不排序、不推荐，不使用行业均值或默认中性分。
