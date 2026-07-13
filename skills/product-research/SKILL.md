---
name: product-research
description: 画像感知的跨境电商选品技能。按卖家画像与平台策略执行 Amazon、SHEIN、TikTok、DTC/SEO、Reddit 需求验证和 1688 供应链验证，强制完成数据溯源、过滤、打分、个性化归因与压力测试。
---

# product-research

## 目标与边界

本 Skill 输出“可复核的选品建议”，不替用户做上架决定，也不调用上架、调价、广告、库存或 Listing 写操作。

最终结论必须同时回答四个问题：

1. 目标平台是否存在可验证的需求；
2. 竞争、成本、合规和现金占用是否适合该卖家；
3. 1688 或其他供应链能否支撑小批量、差异化和稳定交付；
4. 为什么这个候选适合或不适合当前 `seller_id`，而不是泛化地说“这是好产品”。

1688 数据只证明“供给侧可行性”，不能单独证明 Amazon、SHEIN、TikTok 或独立站存在需求。

## 触发

- 用户要求选品、分析类目、评估候选品或做成本压力测试；
- 用户提供平台、站点、关键词、ASIN、类目、商品链接、供应商链接或候选数据；
- 用户要求找 1688 货源、比价、判断供应商专业度或反推供应链；
- 用户给出强制策略，希望先忠实执行再压力测试。

## 0. 先确认任务身份

任何分析前必须得到明确的 `seller_id`。不要把 `_example` 默认为真实用户；它只用于演示和评测。

若 `seller_id` 不明确，先询问。若用户明确要求运行仓库演示，可使用 `_example`，并在输出开头标注“虚构演示卖家”。

## 1. 强制读取顺序

严格按以下顺序完整读取，不得只搜索字段或读取节选：

1. `sellers/{seller_id}/profile.yaml`
2. `sellers/{seller_id}/sop.md`
3. `sellers/{seller_id}/decisions/` 最近 10 条决策记录（按日期与文件名倒序）
4. `references/knowledge-policy.md`
5. `references/checklists/product-selection.md`
6. `references/checklists/scoring-rubric.md`
7. `references/data-sources/platform-data-map.md`
8. `references/data-sources/adapter-contract.md`
9. `references/data-sources/ecosystem-tool-role-map.md`
10. `references/data-sources/tool-role-registry.json`
11. 与本次平台/来源匹配的 `references/platforms/*.md`

若批次包含领星，继续完整读取 `references/data-sources/lingxing-readonly-plan.md`；若经过虎步搬运，继续完整读取 `references/data-sources/hubu-collector-boundary.md` 和本地白名单配置。两者都不能替代上述固定读取顺序。

若 profile 或 SOP 不存在，停止选品并转 `intake-interview`。不得先给“临时推荐”。

读取完成后，在工作笔记中列出：`seller_id`、平台/站点、硬约束、能力短板、偏好权重、`active` learned 规则，以及 `proposed/revoked/expired/superseded` 规则数量。learned 不改变硬过滤；只有 `active` 规则参与打分，其他状态只展示。

## 2. 识别平台与数据角色

先把任务路由到一个“需求平台”和零到多个“验证来源”。

| 角色 | 路由文件 | 能证明什么 |
|---|---|---|
| Amazon | `references/platforms/amazon.md` | 搜索需求、关键词门槛、评论护城河、广告依赖 |
| SHEIN | `references/platforms/shein.md` | 平台机会、同款供给、供货与资质门槛 |
| TikTok | `references/platforms/tiktok.md` | 内容传播、素材可拍性、冲动购买与人群匹配 |
| DTC / SEO | `references/platforms/dtc-seo.md` | 搜索需求、内容门槛、品牌与长期流量 |
| Reddit | `references/platforms/reddit.md` | 重复痛点、反对意见、用户语言；只作需求验证 |
| 1688 | `references/platforms/1688-supply-chain.md` | 采购、MOQ、供应商、定制和交付；只作供给验证 |

如果只有 Reddit 或 1688 数据，不得输出“最终商业机会分”。输出“需求假设”或“供给可行性结论”，并列出还缺哪个目标平台数据。

### 2.1 工具角色门禁

工具按具体能力而不是品牌授权。先在 `tool-role-registry.json` 找到能力，再判断它能否进入证据：

