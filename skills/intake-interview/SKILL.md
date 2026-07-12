---
name: intake-interview
description: 新卖家访谈建档技能。用于从文档/文字、对话或已售产品列表中生成卖家 profile.yaml 与 sop.md，并确认平台偏好、供应链、内容能力和禁做边界。
---

# intake-interview

## 触发

- `sellers/{seller_id}/profile.yaml` 或 `sellers/{seller_id}/sop.md` 不存在。
- 用户说"新建卖家档案"、"帮我建画像"、"这是我的选品标准"。
- 用户提供已售产品列表，希望反推选品策略。
- 用户希望复盘最近一次真实选品，把当时的候选、接受/拒绝理由与后来结果结构化留存。

## 必读知识

执行前读取：

- `references/knowledge-policy.md`
- `references/schemas/profile-template.yaml`
- `references/schemas/sop-template.md`
- `references/questions/intake-platform-fit.md`
- `references/questions/recent-selection-retrospective.md`
- `references/checklists/product-selection.md`

## 四个入口

### 入口 A：文档/文字导入

1. 从用户材料中抽取 profile 槽位和 SOP 规则。
2. 每个抽取值必须标记来源：`document` 或 `inferred`。
3. `inferred` 值不得直接写盘，必须进入缺口访谈确认。
4. 只追问三类问题：必填槽为空、推断值待确认、文档内部矛盾。
5. 规则类语句写入 `sop.md` 候选区，保留原文出处。

### 入口 B：对话访谈

按组提问，不一次性倾倒问题：

1. 平台和站点：目标平台、目标国家、是否偏 Amazon / SHEIN / TikTok / DTC。
2. 硬约束：资金上限、回款周期、禁做类目、禁做属性、物流方式。
3. 能力：供应链、广告、内容、合规、语言、团队。
4. 偏好：风险偏好、竞争容忍、产品风格、毛利红线、评论门槛。
5. SOP：让用户口述"平时怎么判断一个品能不能做"。

### 入口 C：已售产品反推画像

1. 将已售产品按平台、站点、类目、价格带、物流属性、合规属性、差异化方式归类。
2. 总结可观察模式，但全部标记为 `inferred`。
3. 追问：哪些品成功、哪些失败、是否主动策略、未来是否继续做类似品。
4. 未经用户确认，不得写入正式画像 A/B/C 区块。

### 入口 D：最近一次真实选品决策回放

1. 只选一次时间边界清楚的真实选品事件，按 `references/questions/recent-selection-retrospective.md` 从决策现场、当时数据、逐候选理由到后来结果顺序回放。
2. 强制把“当时决定”与“后来结果”分开。后来亏损不改写当时的 `accepted`，后来走红也不改写当时的 `rejected`。
3. 对所有依据标记 `documented`、`recalled` 或 `mixed`。`recalled` 数字只保留为用户原话和待核实上下文，不得进入事实数字、硬过滤、精确毛利或评分。
4. 每个候选品单独保留当时的 `accepted / rejected / watchlist` 与用户原话。用户确认后，转 `recommendation-review`，以 `来源类型: historical_retrospective` 写入一品一文件的决策日志。
5. 从回放中总结的画像值或 SOP 规则仍属于 `inferred`。必须逐条请用户确认；未确认的规则只能进入 `sop.md` 候选区，不得进入 profile A/B/C 区块。

## 写盘前确认

展示确认表：

| 槽位 | 填入值 | 来源 | 原文/证据 | 是否待确认 |
|---|---|---|---|---|

用户确认后，才写入：

- `sellers/{seller_id}/profile.yaml`
- `sellers/{seller_id}/sop.md`

写入时必须复制并填充 `references/schemas/` 中的模板结构，不得自由创建新顶层字段。无法确认的推断规则写入 `sop.md` 候选区，不进入 profile A/B/C 区块。

入口 D 另外展示“决策日志确认表”。只有用户确认了候选品、当时决定、当时原话、依据状态与后来结果的分界后，才能调用 `recommendation-review` 写入 `sellers/{seller_id}/decisions/`。`intake-interview` 不得绕过该 Skill 自由发明决策格式，也不得因为一次历史复盘直接生成 `status: active` 的 learned 规则。

## 边界

- 不编造画像字段。
- 不在无画像状态下输出选品推荐。
- 不把经验观点当作事实数字。
- 不把事后回忆的数字当作当时可核验事实。
- 不用后来结果篡改当时决定，也不用单次结果直接生成长期规则。
- 冲突优先级：用户当场所述 > 文档所写 > 模型推断；同源之间新值覆盖旧值。
