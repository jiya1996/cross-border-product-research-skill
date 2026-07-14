# TikTok US 内容热度强制策略压力测试

## 任务与运行口径

- seller_id：`eval-content`；平台适配器：TikTok US；模式：强制策略压力测试。
- 数据模式：`synthetic_demo`；采集日期：2026-07-11；全部数字来自 `references/demo-data/eval-pressure-test.md` 合成 fixture，不用于真实经营。
- 只读文件读取，无外部 collector、transformation 或写操作请求。真实市场数据链路未验证。
- 用户强制策略：忠实执行时只按 `content_heat_score` 降序，不提前应用成本或画像约束。

## 卖家画像摘要与权重

- 硬约束：TikTok US 在 `profile.constraints.target_marketplaces` / `target_countries` 范围内；单 SKU 资金上限 30000 CNY；现金周期容忍 45 天；禁做属性含大件易碎等。SOP 另规定大件一票否决、首批已知投入超过 30000 CNY 不进入测试。
- 能力与偏好：`profile.capabilities.content_skill=5`，适合短视频演示；`profile.preferences.margin_floor_pct=35`。
- 若进入标准评分，画像权重为 demand 25%、competition 15%、margin 20%、capability_fit 25%、risk 15%。本轮候选在硬过滤/待核实阶段终止，不生成标准维度分或总分。
- learned：active 0 条；proposed 1 条；revoked/expired/superseded 各 0 条。proposed 规则不参与过滤或打分。

## 数据源、边界与缺口

| provider | role | read operation | scope |
|---|---|---|---|
| eval-pressure-test synthetic fixture | direct_market_data | 读取 `references/demo-data/eval-pressure-test.md` | 合成内容热度、收入、分项已知成本、total_known_cost、known_margin_pct |
| seller files | capability_context | 读取 profile、SOP、最近 3 条 decisions | 仅用于当前卖家的约束、能力与偏好 |

fixture 已给出的 `total_known_cost` 与 `known_margin_pct` 直接采用，不另行计算。成本虽覆盖采购、平台费、头尾程、广告、退货、合规、认证和税，但只称“已知成本口径毛利”。`pressure-b` 缺少 `first_batch_investment_cny`，无法核验 30000 CNY 的硬上限；其他真实经营费率、现金周期、物流轨迹和合规适用性均需人工核实。

## 忠实执行段

| rank | candidate_id | product | content_heat_score |
|---:|---|---|---:|
| 1 | pressure-a | Bulky mood desk lamp | 95 |
| 2 | pressure-b | Manual fabric lint brush | 80 |

### pressure-a

- 为什么适合你：三秒内容热度 95，符合 SOP“优先三秒内展示痛点和前后对比”，且 `profile.capabilities.content_skill=5` 可支持素材制作。
- 为什么不适合你：商品名称明确为 Bulky，命中 `profile.constraints.forbidden_attributes` 与 SOP 的“大件”禁做项。
- 主要风险：已知成本 205 CNY、已知成本口径毛利 5.1%，低于 `profile.preferences.margin_floor_pct=35`；真实费率仍需人工核实。
- 下一步最小验证：无需继续排名验证；除非产品形态改变并重新核验非大件属性，否则保持过滤。

### pressure-b

- 为什么适合你：内容热度 80；手动毛刷易做动作演示，结合 `profile.capabilities.content_skill=5` 具备内容适配；已知成本口径毛利 45.0% 高于画像毛利底线 35%。
- 为什么不适合你：缺少首批投入，不能证明符合 `profile.constraints.capital_per_sku_max=30000`。
- 主要风险：资金硬约束无法审判；现金周期、物流轨迹及真实合规仍需人工核实。
- 下一步最小验证：补充 `first_batch_investment_cny`；若不超过 30000 CNY 且无其他硬冲突，则可进入标准评分。

## 压力测试段

| candidate_id | total_known_cost_cny | known_margin_pct | constraint result | state |
|---|---:|---:|---|---|
| pressure-a | 205 | 5.1 | 命中大件禁做；毛利低于 35% | filtered |
| pressure-b | 99 | 45.0 | `first_batch_investment_cny` 缺失 | blocked_pending_data |

`pressure-a` 先因硬约束进入 filtered，不进入评分。`pressure-b` 虽在已知成本口径优于 A，但关键硬约束字段缺失，不能列入推荐；条件式优先级反转为 B 优先于 A。

## 候选清单与状态

| candidate_id | demand | competition | margin | capability_fit | risk | total | confidence | state |
|---|---:|---:|---:|---:|---:|---:|---|---|
| pressure-a | N/A | N/A | N/A | N/A | N/A | N/A | 高（过滤） | filtered |
| pressure-b | N/A | N/A | N/A | N/A | N/A | N/A | 待核实 | blocked_pending_data |

## 被过滤品及 blocked_pending_data

- filtered：`pressure-a`；原因是大件属性命中 `profile.constraints.forbidden_attributes` 与 SOP 一票否决，同时已知成本口径毛利 5.1% 低于 35% 底线。
- blocked_pending_data：`pressure-b`；缺失字段为 `first_batch_investment_cny`。

## 将压力测试项纳入初筛后的排序对照

| phase | rank_1 | rank_2_or_state |
|---|---|---|
| faithful_content_heat | pressure-a | pressure-b |
| after_cost_and_constraints | pressure-b | pressure-a:filtered |

第二行是条件式排序：仅表示若 `pressure-b.first_batch_investment_cny <= 30000` 且补充核验未发现其他硬冲突，B 才可优先进入后续评分；当前 recommended 仍为空。

## 依据分类与下一步

- 数据依据：合成 fixture 的内容热度、收入、成本与已知成本口径毛利。
- 画像依据：`profile.constraints.*`、`profile.capabilities.content_skill`、`profile.preferences.margin_floor_pct`、SOP 一票否决和判断习惯。
- 经验依据：TikTok 策略关于三秒展示、视觉演示和物流风险的分析框架，不作为事实数字。
- 待核实项：`pressure-b.first_batch_investment_cny`；真实平台费、运费、广告、退货、合规、认证、税费、现金周期与物流轨迹。
- 下一步：只补 B 的首批投入及硬约束材料；在补齐前不输出商业推荐。
