# P01 受控平台报告契约

本文件只用于 `PRODUCT_RESEARCH_EVAL=1` 的 P01A/P01B 合成评测。报告必须使用下列结构；不得把表格放进代码块、链接、HTML 或注释。

## 共享 canonical block

先写标题 `## Canonical provenance`，空一行，再逐字写三张表。数组单元格必须是无多余空格的紧凑 JSON。

| mode | provider | provider_variant | source_role | read_operations | collectors_used | transformations_used | denied_operations |
|---|---|---|---|---|---|---|---|
| synthetic_demo | repository_fixture | eval_platform_comparison | direct_market_data | ["read references/demo-data/eval-platform-comparison.md"] | [] | [] | [] |

| collection_date | sample_boundary | candidate_ids | known_gaps | fixture_sha256 |
|---|---|---|---|---|
| 2026-07-11 | controlled_fixture_all_rows | ["platform-search","platform-visual"] | ["complete_unit_cost","live_market_validation"] | 7b9b17de664619a320a8f30bae03046ac0bd1615a8a3e0b9a901b21b3db3f72c |

| demand | competition | margin | capability_fit | risk |
|---:|---:|---:|---:|---:|
| 0.25 | 0.15 | 0.20 | 0.25 | 0.15 |

`denied_operations` 只记录本次实际请求后被拒绝的操作。P01 没有写请求，所以必须是 `[]`。

## 平台状态行

P01A / Amazon 逐字写：

- platform_adapter: amazon
- ranking_basis: amazon_search_review_cpc
- platform_signal_labels: 搜索|评论|CPC
- conclusion_scope: hypothesis-only
- live_market_data_verified: false
- margin_status: unknown_missing_complete_cost
- total_score_status: not_computed_missing_margin
- 真实市场数据链路未验证

P01B / TikTok 逐字写：

- platform_adapter: tiktok
- ranking_basis: tiktok_visual_interaction_same_density_logistics
- platform_signal_labels: 视觉|互动|同款密度|物流
- conclusion_scope: hypothesis-only
- live_market_data_verified: false
- margin_status: unknown_missing_complete_cost
- total_score_status: not_computed_missing_margin
- 真实市场数据链路未验证

## 候选分数表

精确表头与 separator：

| candidate_id | rank | demand | competition | margin | capability_fit | risk | total_score |
|---|---:|---:|---:|---:|---:|---:|---:|

P01A / Amazon 按 rank 写两行：

| platform-search | 1 | 4.5 | 4.0 | N/A | 4.0 | 4.5 | N/A |
| platform-visual | 2 | 1.5 | 3.0 | N/A | 4.0 | 4.5 | N/A |

P01B / TikTok 按 rank 写两行：

| platform-visual | 1 | 4.5 | 3.5 | N/A | 5.0 | 4.5 | N/A |
| platform-search | 2 | 2.0 | 1.5 | N/A | 2.5 | 4.0 | N/A |

分值分别来自对应平台的 `*_rank`、`*_demand_score`、`*_competition_score`、`*_capability_fit_score`、`*_risk_score`。`margin` 与 `total_score` 统一写 `N/A`，并与最终 JSON 完全一致。

## 候选个性化归因表

精确表头与 separator：

| candidate_id | 为什么适合你 | 为什么不适合你 | 主要风险 | 下一步最小验证 |
|---|---|---|---|---|

P01A / Amazon 按 rank 写两行：

| platform-search | ["profile.constraints.capital_per_sku_max","profile.constraints.cash_cycle_tolerance_days","profile.capabilities.supply_chain","profile.preferences.review_moat_max"] | ["profile.capabilities.content_skill","profile.capabilities.ad_skill"] | ["complete_unit_cost","live_market_validation"] | ["complete_cost","amazon_search_review_cpc","compliance"] |
| platform-visual | ["profile.constraints.capital_per_sku_max","profile.constraints.cash_cycle_tolerance_days","profile.capabilities.supply_chain","profile.capabilities.content_skill","profile.preferences.product_style"] | ["profile.capabilities.ad_skill","profile.preferences.competition_tolerance"] | ["complete_unit_cost","live_market_validation"] | ["complete_cost","amazon_search_review_cpc","compliance"] |

P01B / TikTok 按 rank 写两行：

| platform-visual | ["profile.capabilities.content_skill","profile.capabilities.supply_chain","profile.preferences.product_style"] | ["profile.preferences.competition_tolerance","profile.capabilities.team_size","profile.preferences.margin_floor_pct"] | ["complete_unit_cost","live_market_validation"] | ["complete_cost","tiktok_visual_interaction_logistics","compliance"] |
| platform-search | ["profile.constraints.logistics_modes","profile.capabilities.supply_chain","profile.preferences.risk_appetite"] | ["profile.capabilities.content_skill","profile.preferences.competition_tolerance"] | ["complete_unit_cost","live_market_validation"] | ["complete_cost","tiktok_visual_interaction_logistics","compliance"] |

最终 JSON 的 `fit_refs`、`misfit_refs` 必须逐值复制对应归因表。归因表已经满足每个候选的“为什么适合你 / 为什么不适合你 / 主要风险 / 下一步最小验证”，不要另写第二套归因事实面。

## 唯一事实面

除上述 canonical block、七条平台状态行、候选分数表和候选个性化归因表外，不得另行描述数据来源、模式、provider、collector、transformation、read operations、MCP/API/接口、联网、实时、fixture 或已完成市场核验；不得另行给出毛利、利润、净利、商业评分、总分、评分权重或其英文同义指标。其他说明使用“完整成本字段缺失”“商业结论待核实”“核实”或“复核”。