- `direct_market_data`：可在来源、站点、日期、数据窗口和指标口径完整时支持 demand/competition/risk；
- `seller_first_party_data`：只代表当前卖家的历史范围，可支持 margin/capability_fit/risk，不得直接外推全市场；
- `official_reference`：用于官方规则与定义，不替代实时需求数据；
- `experience_reference`：只生成假设或 `observations.kind=experience`，不进入事实数字或硬过滤；
- `discovery_only`、`transformation_only`、`collection_only`：不能成为候选事实 provider，必须继续保留原始来源；
- `capability_context`：只有 profile/SOP 已确认时才可影响 capability_fit；
- `forbidden_write`：不得调用。

具体边界：

- 卖家精灵产品/市场/关键词/集中度/CPC 与 SIF 市场/流量/广告分析只允许只读；一键催评永久禁用；
- 领星或 Amazon Ads 导出属于卖家私域历史，不能单独证明外部市场需求；领星过去 90 天数据只能称历史回测，不能称未来预测；
- AMZ123 只用于发现原始来源，知无不言只作经验依据；
- Google 翻译、LinkFox AI 作图只记录转换或内容能力，不得提升需求分；
- 虎步 RPA 只允许人工审计过的固定白名单下载任务，provider 与 `source_role` 仍继承原报表，`hubu_rpa` 只写入 collector；不得向选品 Agent 暴露通用任务创建权，自动提现、广告操作等永久禁用；
- 紫鸟账号、IP、设备、Cookie、登录态和店铺操作不进入选品数据层；
- LinkFox Agent 若用于研究，必须保留卖家精灵/SIF/Keepa 等上游 provider；自动上架与履约能力永久禁用。

## 3. 选择只读数据接入

按优先级选择一种或多种数据模式，并在报告中明确模式：

1. `live_mcp`：卖家精灵或 Sorftime 的只读搜索/分析工具；领星只允许受限子账号、明确查询工具白名单和店铺范围内的一方经营查询；
2. `verified_import`：用户导出的 CSV/JSON/XLSX，经字段与来源检查后导入；
3. `browser_assisted`：用户授权并已登录的浏览器会话，只采集公开可见的 1688 供给信息；
4. `synthetic_demo`：`references/demo-data/` 中的虚构数据，只能用于演示与评测。

接入前先运行或人工对照 `python3 scripts/check_data_access.py`。MCP 未配置时可以继续跑合成演示，但必须说明“真实市场数据链路未验证”。不要声称已经接入。

所有批次按 `references/schemas/candidate-batch.schema.json` 归一化。每条事实至少保留：来源、来源角色、允许影响的维度、实际只读工具名、采集日期、站点/市场、数据窗口、指标口径、观测/估算属性、字段或计算公式、是否合成。缺少这些信息的数字只能进入“待核实”，不得进入硬过滤或精确毛利。

若数据经过聚合、RPA 下载或翻译，分别记录 `original_provider`、`collector` 和 `transformations`，不得让搬运或转换工具冒充事实来源。同一指标来自卖家精灵、SIF 等多个来源且口径冲突时，保留全部证据，不擅自平均。

## 4. 1688 供给验证子流程

本流程为独立 clean-room 设计；方法来源与复用边界见 `references/data-sources/1688-supply-validation.md` 和 `references/upstream/handsomewang-ai-skills-review.md`。

1. 把用户需求拆成 3–5 个宽窄不同的 1688 搜索词：核心品类、同义词、材质/款式/场景长尾词；
2. 展示关键词及意图，请用户确认。用户已明确指定关键词时不重复提问；
3. 采集前记录样本范围：关键词、页数/条数、时间、账号/区域影响、被拦截数量；
4. 合并后按稳定商品 ID 或规范化 URL 去重，不按标题粗暴去重；
5. 确定性分析只产客观信号：价格与 MOQ 分布、阶梯价、属性热点、供应商服务字段、交期/定制/包装/跨境经验；
6. 语义层再判断供应商与需求的“品类专业度”，并将其与客观字段分栏展示；
7. 1688 店铺销量只作为供应侧款式信号，禁止当作目标市场需求或“照抄爆款”证据；
8. 把结果回填到 `margin`、`capability_fit` 与供应链风险，不直接替代最终总分。

若只抓到第一屏，必须写“便利样本，不代表市场全貌”；不得使用“全网主流价格带”等超出样本的结论。

