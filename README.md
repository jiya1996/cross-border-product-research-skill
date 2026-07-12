# 跨境电商 AI 选品 Skill

这是一个“卖家画像记忆 + 跨平台选品决策 + 可重复评测”的 Codex Skill 包。它不是另一个通用市场数据工具，而是放在市场数据与卖家经营系统之上的、可审计的卖家专属决策记忆层：保存每次接受、拒绝及其理由，并且只有经人工确认的规则才会影响下一轮过滤、评分和归因。

它不把“销量高”直接当答案，而是按固定顺序执行：确认 `seller_id` → 读取 profile/SOP/最近决策 → 识别平台与数据角色 → 数据溯源 → 硬过滤 → 可复算评分 → 逐候选个性化归因 → 风险与最小验证。

当前状态：**Skill、合成 demo、离线单测、黑盒评测 cases 和一键录屏轨迹均可运行；记忆闭环只在合成数据中可复现，真实卖家精灵/SIF/Sorftime/领星数据及真实经营效果尚未验证。**

录屏开场定位、对外表述护栏和分层图见 `references/demo-opening-positioning.md`。不要把“跨工具决策记忆缺口”说成“所有工具都无状态”或“市场上无人做”。

本次交付的完成度、验证证据和剩余真实数据缺口见 `DELIVERY_STATUS.md`。

交给 Claude 或其他模型做全量评审时，请从 `CLAUDE_REVIEW.md` 开始；其中包含建议阅读顺序、已验证/未验证边界和要求的评审格式。

## 核心 Skill

- `skills/intake-interview/SKILL.md`：建立卖家 profile 与 SOP；
- `skills/product-research/SKILL.md`：跨平台选品、1688 供给验证与压力测试；
- `skills/recommendation-review/SKILL.md`：记录接受、拒绝和观察反馈；
- `skills/profile-update/SKILL.md`：从决策日志生成待人工确认的 learned 规则。

记忆全部是 YAML/Markdown 文件。真实卖家数据按目录隔离，不使用数据库、向量库或 embedding。

## 先验收交付包

```bash
python3 scripts/verify_delivery.py
```

该命令依次运行：仓库结构校验、26-case 静态契约、8 个行为单测、数据接入状态检查和一份新的合成选品报告。

从 ZIP 解压到新目录后，先注册项目 Skill：

```bash
python3 scripts/install_project_skills.py
```

单独运行：

```bash
python3 scripts/validate_repo.py
python3 -m unittest discover -s tests -v
python3 scripts/run_product_research_evals.py --mode static
python3 scripts/check_data_access.py
```

## 一键录屏演示

```bash
python3 scripts/run_video_demo.py
```

脚本使用独立虚构卖家 `video-demo`，自动完成：

1. `learned: []` 的干净首轮推荐；
2. 从 3 条重复拒绝生成 `confirmed: false` 候选规则；
3. 未确认重跑，证明排序不变；
4. 人工确认规则；
5. 再次重跑，证明命中候选降权和排序变化；
6. 生成 `reports/video-demo/YYYY-MM-DD_video-full-trace.md`。

详细镜头和话术见 `references/demo-script.md`。

## 黑盒评测

评测说明、100 分 rubric 与 26 个 product-research cases 在 `evals/product-research/`；4 个真人复盘验收 cases 在 `evals/intake-retrospective/`。

```bash
python3 scripts/run_product_research_evals.py --list
python3 scripts/run_product_research_evals.py --mode agent --case E00
python3 scripts/run_product_research_evals.py --mode agent --case T01 --keep-workdir
python3 scripts/run_product_research_evals.py --mode agent --suite core
```

Agent 模式会在临时工作区启动新的 `codex exec`。评分器同时检查最终 JSON、生成的 Markdown 报告和文件 diff，避免 Agent 只在回复中自报合格。运行 Agent cases 会消耗模型时间/额度；默认只跑 static。

关键覆盖：

