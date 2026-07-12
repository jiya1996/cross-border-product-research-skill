# 个性化选品 Agent 执行方案（Codex 执行版）

> 交给 Codex 的总目标：在一个 Git 仓库内搭建"卖家画像记忆 + 选品决策"系统。
> 底层不自研：执行引擎用 Codex CLI，数据用卖家精灵 MCP（或 Sorftime MCP），
> 分析框架 fork 开源 skill（liangdabiao/amazon-sorftime-research-MCP-skill）。
> 本项目唯一自研的东西是：记忆层（画像 + SOP + 决策日志）和把记忆注入选品流程的编排。

---

## 0. 核心设计原则（Codex 在所有任务中必须遵守）

1. **记忆 = 文件，不是数据库。** 所有记忆以 YAML/Markdown 存在 Git 仓库中，可 diff、可回滚、可人工编辑。禁止引入向量库、embedding、外部数据库，除非后续明确要求。
2. **拒绝样本优先。** 用户拒绝一个推荐时必须记录拒绝理由并归类，拒绝记录是画像更新的第一信号源。
3. **建议式输出，不自动执行。** 所有产出是报告和建议，不直接调用任何写操作 API（不上架、不调价、不改广告）。
4. **每条推荐必须带个性化归因。** 输出格式强制包含"为什么适合你 / 为什么不适合你"段落，且必须引用画像中的具体字段（如 `profile.资金上限`、`sop.禁做类目`），不允许泛泛而谈。
5. **多用户隔离。** 每个卖家一个独立目录，skill 和脚本共享，数据绝不共享。
6. **事实数据禁止编造。** 运费费率、合规要求、认证费用、税费等事实性数字只能来自 `references/` 目录下的清单文件或公式计算，输出时标注来源；references 未覆盖的项必须输出"需人工核实"，禁止模型凭记忆给出具体数字。

---

## 1. 仓库目录结构（Task 0 交付物）

```
product-picker/
├── AGENTS.md                    # Codex 的项目级指令（见第2节）
├── config/
│   └── mcp.md                   # MCP 接入说明：卖家精灵 MCP 的 URL/密钥配置方法
├── references/                  # 事实数据层（人工维护，模型只引用不编造）
│   ├── markets/                 # 国家×合规检查清单，如 de.md（EPR/LUCID、VAT、GPSR，
│   │                            #   含费用区间与官方来源链接）、jp.md …
│   ├── freight.md               # 头程费率表 + 体积重/抛比计算公式
│   └── rejection-tags.md        # 拒绝原因标签集定义（供 recommendation-review 使用）
├── skills/                      # 共享技能层（fork + 自研）
│   ├── intake-interview/        # 自研：新卖家访谈建档
│   │   └── SKILL.md
│   ├── product-research/        # fork 开源后改造：画像感知的选品
│   │   └── SKILL.md
│   ├── recommendation-review/   # 自研：记录用户对推荐的反馈
│   │   └── SKILL.md
│   └── profile-update/          # 自研：周期性从决策日志提炼画像更新
│       └── SKILL.md
├── sellers/                     # 记忆层（每个卖家一个目录）
│   └── {seller_id}/
│       ├── profile.yaml         # 静态画像：能力与约束
│       ├── sop.md               # 该卖家的选品 SOP / 决策规则
│       ├── decisions/           # 决策日志（追加式，一次推荐一个文件）
│       │   └── 2026-07-06_pet-grooming.md
│       └── outcomes/            # 结果回填（可选，后期）
└── reports/                     # 每次选品运行的输出报告
    └── {seller_id}/
```

---

## 2. AGENTS.md 内容要求（Task 0 交付物）

Codex 需生成 AGENTS.md，至少包含：

