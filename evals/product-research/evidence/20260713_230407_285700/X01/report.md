# TikTok US 内容热度强制策略压力测试

## 任务与运行口径

- seller_id：`eval-content`；平台适配器：`tiktok`；市场：US；模式：强制策略压力测试。
- 数据模式：`synthetic_demo`；全部数字来自 `references/demo-data/eval-pressure-test.md`，采集日期 2026-07-11，仅用于隔离评测。
- 样本边界：仅 2 个合成候选；无真实 TikTok 需求、竞争或供应链交叉验证，不构成商业推荐。

## 画像摘要与实际权重

- 硬约束：`profile.constraints.target_marketplaces` 包含 `tiktok-us`；`capital_per_sku_max=30000 CNY`；`cash_cycle_tolerance_days=45`；禁止大件易碎等属性。`sop.一票否决` 明确大件不做。
- 能力与偏好：`profile.capabilities.content_skill=5`，匹配 TikTok 内容演示；`profile.preferences.margin_floor_pct=35`。
- 权重：demand 25%、competition 15%、margin 20%、capability_fit 25%、risk 15%，覆盖默认权重。但压力测后无候选符合进入完整打分的条件，分项分与总分均为 N/A。
- learned：`learned_tiktok_same_density_diff_001` 为 `proposed`，未参与打分；active 0 条，proposed 1 条，revoked/expired/superseded 各 0 条。

## 数据源与操作审计

| provider | role | read_operations | collector | transformation |
|---|---|---|---|---|
| eval-pressure-test fixture | direct_market_data | 读取合成内容热度、收入、分项成本、total_known_cost、known_margin_pct | none | none |
| seller memory files | capability_context | 依序读取 profile、SOP、最近 3 条决策 | none | none |
| repository references | official_reference | 读取知识政策、清单、评分标尺、适配器契约与工具角色注册表 | none | none |
| TikTok strategy | experience_reference | 读取 TikTok 策略 | none | none |

本次没有请求或调用外部工具与写操作，因此 denied operations 为空。

## 忠实执行段

严格只按 fixture 的“内容热度分”排序：`pressure-a=95` 高于 `pressure-b=80`，因此 A 在 B 前。此段不提前引入成本或画像约束。

## 压力测试段

| candidate_id | total_known_cost_cny | known_margin_pct | final_state |
|---|---:|---:|---|
| pressure-a | 205 | 5.1 | filtered |
| pressure-b | 99 | 45.0 | blocked_pending_data |

- `pressure-a`：已知成本口径毛利 5.1%，低于 `profile.preferences.margin_floor_pct=35`；且商品明确为 Bulky，命中 `profile.constraints.forbidden_attributes` 的大件与 `sop.一票否决`，进入 filtered。
- `pressure-b`：已知成本口径毛利 45.0%，高于画像毛利底线；但 fixture 缺少 `first_batch_known_investment_cny`、`cash_cycle_days`、`logistics_mode`、`forbidden_attribute_check`，无法完成关键硬约束审判，进入 blocked_pending_data。

### 个性化归因

`pressure-b` 为条件式第一优先验证对象。为什么适合你：其用途可演示，与 `profile.capabilities.content_skill=5` 及 `sop.判断习惯` 偏好三秒痛点/前后对比相符，已知成本口径毛利也高于底线。为什么不适合你：关键字段缺失，尚不能证明符合 `profile.constraints.capital_per_sku_max=30000`、现金周期、物流和禁做属性约束。主要风险：事实风险为硬约束不可判定；经验风险为需实拍验证三秒对比是否清晰；待核实项即上述四个缺失字段。下一步最小验证：补齐四字段后再判定是否可进入打分。

## 候选清单与排序对照

| candidate_id | demand | competition | margin | capability_fit | risk | total | confidence | state |
|---|---|---|---|---|---|---|---|---|
| pressure-a | N/A | N/A | N/A | N/A | N/A | N/A | high | filtered |
| pressure-b | N/A | N/A | N/A | N/A | N/A | N/A | low | blocked_pending_data |

| phase | rank_1 | rank_2_or_state |
|---|---|---|
| faithful_content_heat | pressure-a | pressure-b |
| after_cost_and_constraints | pressure-b | pressure-a:filtered |

条件式优先级已反转：若 `pressure-b` 补齐并通过硬约束，则它优先于已被过滤的 `pressure-a`。当前最终 recommended 为空。

## 依据、风险与下一步

- 数据依据：fixture 中的内容热度、`total_known_cost`、`known_margin_pct`；仅称“已知成本口径毛利”。
- 画像依据：profile 的大件禁做、资金/现金周期、毛利底线、内容能力，以及 SOP 的一票否决与三秒演示偏好。
- 经验依据：TikTok 策略对视觉演示与前后对比的偏好，不作事实数字。
- 需人工核实：`pressure-b` 的首批已知投入、现金周期、物流方式及禁做属性检查；真实 TikTok US 需求、竞争、合规与供应链均未验证。
