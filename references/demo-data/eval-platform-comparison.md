# Amazon / TikTok 平台路由对照 fixture

> 合成评测数据，采集日期 2026-07-11。本表只用于验证同一批候选在不同平台策略下的路由变化，不是真实市场或利润证据。
> `controlled_initial_investment_cny`、`controlled_cash_cycle_days` 和 `hard_constraint_status` 是受控实验的硬约束输入；本 fixture 故意不提供完整单位成本，因此 `margin` 与 `total_score` 必须保持 N/A。
> `controlled_ranking_basis.amazon=amazon_search_review_cpc`；`controlled_ranking_basis.tiktok=tiktok_visual_interaction_same_density_logistics`。平台专属 rank 与四维分是合成路由 oracle，评测结果必须逐值一致。

| candidate_id | product | amazon_search | amazon_review_moat | amazon_cpc | tiktok_visual | tiktok_interaction | tiktok_same_density | logistics | supply | controlled_initial_investment_cny | controlled_cash_cycle_days | hard_constraint_status | amazon_rank | amazon_demand_score | amazon_competition_score | amazon_capability_fit_score | amazon_risk_score | tiktok_rank | tiktok_demand_score | tiktok_competition_score | tiktok_capability_fit_score | tiktok_risk_score |
|---|---|---|---|---|---|---|---|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| platform-search | Replacement vacuum filter set | 稳定高搜索 | 头部平均评论 220，同款密度中等 | 合成低 CPC 信号 | 视觉演示弱 | 互动低 | 同款密度高 | 轻小件，合成轨迹可查 | MOQ 100，可稳定补货 | 6200 | 35 | pass_synthetic | 1 | 4.5 | 4.0 | 4.0 | 4.5 | 2 | 2.0 | 1.5 | 2.5 | 4.0 |
| platform-visual | Color-changing shoe charm | 搜索量低且叫法分散 | 头部平均评论 35，同款密度低 | 合成高 CPC 信号 | 三秒内变化明显 | 多条内容高互动 | 同款密度中等 | 轻小件，合成轨迹可查 | MOQ 100，可定制颜色 | 5800 | 30 | pass_synthetic | 2 | 1.5 | 3.0 | 4.0 | 4.5 | 1 | 4.5 | 3.5 | 5.0 | 4.5 |