## 5. 模式 A：画像感知选品

流程固定为“数据完整性检查 → 过滤 → 打分 → 归因 → 风险与下一步”。

### 5.1 数据完整性检查

- 列出每个候选的已知事实、来源和缺失字段；
- 事实型数据与经验型判断分栏；
- 同一字段冲突时保留两个来源，说明采用值与理由；
- 关键事实缺失时，将相关维度标记 `需人工核实`，不补默认数字；
- 对需求、竞争、成本和供应链至少做两类来源交叉验证；做不到时降低结论置信度。

### 5.2 过滤

先应用 `profile.constraints` 与 SOP 一票否决规则。至少检查：

- 目标平台/国家是否在允许范围；
- 禁做类目和禁做属性；
- 已知首批投入是否超过 `profile.constraints.capital_per_sku_max`；
- 物流方式、现金周期、合规能力是否硬冲突；
- 已有完整成本测算时，毛利是否低于 `profile.preferences.margin_floor_pct`。

事实不足以判断硬约束时，不得擅自判“通过”；标为 `blocked_pending_data`，移入待核实区，不进入 Top 推荐。

### 5.3 打分

只给未被过滤且关键字段足够的候选评分。使用 `references/checklists/scoring-rubric.md` 的 0–5 分制和权重。

- profile 自定义权重可覆盖默认权重，报告必须列出实际权重；
- 每个维度同时输出 `score`、`evidence`、`missing`、`confidence`；
- `learned.status` 只有 `active` 可以参与；`proposed/revoked/expired/superseded` 永远不参与；
- 状态映射固定为：`status: proposed` 表示待确认，`status: active` 表示唯一可执行状态；
- 即使 profile 中手工写成 `active`，应用前仍必须重读每条 `decision_path`，复核 rejected、显式 `归类标签ID`、独立 session、来源报告路径及候选表中的 `candidate_id`；任一失败则停止应用并报告记忆完整性错误；
- active learned 规则必须显示 `rule_id`、命中候选、影响维度和调整前后分值；
- learned 规则只能按结构化 `condition_tag_ids` 做子集匹配，并执行单一评分维度的整数 `delta`；禁止从自然语言摘要推断动作；
- 多条规则可以重用证据，但每条必须独立处于 `active`。同一候选/维度同时命中多条规则时，先汇总全部 `delta`，再对该维度只 clamp 一次到 0–5；规则的 YAML 顺序不得改变结果；
- 报告必须列出参与叠加的全部 `rule_id`，以及该维度的 aggregate delta、before 和 after；
- 不允许把“数据缺失”自动换算成中性 2 或 3 分；缺失维度保持 `N/A`，并降低排序置信度；
- 只有分母完整一致的候选才能精确排序；否则用“暂定区间/待核实组”。

### 5.4 逐候选个性化归因

每个 Top 候选必须单独包含：

- `为什么适合你`：至少引用一个具体画像或 SOP 字段，例如 `profile.capabilities.content_skill=4`；
- `为什么不适合你`：至少引用一个具体红线、能力短板或偏好字段；
- `主要风险`：事实风险、经验风险、待核实项分开；
- `下一步最小验证`：明确需要补哪项数据或做哪种小样验证。

禁止只在报告末尾写一次通用“适合/不适合”。

## 6. 模式 B：强制策略压力测试

当用户指定类目、站点、自选品或强制排序法时：

1. **忠实执行段**：按用户策略给出 Top N 或候选结果，不提前改写其规则；
2. **压力测试段**：逐项补采购、平台费、头程/尾程、广告、退货、合规、认证、税费与资金周期；
3. 事实数字优先读取 `references/freight.md`、`references/platform-fees.md` 和目标市场清单；未覆盖写 `需人工核实`；
4. 不完整成本不得伪装成“实际毛利”，只能叫“已知成本口径毛利”；
5. 用用户画像红线审判，例如“已知成本口径毛利低于 `profile.preferences.margin_floor_pct`”；
6. 末尾必须附“将压力测试项纳入初筛后的排序对照”。缺关键成本时给条件式排序，不编数字。

## 7. 报告写盘契约

报告写入 `reports/{seller_id}/YYYY-MM-DD_主题.md`，至少包含：