- 无 seller_id/profile/SOP 必须停止；
- 禁做类目、属性和超资金一票否决；
- 缺事实不补中性分或费率；
- unconfirmed learned 不参与，确认后才改变排序；
- Amazon/TikTok 路由变形；
- 强制策略的忠实执行、成本压力测试和排序反转；
- Reddit 只作需求验证，1688 只作供给验证；
- 卖家精灵/SIF 的来源角色、指标冲突与估算口径；
- 紫鸟、AMZ123、领星、知无不言、翻译、RPA 和 LinkFox 不得冒充市场需求证据；
- 催评、提现、广告、店铺登录、自动上架和履约写能力的拒绝；
- 多卖家隔离、零平台写操作、数据内提示注入防护。

## 数据接入

生产优先级：只读卖家精灵/SIF MCP → Sorftime 交叉验证 → 用户核实导入 → 用户授权的 1688 浏览器辅助 → 合成 demo。

配置说明见 `config/mcp.md`，统一数据结构见：

- `references/data-sources/adapter-contract.md`
- `references/data-sources/ecosystem-tool-role-map.md`
- `references/data-sources/tool-role-registry.json`
- `references/schemas/candidate-batch.schema.json`
- `references/data-sources/platform-data-map.md`

卖家经营真值先走脱敏、核实过的领星 CSV/XLSX 历史回测，再评估官方 MCP/OpenAPI；具体只读范围、权限风险和 90 天回测口径见 `references/data-sources/lingxing-readonly-plan.md`。虎步只允许作为人工批准的报表投递器，边界见 `references/data-sources/hubu-collector-boundary.md`，不得把通用 RPA 调用权交给选品 Agent。

`check_data_access.py` 只检查变量和配置是否存在，不打印任何值。必须在 Codex `/mcp` 中看到真实只读工具并完成一次最小查询后，才可以声称 live MCP 已验证。

## HandsomeWang/AI_SKILLS 怎么用

该项目适合作为 **1688 供给侧研究思路**，不是完整跨境选品决策 Skill。我们 clean-room 吸收了关键词组合、样本边界、客观分析与语义匹配分层等通用方法，并加入自己的画像、跨平台需求、成本、合规、反馈记忆和评测层。

截至 2026-07-11，上游未声明许可证，因此本仓库没有复制其代码、提示词或报告模板。审计见 `references/upstream/handsomewang-ai-skills-review.md` 与 `THIRD_PARTY_NOTICES.md`。

## 合成 demo

直接运行旧式单轮 demo：

```bash
python3 scripts/run_demo.py --seller-id _example --label before
```

恢复 `_example` 干净基线：

```bash
python3 scripts/reset_demo.py          # dry run
python3 scripts/reset_demo.py --yes    # 实际恢复 learned: []
```

所有 demo 价格、MOQ、重量、运费、费用和换算都明确标为合成数据。报告中的毛利只能称“已知演示成本口径毛利”，不构成真实建议。

## 数据安全

- MCP 只读，禁止上架、调价、广告、库存和 Listing 写操作；
- 真实 URL、密钥、Cookie、Token 和认证头不入仓；
- `.gitignore` 忽略真实 `sellers/*`、`reports/*` 和黑盒评测 artifacts；
- 公开仓库只保留 `_example` 与合成 fixtures；
- 事实数字只能来自带来源的 `references/` 或可复算公式，否则写“需人工核实”。

生成公开安全的交付 ZIP：

```bash
python3 scripts/build_release.py
```

构建脚本使用显式 allowlist，并验证 ZIP 中没有真实卖家、生成报告、评测轨迹、`.env` 或密钥文件。

## 真实使用前仍需完成

1. 取得卖家精灵或 SIF MCP 的只读地址与令牌，Sorftime 可作替代/交叉验证；
2. 完成工具名到 candidate-batch 字段的映射和一次 live smoke；
3. 为目标国家补 `references/markets/` 合规清单；
4. 录入合作方真实运费、平台费、广告/退货口径；
5. 用一个真实在售品跑模式 B，和经营数据核对一笔隐性成本。
6. 用 `references/questions/recent-selection-retrospective.md` 回放一位卖家最近一次真实选品，区分“当时决定”与“后来结果”。
