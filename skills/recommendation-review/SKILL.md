---
name: recommendation-review
description: 推荐反馈记录技能。把用户对候选品的接受、拒绝或观察反馈写成带稳定 ID、决策会话、来源报告和规范标签 ID 的可追溯决策日志。
---

# recommendation-review

## 触发

- 用户对报告或候选品说“这个可以”、“这个不行”、“先观察”。
- 用户给出拒绝理由，如太吃广告、同款太多、素材不好拍、供应链够不着。
- `intake-interview` 完成一次真实选品决策回放，用户已确认当时候选、决定、原话和后来结果的分界。

## 必读知识

- `references/rejection-tags.md`
- `sellers/{seller_id}/profile.yaml`
- `sellers/{seller_id}/sop.md`
- 来源报告；仅 `source_type=historical_retrospective` 且历史上确实无报告时允许“无（历史复盘）”
- 若为历史复盘，完整读取本次已经用户确认的复盘摘要

## 稳定 ID 与会话纪律

1. `决策ID` 在卖家目录内唯一，写盘后不复用。建议格式：`dec-{seller_id}-{YYYYMMDD}-{candidate_id}`；冲突时追加序号。
2. `候选ID` 必须复用来源报告中的 `candidate_id`，不得根据品名重新发明。
3. `决策会话ID` 表示一次真实选品批次/会议/复盘事件。同一批候选的多个决策必须共用同一 session ID，不能为跨过 learned 证据门槛而拆分。
4. `决策发生日期` 是当时做决定的日期，不是今天补录的日期；无法确认时写 `unknown`。

## 行为

1. 识别候选、决策会话、来源类型、来源报告、平台和用户决定。默认 `source_type=report_feedback`；最近一次选品回放使用 `source_type=historical_retrospective`。
2. 保存用户原话，不改写成模型语言。
3. 用 `references/rejection-tags.md` 将用户用词归一为稳定 `归类标签ID` 和规范中文 `归类标签`。例如“差异化不足”写盘为 `differentiation_space_low` / `差异化空间小`。
4. 标注涉及画像字段，如资金、毛利、广告能力、内容能力、供应链和禁做项。
5. 一个被评价候选写一个决策文件。

## 来源报告一致性门禁

对 `source_type=report_feedback`，写盘前必须逐项验证：

- `来源报告` 是仓库相对路径，且文件存在；
- 报告候选表明确包含同一 `候选ID`；
- 报告中候选名称与用户评价对象一致。

任一项不一致时停止写盘，要求选择正确报告/候选；不得把“差不多的品”当成同一个候选。

## 决策文件格式

文件路径：`sellers/{seller_id}/decisions/YYYY-MM-DD_product-slug.md`。`product-slug` 用英文小写、数字和连字符；没有英文名时使用平台或类目加序号。

```markdown
# YYYY-MM-DD | product-slug

- 决策ID: dec-seller-YYYYMMDD-candidate
- 候选ID: candidate-id-from-report
- 决策会话ID: session-seller-YYYYMMDD-a
- 决策发生日期: YYYY-MM-DD
- 来源类型: report_feedback
- 来源报告: reports/{seller_id}/YYYY-MM-DD_主题.md
- 平台/来源: Amazon / SHEIN / TikTok / DTC / Reddit / 1688 / unknown
- 用户决定: accepted / rejected / watchlist
- 用户原话: "..."
- 归类标签ID: [same_product_density_high, differentiation_space_low]
- 归类标签: [同款过多, 差异化空间小]
- 涉及画像字段: ...
- 备注: ...
```

## 历史复盘 fallback 格式

- 历史上确实没有原报告时，使用 `来源报告: 无（历史复盘）`，不伪造路径。
- 本次回忆中的多个候选共用一个 `决策会话ID`。
- 若原平台没有稳定候选 ID，可生成 `historical-{platform}-{slug}-{ordinal}`，但必须标注它是本地复盘 ID，不冒充平台 ID。

```markdown
# YYYY-MM-DD | product-slug

- 决策ID: dec-seller-YYYYMMDD-candidate
- 候选ID: historical-tiktok-product-01
- 决策会话ID: session-seller-retrospective-001
- 决策发生日期: YYYY-MM-DD / unknown
- 来源类型: historical_retrospective
- 来源报告: 无（历史复盘）
- 平台/来源: Amazon / SHEIN / TikTok / DTC / Reddit / 1688 / unknown
- 用户决定: accepted / rejected / watchlist
- 用户原话: "当时的原话"
- 当时依据状态: documented / recalled / mixed / unknown
- 当时使用的数据/工具: [...]
- 当时依据摘要: ...
- 证据定位: [安全本地别名或相对路径] / []
- 归类标签ID: [...]
- 归类标签: [...]
- 涉及画像字段: ...
- 后来结果状态: not_launched / launched_pending / profitable / unprofitable / stopped / unknown
- 后来结果截至: YYYY-MM-DD / unknown
- 后来结果依据状态: documented / recalled / mixed / unknown
- 后来结果原话: "..."
- 备注: recalled 数字需人工核实 / ...
```

### 历史复盘的时点纪律

- `用户决定` 与 `用户原话` 始终表示**当时**的决定和原话，不是今天看到结果后的新判断。
- 后来是否上架、盈利、亏损或停售只写在“后来结果”字段，不得反向改写当时决定。
- 当时依据与后来结果依据分别标记 `documented / recalled / mixed / unknown`，不得用现在的报表伪装成当时已知信息。
- 任何 `recalled` 数字只能保留在原话、摘要、后来结果或备注中，并标记“需人工核实”；不得进入候选事实、硬过滤、精确毛利或评分。
- 后续获得原始报表时，另走 `verified_import` 与事实数据溯源流程，不覆盖或删除原复盘记录。

## 边界

- 决策日志只写入对应卖家的 `sellers/{seller_id}/decisions/`。
- 公开仓库不得提交真实卖家决策日志；只允许 `_example` 虚构样例。
- 反馈记录不得跨卖家复用。
- 不直接修改画像 A/B/C 区块。
- 不把一次拒绝或同一决策会话的批量拒绝直接升级为长期规则。
- 不用后来结果篡改当时决策，不把事后解释冒充当时原话。