- 项目目标一句话说明。
- 强制流程：任何选品任务开始前，必须先完整读取 `sellers/{seller_id}/profile.yaml` 和 `sop.md`，再读取 `decisions/` 下最近 10 条记录；如果画像不存在，先触发 intake-interview 技能，禁止在无画像状态下出推荐。
- 输出纪律：推荐报告写入 `reports/{seller_id}/`，命名 `YYYY-MM-DD_主题.md`。
- 安全纪律：只读数据 MCP，禁止任何平台写操作；密钥只从环境变量读取，禁止写入仓库。
- 第 0 节的六条设计原则原样收录。

---

## 3. 画像 Schema：profile.yaml（Task 1 交付物）

Codex 需实现以下 schema 并附一份填好的示例。字段分四组：

```yaml
meta:
  seller_id: ""
  created: ""
  last_updated: ""
  updated_by: ""            # interview / profile-update / manual

# A. 硬约束（违反即一票否决，选品时作为过滤器）
constraints:
  capital_per_sku_max: 30000      # 单品最大可投入（含首批货+头程+广告，CNY）
  cash_cycle_tolerance_days: 90   # 可接受的资金回笼周期
  forbidden_categories: []        # 禁做类目（如带电、液体、大件）
  forbidden_attributes: []        # 禁做属性（如需FDA认证、侵权高风险）
  target_marketplaces: []         # 只考虑这些站点
  logistics_modes: []             # 可用物流方式（FBA/FBM/海外仓）

# B. 能力画像（用于打分加权，不是过滤）
capabilities:
  supply_chain: ""          # none / 1688代发 / 有工厂资源 / 自有工厂
  ad_skill: 1               # 1-5，广告投放能力自评
  content_skill: 1          # 1-5，图片视频素材能力
  compliance_experience: [] # 有经验的认证类型（CE/FDA/儿童产品等）
  language_ops: []          # 能覆盖的运营语言
  team_size: 1

# C. 偏好画像（软性，影响排序）
preferences:
  risk_appetite: ""         # conservative / balanced / aggressive
  competition_tolerance: "" # 避开红海 / 敢打价格战
  product_style: []         # 如：功能改良型 / 微创新 / 跟卖差异化
  margin_floor_pct: 30      # 毛利率红线
  review_moat_max: 500      # 竞品平均评论数超过此值视为门槛过高

# D. 学习到的规则（只允许 profile-update 技能写入，人工确认后生效）
learned:
  - rule: ""                # 如"用户连续3次拒绝季节性产品→季节性列为负向因子"
    evidence: []            # 指向 decisions/ 中的文件
    confirmed: false        # 人工确认前不参与打分
```

**验收标准：** schema 有注释、有示例；`learned` 区块必须带 `evidence` 和 `confirmed` 字段，未确认的规则不得影响推荐。

---

## 4. 四个自研技能的规格

### 4.1 intake-interview（新卖家建档，双入口）

- 触发：`sellers/` 下没有该卖家目录，或用户说"新建卖家档案"。
- **槽位清单**：SKILL.md 内维护一张槽位表，每个槽位标注四个属性——
  对应 profile.yaml 的字段路径、类型（封闭枚举 / 开放数值 / 开放文本）、
  是否必填（`capital_per_sku_max` 与 `margin_floor_pct` 为必填）、追问策略。
  封闭槽位用 AskUserQuestion 选项式提问；数值与自由口述类直接开放式问。
- **入口 A：文档/文字导入（优先推荐）。** 用户提供选品笔记、内部文档或
  一段文字时：
  1. 解析并映射到槽位清单，每个抽取值必须带 `source` 标记：
     `document`（原文明确写出，附原文引用）或 `inferred`（推断）；
     **inferred 值一律不直接写盘，必须进入缺口访谈确认。**
  2. 缺口访谈只问三类：必填槽仍为空、inferred 待确认、文档内部矛盾项。
     已从文档确认的槽位禁止重复提问。
  3. 规则类语句（"评论超 500 的头部品不碰"）单独摘出汇入 sop.md，保留原文出处。
