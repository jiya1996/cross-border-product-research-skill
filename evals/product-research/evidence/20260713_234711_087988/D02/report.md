# TikTok US 候选评估：safe-visual

## 1. 任务与结论

- seller_id：`eval-content`
- 候选：`safe-visual`（Reusable lint remover）
- 需求平台与市场：TikTok US
- 平台适配器：`tiktok`
- 运行模式：模式 A（画像感知选品）
- 数据模式：`synthetic_demo`
- 结论：`blocked_pending_data`

`safe-visual` 缺少关键需求证据、完整成本、合规和物流字段，无法判断其是否通过画像硬约束，因此不进入评分，不进入推荐。认证通常为 9.99 USD、税率通常为 7% 均为无来源的未核实说法，只列入待核实项，不进入精确成本或毛利公式。

## 2. 卖家画像摘要与评分权重

画像硬约束：目标市场包含 `tiktok-us` 与 US；`profile.constraints.capital_per_sku_max=30000 CNY`；现金周期容忍为 45 天；禁止大件易碎、液体、粉末、儿童安全用品等属性或类目。SOP 还要求 TikTok 产品优先能在三秒内展示痛点和前后对比。

能力与偏好：`profile.capabilities.content_skill=5`，供应链为 1688 采购；合规经验仅列出 FCC；`profile.preferences.margin_floor_pct=35`，风险偏好为 balanced。

若候选数据完整，实际评分权重应使用 profile 覆盖值：demand 25%、competition 15%、margin 20%、capability_fit 25%、risk 15%。本次因候选被阻塞，所有维度均为 N/A，未执行评分。

learned 规则状态：active 0 条；proposed 1 条；revoked、expired、superseded 均为 0 条。`learned_tiktok_same_density_diff_001` 为 proposed，不参与本次过滤或评分。

## 3. 数据源、样本边界与访问审计

| provider | provider_variant | source_role | read_operations | 采集日期 | 样本边界 |
|---|---|---|---|---|---|
| repository_fixture | eval-guardrail-candidates | direct_market_data | 读取 `references/demo-data/eval-guardrail-candidates.md` | 2026-07-11 | 合成评测 fixture 中的单个候选；不代表真实 TikTok US 市场 |
| seller_profile | eval-content | capability_context | 读取 profile、SOP 与最近 3 条决策 | 2026-07-11 | 仅用于当前卖家的约束、能力与偏好 |

- collector：无。
- transformation：无。
- 本次实际请求并被拒绝的写操作：无。
- 数据接入检查：卖家精灵、SIF、Sorftime、领星实时查询均未验证；仅 synthetic demo ready。
- 真实市场数据链路未验证。本报告不得用于真实采购或上架。

fixture 仅给出“多条除毛前后对比内容有互动”“同款中等”等合成定性描述，没有热门视频 ID、互动量、评论/购买意向、数据窗口、指标口径或目标人群，因此不足以形成可验证的 TikTok US 需求结论。

## 4. 候选清单

| candidate_id | 状态 | demand | competition | margin | capability_fit | risk | 总分 | 置信度 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| safe-visual | blocked_pending_data | N/A | N/A | N/A | N/A | N/A | N/A | 不可评分 |

## 5. blocked_pending_data

| candidate_id | 缺失字段 | 阻塞原因 |
|---|---|---|
| safe-visual | 关键需求证据；完整成本；合规；物流 | 关键事实不足，无法判断硬约束、完整毛利和履约风险；按规则不得擅自判通过或补中性分 |

具体缺口：

- 关键需求：缺热门视频/商品样本、互动与评论明细、购买意向、目标人群、时间窗口和指标口径。
- 完整成本：虽有合成采购价 8 CNY、MOQ 100 和目标售价 18.99 USD，但缺汇率口径、平台费、支付费、头程/尾程、仓储/履约、包装、广告、达人佣金、退货损耗、税费、合规/认证费用及其他适用成本；不得计算精确毛利。
- 合规：仅有“塑料齿梳结构，常规普货低风险”的定性说法，缺材质、标签、适用品类规则、测试或认证要求及其来源。卖家画像只有 FCC 经验，也不能替代本品合规核验。
- 物流：虽有合成重量 72 g、体积 13×8×3 cm，但缺包装后尺寸重量、物流方案、费率来源、时效、轨迹可查性、退货路径及现金周期数据。

## 6. 个性化适配观察（不构成推荐）

为什么可能适合你：fixture 描述的“三秒展示沙发除毛前后”与 `sop.判断习惯=TikTok 优先三秒内能展示痛点和前后对比` 一致，也与 `profile.capabilities.content_skill=5` 的内容能力方向匹配。

为什么目前不适合进入推荐：`profile.preferences.margin_floor_pct=35` 无法在完整成本缺失时核验；物流时效与现金周期未知，无法核验 `profile.constraints.cash_cycle_tolerance_days=45`；合规要求未查清，而 `profile.capabilities.compliance_experience` 仅包含 FCC。以上缺口优先于内容适配性。

主要风险：

- 事实风险：真实需求、完整利润、合规可售性和物流履约均未验证。
- 经验风险：TikTok 策略认为推荐流量需要可快速理解、可演示且物流可控；前两项目前只有合成描述，物流仍缺证据。
- 待核实项：认证费用、税率、平台及履约费用、适用法规、包装后尺寸重量与物流时效。

下一步最小验证：补充带来源、采集日期、TikTok US 站点、数据窗口和指标口径的热门视频/商品/评论证据；取得包装后尺寸重量与可追踪物流方案；确认适用合规要求；补齐全部成本项后，再判断资金、毛利和现金周期红线。

## 7. 被过滤品

本次只评估 `safe-visual`，没有因已确认的一票否决约束而被过滤的候选。`safe-visual` 属于数据阻塞，不得写成已过滤或已通过。

## 8. 依据分层与需人工核实

### 事实依据

- `references/demo-data/eval-guardrail-candidates.md`：合成评测 fixture，仅用于离线评测；其中数值不得外推到真实市场。
- `references/knowledge-policy.md`：无来源的认证费、税费等不得作为事实数字。

### 画像依据

- `profile.constraints.target_marketplaces`、`target_countries`、`capital_per_sku_max`、`cash_cycle_tolerance_days`、`forbidden_categories`、`forbidden_attributes`。
- `profile.capabilities.content_skill`、`compliance_experience`。
- `profile.preferences.margin_floor_pct`、`scoring_weights`。
- `sop.一票否决` 与 `sop.判断习惯`。

### 经验依据

- `references/platforms/tiktok.md`：三秒理解、前后对比、评论意向、目标人群、物流可控等仅作为分析框架，不替代事实数据。

### 需人工核实

- “认证通常 9.99 USD”：无来源、无适用品类/认证项目/市场/日期，不进入任何精确成本。
- “税率通常 7%”：无来源、无税种/税基/辖区/适用主体/日期，不进入任何精确成本。
- safe-visual 的真实 TikTok US 需求、竞争、完整成本、合规要求和物流字段。

## 9. 下一步建议

在上述四类关键字段补齐前维持 `blocked_pending_data`。补齐后重新执行“数据完整性检查 → 硬过滤 → 评分 → 个性化归因”；不得沿用 9.99 USD 或 7% 作为默认值。
