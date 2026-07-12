---
name: profile-update
description: 画像自更新技能。从结构化决策日志聚合候选规则，达到跨会话证据门槛后写入 proposed，只有人工确认为 active 才参与后续推荐。
---

# profile-update

## 触发

- 用户要求更新画像、总结拒绝原因、复盘选品反馈。
- `sellers/{seller_id}/decisions/` 新增满 10 条。
- 用户要求确认、撤销、过期或取代某条 learned 规则。

## 必读内容

1. `sellers/{seller_id}/profile.yaml`
2. `sellers/{seller_id}/sop.md`
3. `sellers/{seller_id}/decisions/` 全部决策日志
4. `references/rejection-tags.md`
5. `references/knowledge-policy.md`
6. 每条 `source_type=report_feedback` 证据指向的来源报告

## 标签与证据归一

- 只按 `归类标签ID` 聚合，不按自由文本标签聚合。
- 先用 `references/rejection-tags.md` 将旧 alias 归一。例如 `差异化不足` 和 `差异化弱` 均映射为 `differentiation_space_low`。
- 聚合维度包括：用户决定、平台/来源、规范标签 ID、涉及画像字段、决策会话和事件日期。

## 候选规则生成门槛

只有同时满足以下条件才生成 learned 候选：

1. 至少 3 条 `用户决定: rejected` 证据，且分别指向 3 个不同 `决策ID` 和决策文件。
2. 证据覆盖至少 2 个独立会话。对 `report_feedback`，独立性 key 由 `来源报告 + 决策发生日期` 派生：报告或日期至少一项不同；仅改写手工 `决策会话ID` 不能把同一报告、同一天的批量拒绝拆成多个独立会话。
3. 所有证据必须共现规则所声明的全部 `condition_tag_ids`；不得用“标签 A 三次 + 标签 B 三次但从未共现”生成合取规则。
4. `report_feedback` 证据的 `source_report_id` 必须是仓库相对报告路径，文件存在，且来源报告候选表中包含同一 `candidate_id`。
5. 模式有明确可执行方向，不与现有硬约束冲突，`action.dimension` 属于已知评分维度，`action.delta` 是可复算数值。

门槛不足时只输出“观察到的模式 + 还缺什么证据”，不写入 learned。

## 历史复盘 fallback

- 历史上确实没有原报告时，接受 `source_type=historical_retrospective`，但必须保留 `来源报告: 无（历史复盘）`，不得伪造路径。
- 这类 evidence 的 `source_report_id` 保持 `null`，`session_id` 保存由显式会话或真实事件日期派生的独立性 key；显式会话 fallback 只适用于 `historical_retrospective`，不得用于拆分普通报告反馈，也不得声称已由原报告验证。
- 历史复盘确实无法确认事件日期、但有显式会话时，evidence 的 `decided_at` 可为 `null`；普通 `report_feedback` 的 `decided_at` 必须是 ISO 日期。
- 同一次复盘中回忆的多个候选共用一个 `决策会话ID`；不能通过为每个候选伪造 session 来跨过独立证据门槛。
- `决策发生日期: unknown` 的多条回忆，除非另有不同可定位文档证明，默认只算 1 个独立会话。

## learned v2 写入格式

`condition_tag_ids` 为合取；候选的 `rule_tag_ids` 必须同时包含全部 ID 才命中。

```yaml
learned:
  - rule_id: "learned_tiktok_same_density_diff_001"
    version: 1
    summary: "TikTok 同款密度高且差异化空间小的候选应降低竞争分"
    status: proposed
    scope:
      platforms: [tiktok]
      markets: [US]
      categories: []
    condition_tag_ids: [same_product_density_high, differentiation_space_low]
    action:
      dimension: competition
      delta: -1
    evidence:
      - decision_path: decisions/2026-07-06_mini-desk-vacuum.md
        decision_id: dec-example-20260706-tt002
        session_id: "report-date:reports/_example/2026-07-06_tiktok-pet-products.md|2026-07-06"
        source_report_id: reports/_example/2026-07-06_tiktok-pet-products.md
        candidate_id: tt-002
        decided_at: "2026-07-06"
      - decision_path: decisions/2026-07-06_silicone-cable-organizer.md
        decision_id: dec-example-20260706-tt004
        session_id: "report-date:reports/_example/2026-07-06_tiktok-desk-accessories.md|2026-07-06"
        source_report_id: reports/_example/2026-07-06_tiktok-desk-accessories.md
        candidate_id: tt-004
        decided_at: "2026-07-06"
      - decision_path: decisions/2026-07-06_foldable-phone-stand.md
        decision_id: dec-example-20260706-tt008
        session_id: "report-date:reports/_example/2026-07-06_tiktok-desk-accessories.md|2026-07-06"
        source_report_id: reports/_example/2026-07-06_tiktok-desk-accessories.md
        candidate_id: tt-008
        decided_at: "2026-07-06"
    created: "2026-07-12"
    confirmed_by: null
    confirmed_at: null
    revoked_by: null
    revoked_at: null
    revoke_reason: null
    expires_at: null
    supersedes: null
```

## 状态机

| status | 是否生效 | 写入规则 |
|---|---:|---|
| `proposed` | 否 | 证据达标后创建，等待人工确认 |
| `active` | 是 | 只能由用户明确确认，并写 `confirmed_by` / `confirmed_at` |
| `revoked` | 否 | 用户撤销后写 `revoked_by` / `revoked_at` / `revoke_reason` |
| `expired` | 否 | 超过 `expires_at` 后标记；不删除原证据 |
| `superseded` | 否 | 新规则以 `supersedes` 指向旧 `rule_id`，旧规则保留 |

`confirmed_by` / `revoked_by` 是调用者填写的自报审计字段，不承担身份认证。真实卖家环境必须由宿主权限、Git review 或独立操作者流程保证“用户明确确认”；演示脚本只能模拟状态迁移。

- **只有 `status: active` 可参与打分和排序。** 硬过滤仍只由 `constraints` 和 SOP 决定；`proposed` 是非活动状态，不得用“已提议”替代“已确认”。
- 规则内容改变时创建新的不可变 revision，增加 `version`，并让新规则的 `supersedes` 指向旧 `rule_id`。新 revision 仍为 `proposed` 时，旧规则继续保持原状态；只有人工确认新 revision 时，确认器才原子地将新规则改为 `active`、旧规则改为 `superseded`。不得原地改写旧证据，报告按反向引用显示 `superseded_by`。
- 证据可在多条规则间重叠，但每条规则都必须独立达到证据门槛并独立成为 `active`。同一候选的同一维度命中多条 active 规则时，先汇总全部 `delta`，最后只 clamp 一次到 0–5；结果不得依赖 YAML 顺序，报告必须公开所有 `rule_id`、aggregate delta、before 和 after。
- 报告必须分开列出“本次应用的 active 规则”和“未应用的非 active 规则”。后者展示 status、scope、时间和撤销/过期/取代原因，不得为了干净而删除。

## 边界

- 永远不直接修改 `profile.yaml` 的 A/B/C 区块。
- 不用经验观点覆盖用户画像。
- 不因单次反馈、单次批量拒绝或同一会话生成长期规则。
- 不自动将 `proposed` 变为 `active`，不自动恢复 `revoked / expired / superseded` 规则。
