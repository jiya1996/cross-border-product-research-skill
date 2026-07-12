# TikTok 宠物小件样例选品报告

> 这是虚构 demo 报告, 用于演示流程和文件结构。不得作为真实采购或上架建议。

## 任务背景和平台适配器

- seller_id: `_example`
- 平台: TikTok / 推荐电商
- 读取策略: `references/platforms/tiktok.md`
- 评分标尺: `references/checklists/scoring-rubric.md`

## 数据来源和缺口

- 来源: 虚构候选品列表 + 虚构用户画像。
- 缺口: 真实互动数据、采购价、物流报价、认证要求均为需人工核实。

## 候选清单

| 品名 | 类目 | demand | competition | margin | capability_fit | risk | 总分 |
|---|---|---:|---:|---:|---:|---:|---:|
| LED pet collar | 宠物夜间出行 | 4 | 3 | 3 | 4 | 2 | 3.3 |
| Mini desk vacuum | 桌面清洁 | 3 | 1 | 3 | 4 | 3 | 2.8 |
| Glass storage jar | 厨房收纳 | 2 | 2 | 2 | 2 | 1 | 1.8 |

## 为什么适合你

- `profile.capabilities.content_skill=4`: 适合测试能拍前后对比、情绪价值强的短视频产品。
- `profile.constraints.capital_per_sku_max=30000`: 三个候选都应先以小批量样品验证。

## 为什么不适合你

- `profile.constraints.forbidden_attributes` 包含大件易碎, 因此 glass storage jar 应过滤或强降权。
- `profile.preferences.competition_tolerance=medium`, mini desk vacuum 同款过多, 需要明显差异化才值得测试。

## 被过滤品及原因

- Glass storage jar: 易碎、包装风险高、退货风险高。

## 需人工核实项

- LED pet collar 是否涉及电池运输、宠物安全责任、FCC/电商平台限制。
- 三个候选的真实 1688 采购价、MOQ、头程和尾程费用。
- TikTok 近 30 天视频互动、评论痛点和同款投放密度。

## 下一步建议

1. 只保留 LED pet collar 进入样品核价。
2. 对 mini desk vacuum 只找有明显差异化结构的供应商。
3. 将 glass storage jar 记录为拒绝样本, 用于后续画像更新。