- **入口 B：对话访谈。** 无输入材料时按组提问（硬约束→能力→偏好），
  每组不超过 4 问；每轮回答后先扫描空槽再决定下一组问题（允许一答多填），
  循环至必填槽全满。答不出的填 null 加 TODO，模糊回答追问一次后降级为 null，
  禁止编造默认值。最后让用户口述"你平时怎么判断一个品能不能做"，
  整理为 sop.md 规则清单。
- **冲突优先级（写死）**：用户当场所述 > 文档所写 > 模型推断；同源之间新值覆盖旧值。
- **写盘前确认**：展示抽取结果表（槽位 / 填入值 / 来源与原文引用），
  用户确认后才写入 `profile.yaml` + `sop.md`。
- 验收标准：同一份用户文档跑入口 A，重复提问数为 0（已覆盖槽位不再问）；
  产出画像经本人确认"这写的是我"。

### 4.2 product-research（画像感知选品，fork 开源改造）

- 基底：fork `liangdabiao/amazon-sorftime-research-MCP-skill` 中的市场/品类/关键词分析流程，数据源改为已配置的 MCP。
- 改造点（这是本项目的核心工作量）：
  1. 运行前强制加载画像三件套（profile / sop / 最近决策）。
  2. 流程分三段：**过滤**（用 constraints 一票否决）→ **打分**（用 capabilities + preferences 加权）→ **归因**（每个候选品输出适配理由）。
  3. 打分维度至少含：预估单品投入 vs 资金上限、毛利测算 vs 毛利红线、
     竞品评论护城河 vs review_moat_max、广告依赖度 vs ad_skill、
     合规要求 vs compliance_experience、与 learned 规则的冲突检查。
  4. 输出报告模板固定为：候选清单表（品名/类目/核心数据/总分）＋
     每个品的"为什么适合你"（引用画像字段）＋"主要风险"＋
     "被过滤掉的品与原因"（这一节必须有，让用户看到系统懂他的边界）。
- **模式 B：强制策略压力测试。** 当用户给出强制策略（指定类目/站点/自选品）时，
  不做过滤干预，改为输出双段式报告：
  1. **忠实执行段**：完全按用户策略选出 Top N，一个字不质疑。
  2. **压力测试段**：对每个候选品补齐用户未计入的成本项，全部折算进
     单件毛利：体积重头程（按 `references/freight.md` 公式）、目标国
     合规成本（按 `references/markets/{国家}.md` 清单）、类目退货率折算。
     每项标注来源；references 未覆盖的输出"需人工核实"。
     结论句强制用用户自己的红线审判：如
     "实际毛利 21%，低于你设定的 30% 红线（profile.margin_floor_pct）"。
  3. 报告末尾附对照小节："若将上述成本纳入初筛，排序变为……"，只呈现不劝说。
- 验收标准（模式 A）：同一份市场数据，喂两个不同 profile，推荐结果和归因明显不同。这是整个项目的核心验收测试。
- 验收标准（模式 B）：用合作方正在销售的一个真实产品跑压力测试，
  至少算出一笔与其真实经营数据吻合、且其本人认可的隐性成本。

### 4.3 recommendation-review（反馈记录）

- 触发：用户对某次报告给出反馈（"这个可以""这个不行，太吃广告了"）。
- 行为：为每个被评价的品在 `decisions/` 写一个文件，格式：

```markdown
# 2026-07-06 | pet-grooming-glove
- 来源报告: reports/{seller_id}/2026-07-06_宠物类目.md
- 用户决定: rejected        # accepted / rejected / watchlist
- 用户原话: "太吃广告了，这个词CPC得3刀往上"
- 归类标签: [广告依赖度高, CPC超预期]   # 从固定标签集选择，可新增
- 涉及画像字段: capabilities.ad_skill, preferences.margin_floor_pct
```

- 标签集初始化 12 个左右常见拒绝原因（广告依赖、季节性、侵权风险、
  资金占用、物流超限、认证门槛、红海、毛利不足、供应链够不着、
  差异化空间小、退货率高、个人不喜欢），允许增量扩展。
- 验收标准：反馈一句话进来，30 秒内落盘成结构化决策文件。

### 4.4 profile-update（画像自更新）

