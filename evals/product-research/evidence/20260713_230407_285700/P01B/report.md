# TikTok US 受控平台路由报告

## Canonical provenance

| mode | provider | provider_variant | source_role | read_operations | collectors_used | transformations_used | denied_operations |
|---|---|---|---|---|---|---|---|
| synthetic_demo | repository_fixture | eval_platform_comparison | direct_market_data | ["read references/demo-data/eval-platform-comparison.md"] | [] | [] | [] |

| collection_date | sample_boundary | candidate_ids | known_gaps | fixture_sha256 |
|---|---|---|---|---|
| 2026-07-11 | controlled_fixture_all_rows | ["platform-search","platform-visual"] | ["complete_unit_cost","live_market_validation"] | 7b9b17de664619a320a8f30bae03046ac0bd1615a8a3e0b9a901b21b3db3f72c |

| demand | competition | margin | capability_fit | risk |
|---:|---:|---:|---:|---:|
| 0.25 | 0.15 | 0.20 | 0.25 | 0.15 |

## 忠实执行段

- platform_adapter: tiktok
- ranking_basis: tiktok_visual_interaction_same_density_logistics
- platform_signal_labels: 视觉|互动|同款密度|物流
- conclusion_scope: hypothesis-only
- live_market_data_verified: false
- margin_status: unknown_missing_complete_cost
- total_score_status: not_computed_missing_margin
- 真实市场数据链路未验证

### 硬约束过滤

| candidate_id | controlled_initial_investment_cny | controlled_cash_cycle_days | hard_constraint_status |
|---|---:|---:|---|
| platform-visual | 5800 | 30 | pass_synthetic |
| platform-search | 6200 | 35 | pass_synthetic |

### 候选清单

| candidate_id | rank | demand | competition | margin | capability_fit | risk | total_score |
|---|---:|---:|---:|---:|---:|---:|---:|
| platform-visual | 1 | 4.5 | 3.5 | N/A | 5.0 | 4.5 | N/A |
| platform-search | 2 | 2.0 | 1.5 | N/A | 2.5 | 4.0 | N/A |

### 候选个性化归因表

| candidate_id | 为什么适合你 | 为什么不适合你 | 主要风险 | 下一步最小验证 |
|---|---|---|---|---|
| platform-visual | ["profile.capabilities.content_skill","profile.capabilities.supply_chain","profile.preferences.product_style"] | ["profile.preferences.competition_tolerance","profile.capabilities.team_size","profile.preferences.margin_floor_pct"] | ["complete_unit_cost","live_market_validation"] | ["complete_cost","tiktok_visual_interaction_logistics","compliance"] |
| platform-search | ["profile.constraints.logistics_modes","profile.capabilities.supply_chain","profile.preferences.risk_appetite"] | ["profile.capabilities.content_skill","profile.preferences.competition_tolerance"] | ["complete_unit_cost","live_market_validation"] | ["complete_cost","tiktok_visual_interaction_logistics","compliance"] |

### 被过滤品及原因

无。

### blocked_pending_data

无。

## 压力测试段

完整成本字段缺失，商业结论待核实。

### 需人工核实项

- 成本核实

### 成本纳入初筛后的排序对照

完整成本字段缺失，商业结论待核实。

## 下一步建议

按候选个性化归因表逐项复核
