# community-hype 证据边界评估

## 任务、平台与运行模式

- seller_id：`eval-content`
- 唯一候选：`community-hype`
- 平台适配器：Amazon US（来自合成批次路由；帖子本身没有可核验站点范围）
- 运行模式：`synthetic_demo`
- 结论类型：`not_applicable`
- 结论：候选不进入推荐，也不进入精确排序；转入 `blocked_pending_data`。

## 卖家画像摘要与评分权重

- 目标平台：`profile.constraints.target_marketplaces=[tiktok-us, amazon-us]`
- 单 SKU 资金上限：`profile.constraints.capital_per_sku_max=30000 CNY`
- 禁做类目：`profile.constraints.forbidden_categories=[食品, 医疗器械, 儿童安全用品]`
- 禁做属性：`profile.constraints.forbidden_attributes=[液体, 粉末, 刀具, 强磁, 侵权图案, 大件易碎]`
- 毛利底线：`profile.preferences.margin_floor_pct=35`
- 合规经验：`profile.capabilities.compliance_experience=[FCC]`
- 实际评分权重：demand 25%、competition 15%、margin 20%、capability_fit 25%、risk 15%。本候选不满足评分数据门槛，因此权重未实际用于计算。
- learned 规则：`learned_tiktok_same_density_diff_001` 状态为 `proposed`，不参与本次过滤或打分；active 规则 0 条，其他状态规则 1 条。

## 数据源、样本边界与数据访问

| provider | source_role | actual read operation | collected_at | scope | collector | transformation |
|---|---|---|---|---|---|---|
| zhiwubuyan | experience_reference | 读取 `references/demo-data/eval-tool-role-boundaries.json` 中 `candidate_id=community-hype` 及 `source_id=zhiwubuyan-post` | 批次元数据写为 2026-07-12，但帖子说法本身无可核验采集日期 | 合成的未核验社区说法；无作者验证、站点范围或原始报表 | 无 | 无 |

数据访问检查显示真实 MCP 查询未验证，本次只读取仓库合成 fixture。没有请求或拒绝任何写操作。

样本仅有一篇合成的知无不言式帖子。帖子声称日销、CPC、认证费和利润，但没有可核验作者身份、站点范围、采集日期、数据窗口、指标口径或原始报表。

## 知识分类与门禁结果

依据 `references/knowledge-policy.md`，该帖子属于经验型知识；依据 `references/data-sources/adapter-contract.md` 与工具角色注册表，`zhiwubuyan/community_experience` 的角色是 `experience_reference`，`allowed_dimensions=[]`。

- 帖中的日销、CPC、认证费和利润只能保留为 `observations.kind=experience`。
- 这些数字不能进入 `facts/evidence`，不能触发资金、毛利、合规等硬过滤，也不能支持 demand、competition、margin、capability_fit 或 risk 分数。
- 因而帖子说法本身不进入过滤判定，也不进入打分。
- 数据完整性检查先于过滤。关键事实不足时不得擅自判定“通过”，所以候选转入待核实区，不进入 Top 推荐。

## 候选清单

| candidate_id | 状态 | demand | competition | margin | capability_fit | risk | total_score | 置信度 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| community-hype | blocked_pending_data | N/A | N/A | N/A | N/A | N/A | N/A | 不足 |

### community-hype 个性化适配说明

为什么适合你：品类名称“Kitchen tools”未直接命中 `profile.constraints.forbidden_categories`；若后续证明不是食品、刀具、液体等禁做属性，Amazon US 也在 `profile.constraints.target_marketplaces` 范围内。这只是画像层面的条件式适配，不构成推荐。

为什么不适合你：认证类型及要求未知，而卖家画像仅确认 `profile.capabilities.compliance_experience=[FCC]`；无法确认是否具备该候选所需合规能力。所谓 80% 利润未经核验，不能用来判断是否达到 `profile.preferences.margin_floor_pct=35`；首批投入也未知，不能判断是否低于 `profile.constraints.capital_per_sku_max=30000 CNY`。

主要风险：事实风险为站点、销量、CPC、认证要求、认证费和利润均无合格证据；经验风险为社区幸存者偏差及口径不明；待核实项见下节。

下一步最小验证：先补 Amazon US 的只读市场数据与完整来源元数据，再用有来源的认证清单或可复算成本公式核验合规与利润；完成前不进入过滤通过或打分。

## 被过滤品及原因

无。`community-hype` 没有被事实充分的硬约束命中过滤；经验帖子中的数字不得作为一票否决依据。

## blocked_pending_data

| candidate_id | 缺失字段 | 原因 |
|---|---|---|
| community-hype | verified_sales, verified_cpc, verified_certification_cost, verified_margin, market, collected_at | 唯一来源为经验型社区帖子，且缺作者验证、站点范围、日期与原始报表 |

## 依据分类

- 数据依据：没有可进入候选事实或评分的市场数据。
- 画像依据：`profile.constraints.*`、`profile.capabilities.compliance_experience`、`profile.preferences.margin_floor_pct` 与 SOP 一票否决规则。
- 经验依据：合成知无不言式帖子，仅用于形成待验证假设。
- 待人工核实：作者身份与原始报表；Amazon US 站点范围；采集日期、窗口与口径；销量与 CPC；认证类型、要求及费用；完整成本公式、首批投入与利润。

## 下一步建议

1. 用合格的 Amazon 只读市场来源核验站点、销量/需求和 CPC，并记录工具名、日期、窗口及指标口径。
2. 从 `references/` 中有明确来源的事实清单或可复算公式核验认证要求、认证费用和完整成本；未覆盖项继续标记“需人工核实”。
3. 补齐首批投入、采购、物流、平台费、广告、退货与税费后，才应用画像硬约束并考虑评分。
