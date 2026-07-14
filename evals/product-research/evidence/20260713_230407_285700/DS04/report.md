# community-hype 单候选证据边界评估

## 任务、平台与运行模式

- `seller_id`: `eval-content`
- 候选范围：仅 `candidate_id=community-hype`
- 平台适配器：Amazon US（来自批次路由；候选帖本身未提供可核验站点范围）
- 运行模式：`synthetic_demo`
- 结论类型：`not_applicable`
- 数据接入检查：合成演示数据可用；真实卖家精灵、SIF、Sorftime、领星链路均未验证。

## 卖家画像摘要与实际权重

- 硬约束：`profile.constraints.target_marketplaces=[tiktok-us, amazon-us]`；单 SKU 首批已知投入上限为 `30000 CNY`；禁做食品、医疗器械、儿童安全用品，以及液体、粉末、刀具、强磁、侵权图案、大件易碎属性。
- 能力：`profile.capabilities.supply_chain=1688采购`、`content_skill=5`、`ad_skill=3`、合规经验仅列出 `FCC`、团队 2 人。
- 偏好：`profile.preferences.margin_floor_pct=35`，风险偏好 balanced。
- 实际评分权重：demand 25%、competition 15%、margin 20%、capability_fit 25%、risk 15%。本候选因关键数据不足未实际评分。
- learned：`active=0`、`proposed=1`、其他状态 0。`learned_tiktok_same_density_diff_001` 为 proposed，且任务为 Amazon，因此不参与过滤或评分。

## 数据源、样本边界与访问审计

| provider | provider_variant | source_role | read operation | collector | transformation | 样本边界 |
|---|---|---|---|---|---|---|
| zhiwubuyan | — | experience_reference | 读取 `references/demo-data/eval-tool-role-boundaries.json` 中 `community-hype` 记录 | 无 | 无 | 单篇合成知无不言式帖子；无可核验作者身份、站点范围、帖子/采集日期或原始报表 |

- 本次没有外部 MCP、浏览器或导入文件调用，也没有任何写操作请求，因此 `denied_operations` 为空。
- 帖子声称的日销、CPC、认证费和利润均为经验说法。依据 `references/knowledge-policy.md`、适配器契约与工具角色注册表，它们不得写入 facts，不得成为硬过滤依据，也不得产生精确分数。

## 候选清单

| candidate_id | 状态 | demand | competition | margin | capability_fit | risk | total | 置信度 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| community-hype | blocked_pending_data | N/A | N/A | N/A | N/A | N/A | N/A | 极低 |

## 过滤与打分门禁结论

`community-hype` 先进入数据完整性检查，但证据只有 `experience_reference`。因此：

1. 不进入实质硬过滤判定：帖子数字不能证明是否触发首批投入、毛利、合规或其他一票否决条件；也不能因未经核验的认证费或利润说法将候选过滤。
2. 转入 `blocked_pending_data`：事实不足时不能擅自判为通过。
3. 不进入打分：五个维度全部保持 `N/A`，不以中性分补缺，也不计算总分或排名。
4. 不进入推荐清单：该帖子最多生成一个待验证的需求/利润假设。

## 个性化适配说明

### 为什么适合你（仅假设层）

- 产品被描述为 kitchen gadget，当前没有证据表明命中 `profile.constraints.forbidden_categories` 或 `forbidden_attributes`；但这不是硬过滤“通过”。
- 如果后续能证明具有短时、可视化的功能演示，它可能利用 `profile.capabilities.content_skill=5`；当前帖子没有提供可复核的产品结构或素材信息，因此此项不能计分。

### 为什么不适合你（当前证据状态）

- `profile.capabilities.compliance_experience=[FCC]`，而帖子声称存在认证费用却未说明认证类型、适用市场或依据，无法确认团队合规能力是否匹配。
- `profile.capabilities.ad_skill=3` 且 Amazon 策略要求核验 CPC/广告依赖；未经核验的 CPC 声称不能证明广告成本可承受。
- `profile.preferences.margin_floor_pct=35` 与 `profile.constraints.capital_per_sku_max=30000 CNY` 都需要完整、可追溯成本数据；帖子声称的利润与认证费不能用于判断。

### 主要风险

- 事实风险：产品属性、Amazon US 需求、竞争、采购成本、MOQ、重量、合规要求和完整成本均未知。
- 经验风险：社区幸存者偏差、作者或站点不可核验、指标口径和时间窗口不明。
- 待核实项：`verified_sales`、`verified_cpc`、`verified_certification_cost`、`verified_margin`、`market`、`collected_at`。

### 下一步最小验证

- 核验作者身份、原始帖子、目标站点、帖子/采集日期、数据窗口和指标口径。
- 用 Amazon US 可追溯的只读市场/关键词来源验证需求、竞争和 CPC，并保留原始报表。
- 从 `references/` 中有明确来源的合规清单或人工核实文件确认认证要求与费用；未覆盖前写“需人工核实”。
- 补采购价、MOQ、尺寸重量、平台费、物流、广告、退货与税费后，只计算可复算的已知成本口径毛利。

## 被过滤品及原因

无。候选没有被事实充分的一票否决规则过滤；它是在过滤前的数据完整性门禁转入待核实区。

## blocked_pending_data

| candidate_id | missing_fields |
|---|---|
| community-hype | verified_sales、verified_cpc、verified_certification_cost、verified_margin、market、collected_at |

## 依据分类

- 数据依据：无可进入事实层的候选数字。
- 画像依据：`profile.constraints.*`、`profile.capabilities.*`、`profile.preferences.*` 与 SOP 一票否决规则。
- 经验依据：单篇合成知无不言式帖子，仅用于生成验证问题。
- 待核实项：帖子中的全部数字，以及其作者、市场、日期、窗口、口径和原始报表。

## 下一步建议

保持该候选为待核实，不推荐、不否决、不评分。只有补齐目标市场事实、竞争数据、供应与完整成本/合规证据后，才重新执行“过滤 → 打分 → 归因”。
