# Amazon / TikTok 平台路由对照 fixture

> 合成评测数据，采集日期 2026-07-11。

| candidate_id | product | amazon_search | amazon_review_moat | amazon_cpc | tiktok_visual | tiktok_interaction | logistics | supply |
|---|---|---|---|---|---|---|---|---|
| platform-search | Replacement vacuum filter set | 稳定高搜索 | 头部平均评论 220 | 合成低 CPC 信号 | 视觉演示弱 | 互动低 | 轻小件 | MOQ 100，可稳定补货 |
| platform-visual | Color-changing shoe charm | 搜索量低且叫法分散 | 评论数据不足 | CPC 缺失 | 三秒内变化明显 | 多条内容高互动 | 轻小件 | MOQ 100，可定制颜色 |

期望：Amazon 路由优先 `platform-search` 并引用搜索/评论/CPC；TikTok 路由优先 `platform-visual` 并引用视觉/互动/物流。缺失字段必须保留为待核实。
