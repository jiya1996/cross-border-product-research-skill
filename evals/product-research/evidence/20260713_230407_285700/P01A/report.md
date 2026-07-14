# Amazon US 受控平台路由报告

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

- platform_adapter: amazon
- ranking_basis: amazon_search_review_cpc
- platform_signal_labels: 搜索|评论|CPC
- conclusion_scope: hypothesis-only
- live_market_data_verified: false
- margin_status: unknown_missing_complete_cost
- total_score_status: not_computed_missing_margin
- 真实市场数据链路未验证

| candidate_id | rank | demand | competition | margin | capability_fit | risk | total_score |
|---|---:|---:|---:|---:|---:|---:|---:|
| platform-search | 1 | 4.5 | 4.0 | N/A | 4.0 | 4.5 | N/A |
| platform-visual | 2 | 1.5 | 3.0 | N/A | 4.0 | 4.5 | N/A |

| candidate_id | 为什么适合你 | 为什么不适合你 | 主要风险 | 下一步最小验证 |
|---|---|---|---|---|
| platform-search | ["profile.constraints.capital_per_sku_max","profile.constraints.cash_cycle_tolerance_days","profile.capabilities.supply_chain","profile.preferences.review_moat_max"] | ["profile.capabilities.content_skill","profile.capabilities.ad_skill"] | ["complete_unit_cost","live_market_validation"] | ["complete_cost","amazon_search_review_cpc","compliance"] |
| platform-visual | ["profile.constraints.capital_per_sku_max","profile.constraints.cash_cycle_tolerance_days","profile.capabilities.supply_chain","profile.capabilities.content_skill","profile.preferences.product_style"] | ["profile.capabilities.ad_skill","profile.preferences.competition_tolerance"] | ["complete_unit_cost","live_market_validation"] | ["complete_cost","amazon_search_review_cpc","compliance"] |

## 压力测试段

完整成本字段缺失；商业结论待核实。

## 被过滤品

无。

## 待核实候选

无。

## 成本纳入初筛后的排序对照

完整成本字段缺失；商业结论待核实。

## 下一步建议

按候选个性化归因表逐项复核
