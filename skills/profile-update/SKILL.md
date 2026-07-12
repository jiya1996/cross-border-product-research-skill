---
name: profile-update
description: 画像自更新技能。从决策日志聚合平台、风险、能力和偏好模式，生成 learned 候选规则，等待用户确认后才参与推荐。
---

# profile-update

## 触发

- 用户要求更新画像、总结拒绝原因、复盘选品反馈。
- `sellers/{seller_id}/decisions/` 新增满 10 条。

## 必读内容

1. `sellers/{seller_id}/profile.yaml`
2. `sellers/{seller_id}/sop.md`
3. `sellers/{seller_id}/decisions/` 全部决策日志
4. `references/rejection-tags.md`
5. `references/knowledge-policy.md`

## 聚合逻辑

按以下维度聚合：

- 用户决定：accepted / rejected / watchlist
- 平台/来源：Amazon / SHEIN / TikTok / DTC / Reddit / 1688
- 拒绝标签：广告、物流、合规、平台、素材、供应链、毛利等
- 涉及画像字段：资金、毛利、广告能力、内容能力、供应链能力、禁做项

## 候选规则生成

只有满足以下条件才生成 learned 候选：

- 至少 3 条 evidence 指向不同决策文件。
- 模式有明确方向，如"多次拒绝素材不可拍的 TikTok 品"。
- 不与现有硬约束冲突。
- 规则写成可执行偏好，而不是泛泛总结。

示例：

```yaml
learned:
  - rule: "用户连续拒绝 TikTok 素材不可拍产品，推荐电商场景下素材可拍性低的品应降权"
    evidence:
      - decisions/2026-07-06_x.md
      - decisions/2026-07-07_y.md
      - decisions/2026-07-08_z.md
    confirmed: false
```

## 输出

先输出变更摘要，逐条请用户确认。用户确认前：

- 可以写入 `learned`，但必须 `confirmed: false`。
- 不得参与 product-research 打分。

用户逐条确认后：

- 将对应规则的 `confirmed` 改为 `true`。
- 写入 `confirmed_at: YYYY-MM-DD`。
- 保留原 `evidence` 列表，禁止压缩成一句总结。

## 边界

- 永远不直接修改 profile.yaml 的 A/B/C 区块。
- 不用经验观点覆盖用户画像。
- 不因单次反馈生成长期规则。
- `confirmed: false` 的规则不得参与推荐打分。
