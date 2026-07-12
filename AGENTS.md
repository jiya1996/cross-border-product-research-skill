# AGENTS.md

## 项目目标

在一个 Git 仓库内搭建"卖家画像记忆 + 选品决策"系统。执行引擎使用 Codex CLI，数据层接入卖家精灵 MCP（或 Sorftime MCP），分析框架基于开源 skill 改造；本项目唯一自研的是记忆层（画像 + SOP + 决策日志）以及把记忆注入选品流程的编排。

## 核心设计原则

1. **记忆 = 文件，不是数据库。** 所有记忆以 YAML/Markdown 存在 Git 仓库中，可 diff、可回滚、可人工编辑。禁止引入向量库、embedding、外部数据库，除非后续明确要求。
2. **拒绝样本优先。** 用户拒绝一个推荐时必须记录拒绝理由并归类，拒绝记录是画像更新的第一信号源。
3. **建议式输出，不自动执行。** 所有产出是报告和建议，不直接调用任何写操作 API（不上架、不调价、不改广告）。
4. **每条推荐必须带个性化归因。** 输出格式强制包含"为什么适合你 / 为什么不适合你"段落，且必须引用画像中的具体字段（如 `profile.资金上限`、`sop.禁做类目`），不允许泛泛而谈。
5. **多用户隔离。** 每个卖家一个独立目录，skill 和脚本共享，数据绝不共享。
6. **事实数据禁止编造。** 运费费率、合规要求、认证费用、税费等事实性数字只能来自 `references/` 目录下的清单文件或公式计算，输出时标注来源；references 未覆盖的项必须输出"需人工核实"，禁止模型凭记忆给出具体数字。

## 强制流程

- 任何选品任务开始前，必须先确认 `seller_id`。
- 读取顺序固定为：完整读取 `sellers/{seller_id}/profile.yaml`，再完整读取 `sellers/{seller_id}/sop.md`，再读取 `sellers/{seller_id}/decisions/` 下最近 10 条决策记录。
- 如果 `sellers/{seller_id}/profile.yaml` 或 `sellers/{seller_id}/sop.md` 不存在，先触发 `skills/intake-interview` 建档流程；禁止在无画像状态下输出选品推荐。
- 建档必须以 `references/schemas/profile-template.yaml` 和 `references/schemas/sop-template.md` 为准；画像字段不得自由发挥。
- 任何选品任务都必须读取 `references/knowledge-policy.md`，区分事实型知识、经验型知识、用户画像知识和推断型知识。
- 选品任务必须先识别平台/来源：Amazon、SHEIN、TikTok、DTC/SEO、Reddit、1688 或 unknown；再读取 `references/platforms/` 下对应策略文件。
- 选品分析必须遵循"过滤 -> 打分 -> 归因"。过滤使用 `constraints` 一票否决；打分使用 `references/checklists/scoring-rubric.md`、`capabilities`、`preferences` 和状态为 `active` 的 `learned` 规则；归因必须引用画像或 SOP 的具体字段。
- 用户反馈推荐结果时，必须使用 `skills/recommendation-review` 将接受、拒绝或观察记录写入对应卖家的 `decisions/` 目录。
- 画像自更新只能由 `skills/profile-update` 基于决策日志生成候选规则；`learned.status` 的唯一可执行状态是 `active`。`proposed`、`revoked`、`expired`、`superseded` 均不得参与推荐打分。

## 知识库纪律

- `references/platforms/` 存放平台策略，只作为经验型策略和数据处理框架。
- `references/checklists/` 存放选品确认清单，用于过滤、打分和报告结构。
- `references/questions/` 存放访谈问题库，用于建档和缺口访谈。
- `references/data-sources/` 存放平台数据字段映射，用于 MCP/API 接入和缓存规范。
- 生财、有术、Reddit、卖家复盘等内容只能作为"经验依据"，不得作为事实数字。
- 当经验策略与卖家画像冲突时，以卖家画像和 SOP 为准。

## 输出纪律

- 推荐报告统一写入 `reports/{seller_id}/`。
- 报告命名统一为 `YYYY-MM-DD_主题.md`，日期使用当前本地日期。
- 每份报告必须包含候选清单、个性化适配理由、主要风险、被过滤品及原因。
- 强制策略压力测试报告必须分为"忠实执行段"和"压力测试段"，并在末尾附成本纳入初筛后的排序对照。

## 安全纪律

- MCP 仅用于只读数据查询和分析；禁止调用任何平台写操作，包括但不限于上架、调价、改广告、改库存、改 Listing。
- 密钥、令牌、真实 MCP 地址等敏感配置只能来自环境变量或本地用户配置，禁止写入仓库。
- 不要提交 `.env`、项目级 `.codex/config.toml`、本地密钥文件、平台后台导出的敏感原始数据。
- 当前 GitHub 仓库如保持公开，真实 `sellers/` 和 `reports/` 数据不得提交；只允许提交 `.gitkeep` 和 `_example/` 虚构演示数据。
- 事实性数字只能引用 `references/` 内的清单或公式；没有覆盖时写"需人工核实"。
- 不引入数据库、向量库、embedding 服务或外部持久化系统，除非用户后续明确要求。
