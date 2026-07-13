# Amazon / TikTok 平台路由对照 fixture

> 合成评测数据，采集日期 2026-07-11。本表只用于验证同一批候选在不同平台策略下的路由变化，不是真实市场或利润证据。
> `controlled_initial_investment_cny`、`controlled_cash_cycle_days` 和 `hard_constraint_status` 是受控实验的硬约束输入；本 fixture 故意不提供完整单位成本，因此 `margin` 与 `total_score` 必须保持 N/A。

| candidate_id | product | amazon_search | amazon_review_moat | amazon_cpc | tiktok_visual | tiktok_interaction | tiktok_same_density | logistics | supply | controlled_initial_investment_cny | controlled_cash_cycle_days | hard_constraint_status |
|---|---|---|---|---|---|---|---|---|---|---:|---:|---|
| platform-search | Replacement vacuum filter set | 稳定高搜索 | 头部平均评论 220，同款密度中等 | 合成低 CPC 信号 | 视觉演示弱 | 互动低 | 同款密度高 | 轻小件，合成轨迹可查 | MOQ 100，可稳定补货 | 6200 | 35 | pass_synthetic |
| platform-visual | Color-changing shoe charm | 搜索量低且叫法分散 | 头部平均评论 35，同款密度低 | 合成高 CPC 信号 | 三秒内变化明显 | 多条内容高互动 | 同款密度中等 | 轻小件，合成轨迹可查 | MOQ 100，可定制颜色 | 5800 | 30 | pass_synthetic |
