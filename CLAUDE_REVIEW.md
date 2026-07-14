# Claude 全量评审入口

请把本仓库视为一个待交付的“卖家专属决策记忆 + 跨境电商 AI 选品”系统，而不是只评审一段 prompt。

## 建议阅读顺序

1. `README.md`：产品边界、运行与评测入口；
2. `DELIVERY_STATUS.md`：已完成证据与真实数据缺口；
3. `references/demo-opening-positioning.md`：产品定位、竞争表述护栏与演示开场；
4. `AGENTS.md`：项目级不可违背约束；
5. `skills/product-research/SKILL.md`：核心选品工作流；
6. `skills/intake-interview/SKILL.md`、`skills/recommendation-review/SKILL.md`、`skills/profile-update/SKILL.md`：建档、反馈与记忆更新闭环；
7. `references/data-sources/`：数据角色、Candidate Batch、领星和虎步只读边界；
8. `evals/product-research/` 与 `evals/intake-retrospective/`：26 个选品 cases、4 个真人复盘 cases 与评分契约；
9. `scripts/`、`tests/`、`sellers/_example/`、`reports/_example/`：可执行证据与虚构样例。

## 当前已验证

- 仓库结构校验通过；
- 26-case 静态契约通过，100 分 rubric 完整；
- 137/137 行为单测通过；
- learned v2 被测代码提交为 `92e0a6040967e1c7ac9d7bc1a60ea61ec9d53996`；
- 全量 26-case Agent 评测 26/26 PASS，脱敏证据见 `evals/product-research/evidence/20260713_230407_285700/`；
- 独立 P0 评测 23/23 PASS，脱敏证据见 `evals/product-research/evidence/20260713_234711_087988/`；
- 两次正式运行的 Codex 版本均为 `codex-cli 0.144.2`，命令配置均为 `codex_exec_ephemeral_workspace_write_v4`；`evaluated_commit / codex_version / command_profile` 的 `metadata_sources` 均为 `run_metadata`；
- `P01A/P01B` 平台路由、`L01/L02` proposed/active 因果门、`X01` 压力排序反转、`W01/W02` 零写操作边界均在本次全量运行中通过；
- `IR01–IR04` 是静态契约和人工验收规范，尚不是 Agent 自动评测结果；
- learned v2 使用结构化 `rule_id / status / scope / condition_tag_ids / action / evidence`，不再从规则摘要猜动作；
- `status: proposed` 不改变排序，只有显式迁移后的 `status: active` 才改变排序；CLI 的 `confirmed_by` 是自报字段，真实人工授权仍依赖宿主权限或 Git review；
- 视频回归同时证明三个完整标签命中候选被调整、`Shoe crease protector` 只有部分标签且未被误伤；
- `revoked / expired / superseded` 不参与打分，但规则级审计字段和报告中的停用规则区保留；
- 领星历史数据不会被外推成全市场需求或未来预测；
- 虎步只记为 collector，搬运后保留原始事实 provider；
- 公开仓库只包含 `_example` 虚构卖家与演示数据，平台写操作为零。

## 当前明确未完成

- 未接入真实卖家精灵、SIF、Sorftime 或领星账号；
- 未完成目标国家事实清单；
- 未用真实卖家验证画像排序优于通用排序；
- 未证明排序变化带来利润提升；
- 未实现经真实 T0 快照校准的 90 天预测；
- 真人复盘 cases 当前是人工验收规范，尚无独立自动 runner。

## 请重点挑战

1. “跨工具、带理由、经确认的卖家决策记忆层”是否是真需求，还是可被 ERP、表格或通用 Agent 快速替代？
2. 四个 Skill 的触发、读取顺序、写盘边界和交接是否存在漏洞、循环或隐含冲突？
3. learned v2 的“三条拒绝 + 两个独立 session”、结构化 tag 合取、作用域、失效、撤销和版本机制是否还有可绕过或误用的路径？
4. 缺数据、成本、合规、估算值和经验观点是否可能被错误转成精确分数或硬结论？
5. 领星 MCP/OpenAPI 与虎步 RPA 的权限隔离是否足够，是否还有间接写操作、数据越权或凭证泄露路径？
6. 26+4 cases 是否只在验证“按提示说对话”，而没有验证真正的推荐质量、因果改进和长期经营结果？
7. 当前演示是否存在夸大、循环论证或容易被从业者质疑的表述？

## 希望得到的评审格式

请引用具体文件和行号，并按下面结构输出：

1. 一句话 verdict：可交付 / 有条件可交付 / 不可交付；
2. P0 阻断项：不修不能给真实卖家使用；
3. P1 高价值改进：最影响可信度或推荐质量；
4. P2 工程完善项；
5. 对外主张审计：哪些能说、哪些必须收紧；
6. 最可能失败的三个场景及复现方法；
7. 下一轮最小验证实验，按信息增益排序；
8. 如果只能再改三处，请给出具体文件、位置和修改建议。

## 本地复现

```bash
python3 scripts/verify_delivery.py
python3 scripts/run_video_demo.py
python3 scripts/run_product_research_evals.py --mode static
```

Agent 模式会调用新的 Codex 进程并消耗模型额度，按需执行：

```bash
python3 scripts/run_product_research_evals.py --mode agent --case DS06
python3 scripts/run_product_research_evals.py --mode agent --case DS07
```

仓库中的正式 evidence 是两次固定运行的脱敏快照；重新运行会受当时模型与额度状态影响，不应把“本地可重跑”理解为保证产生字节级相同的新结果。
