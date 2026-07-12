# TikTok 桌面配件样例选品报告

> 这是虚构 demo 报告，用于演示跨会话决策证据和来源候选一致性。不得作为真实采购或上架建议。

## 任务背景和平台适配器

- seller_id: `_example`
- 市场: US
- source_report_id: `reports/_example/2026-07-06_tiktok-desk-accessories.md`
- decision_session_id: `session-example-20260706-desk-b`
- 平台: TikTok / 推荐电商
- 读取策略: `references/platforms/tiktok.md`
- 评分标尺: `references/checklists/scoring-rubric.md`

## 数据来源和缺口

- 来源: `references/demo-data/tiktok-candidates.md` 中的虚构候选和虚构卖家画像。
- 缺口: 真实需求、竞争、采购、物流、退货和合规数据均需人工核实。

## 候选清单

| candidate_id | 品名 | 类目 | demand | competition | margin | capability_fit | risk | 总分 |
|---|---|---|---:|---:|---:|---:|---:|---:|
| tt-004 | Silicone cable organizer | 桌面收纳 | 3 | 2 | 4 | 3 | 3 | 3.0 |
| tt-008 | Foldable phone stand | 手机配件 | 3 | 1 | 4 | 3 | 3 | 2.8 |

## 为什么适合你

- `profile.capabilities.content_skill=4`：两个候选都可演示桌面整理或支架使用场景。
- 体积和合成 MOQ 适合小样验证；真实投入仍需核价。

## 为什么不适合你

- `profile.preferences.competition_tolerance=medium`：两个候选的同款密度高，且虚构数据未显示可感知差异化。
- 未核实广告、退货和完整履约成本，不能声称真实毛利达标。

## 被过滤品及原因

- 无硬过滤候选；两者都因竞争与差异化风险不进入本次样品测试。

## 需人工核实项

- TikTok 目标市场同款供给密度、价格带和近期视频表现。
- 两个候选的真实采购价、MOQ、运费、平台费和退货率。

## 下一步建议

1. 只有在找到可感知结构/内容差异后才重新评估。
2. 将本次两个拒绝与另一独立选品会话的同类拒绝交给 `profile-update` 聚合，不因本会话单独生成长期规则。