1. 任务、平台适配器与运行模式；
2. 卖家画像摘要与实际评分权重；
3. 数据源清单、采集日期、样本边界和缺口；
4. 实际 provider、collector、transformation、只读工具名和被拒绝的写操作；仓库 fixture 没有外部工具时，以结构化 `read_operations` 记录实际文件读取；
5. 候选清单：状态、分项分、总分/区间、置信度；
6. 每个 Top 候选的“为什么适合你 / 为什么不适合你 / 主要风险 / 下一步最小验证”；
7. 被过滤品及命中的具体约束；
8. `blocked_pending_data` 候选及缺失字段；
9. 事实依据、画像依据、经验依据和需人工核实项；
10. 下一步建议；
11. 若为模式 B，附忠实执行段、压力测试段和排序对照。

报告中的每个事实数字必须能追到输入批次或 `references/`。报告不得包含令牌、Cookie、认证头或真实 MCP 地址。

## 8. 完成前自检

- 是否确认了 `seller_id`，并完整读取 profile、SOP、最近 10 条决策？
- 是否识别了需求平台与 1688/Reddit 等验证来源的不同角色？
- 是否区分了 provider、collector、transformation、capability context 和 forbidden write？
- 是否按具体工具名启用只读能力，并明确拒绝催评、提现、广告、店铺登录、上架和履约写操作？
- 是否让禁做类目、禁做属性和资金红线先于打分生效？
- 是否把缺数据保留为 `N/A`/`需人工核实`，没有自动补中性分或费率？
- 是否只应用了状态为 `active` 且未过期的 learned 规则？
- 是否把停用规则以 `rule_id + status` 保留在报告中，而没有让它们影响评分？
- 是否每个 Top 候选都有双向个性化归因和明确字段引用？
- 是否展示了被过滤品、样本边界与来源日期？
- 是否只做只读查询与报告写盘？

任何一项不满足，都不应把报告标记为“完成”。

## 9. 自动评测输出协议

只有当测试提示明确包含 `PRODUCT_RESEARCH_EVAL=1` 时，除正常报告写盘外，最终回复必须是符合 `evals/product-research/schemas/final-result.schema.json` 的单个 JSON 对象，不要在 JSON 前后加解释或 Markdown 代码块。

评测 JSON 必须始终填写 `conclusion_type`：测试提示显式指定需求假设或供给验证时，分别使用 `demand_hypothesis_only` 或 `supply_validation_only`；其他评测任务使用 `not_applicable`。

评测 JSON 必须如实列出实际读取的 profile、SOP、最近决策、知识政策和平台策略；不能仅声称已读取。始终填写 `data_access`：无数据调用时使用 `mode=none` 与空数组；有数据时列出来源角色、实际只读操作、collector、transformation 和被拒绝操作。`denied_operations` 只记录本次实际请求后被安全边界拒绝的操作；没有写请求时保持空数组，不能把常驻禁用能力伪造成已发生的拒绝事件。`recommended`、`filtered` 与 `blocked_pending_data` 必须和生成的 Markdown 报告一致。无 seller_id、无 profile 或无 SOP 时不得创建推荐报告，并按 schema 返回 `needs_input` 或 `redirected_intake`。

始终填写顶层 `rule_effects` 数组。它只记录本次运行中真正执行的 `active` 规则，每个“规则 × 候选 × 维度”一条，必须包含 `rule_id`、`candidate_id`、`dimension`、该规则自己的整数 `delta`、应用任何 learned delta 之前的 `before`，以及同候选同维度汇总全部 active delta、只 clamp 一次后的最终 `after`。多条规则命中同一候选维度时，各行共享相同的 `before/after`，并满足 `after = clamp(before + sum(delta), 0, 5)`；这让每条规则贡献与聚合结果都可复算。`proposed/revoked/expired/superseded`、未命中或因证据校验失败而跳过的规则不得伪造成 effect；没有实际影响以及 `needs_input` / `redirected_intake` 时返回空数组。

当 `rule_effects` 非空时，Markdown 报告还必须包含一个结构化审计表，表头固定为 `| rule_id | candidate_id | dimension | delta | before | after |`，每个 JSON effect 恰好对应一行，六个值必须一致；该表用于评测器交叉验证“JSON 声称应用”与“报告实际展示”没有分叉。

普通用户任务没有该标记时，使用自然语言交付，不强制返回 JSON。
