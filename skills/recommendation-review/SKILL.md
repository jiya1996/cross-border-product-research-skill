---
name: recommendation-review
description: 推荐反馈记录技能。把用户对候选品的接受、拒绝或观察反馈结构化写入 decisions/，并按平台、能力、风险和画像字段归类。
---

# recommendation-review

## 触发

- 用户对报告或候选品说"这个可以"、"这个不行"、"先观察"。
- 用户给出拒绝理由，如太吃广告、同款太多、素材不好拍、供应链够不着。
- `intake-interview` 完成一次真实选品决策回放，用户已确认当时的候选、决定、原话与后来结果分界。

## 必读知识

- `references/rejection-tags.md`
- 对应报告文件（`source_type=historical_retrospective` 且当时无报告时可为无，不伪造路径）
- `sellers/{seller_id}/profile.yaml`
- `sellers/{seller_id}/sop.md`
- 若为历史复盘，完整读取本次已经用户确认的复盘摘要

## 行为

1. 识别被评价的候选品、来源类型、来源报告和用户决定。默认 `source_type=report_feedback`；最近一次选品回放使用 `source_type=historical_retrospective`。
2. 保存用户原话，不要改写成模型语言。
3. 从 `references/rejection-tags.md` 选择标签；没有合适标签时新增，但保留原话证据。
4. 标注涉及画像字段，如资金、毛利、广告能力、内容能力、供应链、禁做项。
5. 一个被评价的品写一个决策文件。

### 历史复盘的时点纪律

- `用户决定` 与 `用户原话` 始终表示**当时**的决定和当时原话，不是今天看到结果后的新判断。
- 后来是否上架、盈利、亏损或停售只写在“后来结果”字段，不得反向改写当时的 `accepted / rejected / watchlist`。
- 当时依据与后来结果依据分别标记 `documented`、`recalled`、`mixed` 或 `unknown`，不得用现在的报表伪装成当时已知信息。
- 任何 `recalled` 数字只能保留在用户原话、当时依据摘要、后来结果原话或备注中，同时标记“需人工核实”。它不得进入候选事实、硬过滤、精确毛利、评分或用来证明市场机会。
- 后续获得原始报表时，应另走 `verified_import` 与事实数据溯源流程；不覆盖或删除原复盘记录。

## 决策文件格式

文件路径必须为 `sellers/{seller_id}/decisions/YYYY-MM-DD_product-slug.md`。`product-slug` 用英文小写、数字和连字符；没有英文名时用平台或类目加序号。

```markdown
# YYYY-MM-DD | product-slug
- 来源类型: report_feedback
- 来源报告: reports/{seller_id}/YYYY-MM-DD_主题.md
- 平台/来源: Amazon / SHEIN / TikTok / DTC / Reddit / 1688 / unknown
- 用户决定: accepted / rejected / watchlist
- 用户原话: "..."
- 归类标签: [...]
- 涉及画像字段: ...
- 备注: ...
```

`historical_retrospective` 格式：

```markdown
# YYYY-MM-DD | product-slug
- 来源类型: historical_retrospective
- 来源报告: 无（历史复盘） / reports/{seller_id}/...
- 复盘事件日期: YYYY-MM-DD / unknown
- 平台/来源: Amazon / SHEIN / TikTok / DTC / Reddit / 1688 / unknown
- 用户决定: accepted / rejected / watchlist
- 用户原话: "当时的原话"
- 当时依据状态: documented / recalled / mixed / unknown
- 当时使用的数据/工具: [...]
- 当时依据摘要: ...
- 证据定位: [安全本地别名或相对路径] / []
- 归类标签: [...]
- 涉及画像字段: ...
- 后来结果状态: not_launched / launched_pending / profitable / unprofitable / stopped / unknown
- 后来结果截至: YYYY-MM-DD / unknown
- 后来结果依据状态: documented / recalled / mixed / unknown
- 后来结果原话: "..."
- 备注: recalled 数字需人工核实 / ...
```

## 边界

- 决策日志只写入对应卖家的 `sellers/{seller_id}/decisions/`。
- 公开仓库中不得提交真实卖家的决策日志；只允许提交 `_example` 虚构样例。
- 反馈记录不得跨卖家复用。
- 不直接修改画像 A/B/C 区块。
- 不把一次拒绝直接升级为长期规则，必须交给 `profile-update` 聚合。
- 不用后来结果篡改当时决策，不把事后解释冒充当时原话。
- 不将 `recalled` 数字传入 `product-research` 的 facts/evidence 或精确评分。