- 触发：手动运行，或 decisions/ 新增满 10 条。
- 行为：读取全部决策日志，按标签聚合，发现模式（如"rejected 中 60% 带
  '季节性'标签"），生成候选规则写入 `profile.yaml` 的 `learned` 区块，
  `confirmed: false`，并输出一份变更摘要请用户逐条确认。
- 硬性要求：**永远不直接修改 A/B/C 区块**，只能建议；用户确认后才把
  `confirmed` 改为 true。防止画像被模型幻觉污染。

---

## 5. 分阶段任务清单（按顺序喂给 Codex）

| 任务 | 内容 | 验收标准 | 预估 |
|---|---|---|---|
| Task 0 | 建仓库骨架 + AGENTS.md + config/mcp.md（写清卖家精灵 MCP 的 streamableHttp 配置步骤和密钥环境变量约定） | 目录齐全；AGENTS.md 含强制流程 | 0.5 天 |
| Task 1 | profile.yaml schema + 示例 + sop.md 模板 | schema 四区块齐全，learned 带确认机制 | 0.5 天 |
| Task 2 | intake-interview 技能 | 用你老板真人跑一次访谈，产出他的画像和 SOP，他本人认可"这写的是我" | 1 天 |
| Task 3 | fork 开源选品 skill，接 MCP，跑通无画像版分析 | 能对指定类目出一份基础分析报告 | 1–2 天 |
| Task 4 | 改造为画像感知版（过滤→打分→归因，模式 A） | 双画像对照测试通过（见 4.2 验收） | 2–3 天 |
| Task 5 | references 种子数据（先做 1 个目标国清单 + 运费公式）+ 压力测试模式 B | 用合作方正在卖的真实产品跑压力测试，算出一笔其本人认可的真实隐性成本（这是给合作方的首个演示节点） | 2 天 |
| Task 6 | recommendation-review + profile-update | 模拟 10 条反馈，能聚合出至少 1 条合理的候选规则 | 1–2 天 |
| Task 7 | 第二个真实用户接入（老板团队里另一个运营） | 两人画像不同、同类目推荐结果不同，且两人都认可各自归因 | 1 天 |

## 6. 给 Codex 的启动提示词（可直接复制）

```
读取本仓库的《选品记忆Agent执行方案.md》。你的任务是按第 5 节的任务
清单逐个执行，从 Task 0 开始。每个任务完成后停下来，向我展示交付物
并对照验收标准自查，等我确认后再进入下一个任务。全程遵守方案第 0 节
的六条设计原则，特别是：不引入数据库、不做任何平台写操作、每条推荐
必须引用画像字段做归因、事实性数字只来自 references 或公式计算。
```

## 7. 已知风险与对策

1. **结果回填周期长。** 一个品选得对不对要 2–3 个月销售验证。前期不要
   等销售数据，用"用户接受/拒绝"作为代理信号先把学习闭环跑起来；
   outcomes/ 目录留到第二阶段。
2. **画像污染。** 模型可能过度概括（拒绝两次就总结出一条规则）。对策
   已内置：learned 规则需 evidence≥3 条 + 人工 confirmed 才生效。
3. **MCP 成本。** 卖家精灵 MCP 按量计费，product-research 技能中应加
   缓存约定：同一 ASIN/类目 7 天内的查询结果落盘复用，写进 SKILL.md。
4. **开源基底更新。** fork 后与上游解耦，不追更新；只借流程框架，
   数据字段映射自己维护。
5. **事实数据被编造是最大信任风险。** 压力测试的价值完全建立在数字可信上，
   一次编造的合规费用被用户识破，系统信任归零。对策即设计原则第 6 条 +
   references 只增不删 + 每季度人工复核一次费率与法规时效。
6. **范围控制。** Task 0–5 完成即具备对外演示条件，Task 6–7（学习闭环与
   多用户）见效慢，不要为了"功能完整"推迟首次演示；references 首期只做
   1 个国家 1 个类目，跑通后再扩。
