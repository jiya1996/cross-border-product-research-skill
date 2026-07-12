# 新卖家平台适配访谈问题库

本问题库供 `intake-interview` 使用。问题应按用户回答动态裁剪，不要求一次性全部询问。

## 必问问题

| 问题 | 写入画像字段 | 用途 |
|---|---|---|
| 你主要想做哪些平台或站点？Amazon、SHEIN、TikTok、独立站、Shopee，还是其他？ | `constraints.target_marketplaces` | 确定平台策略和数据源 |
| 单个 SKU 首批最多能投入多少钱？请把货款、物流、包装、广告都算进去。 | `constraints.capital_per_sku_max` | 资金一票否决 |
| 你最低能接受多少毛利率？低于多少一定不做？ | `preferences.margin_floor_pct` | 毛利红线 |
| 哪些类目或属性你明确不做？如带电、液体、大件、儿童、食品接触、医疗、美妆等。 | `constraints.forbidden_categories`, `constraints.forbidden_attributes` | 禁做项 |
| 你能接受哪些物流方式？FBA、FBM、海外仓、全托管、Dropshipping、1688 代发？ | `constraints.logistics_modes` | 物流可行性 |
| 你的供应链资源是什么？无固定供应链、1688 采购、有工厂资源、自有工厂？ | `capabilities.supply_chain` | 供应链能力 |
| 广告投放能力 1-5 分？内容素材能力 1-5 分？ | `capabilities.ad_skill`, `capabilities.content_skill` | 平台能力匹配 |
| 是否处理过认证或合规？如 CE、FDA、FCC、CPC、EPR、GPSR 等。 | `capabilities.compliance_experience` | 合规能力 |
| 你更偏好哪类产品？稳健常青、功能改良、轻创新、趋势品、低价走量、情绪价值、礼品类？ | `preferences.product_style` | 软排序 |
| 过去哪些产品你会一眼拒绝？为什么？ | `sop.md`, 决策标签候选 | 拒绝样本 |

## 已售产品反推入口

当用户提供正在销售或过去销售的产品列表时：

1. 先按平台、站点、类目、价格带、物流属性、合规属性、差异化方式归类。
2. 总结可观察模式，但全部标记为 `inferred`。
3. 只追问关键确认：这些品是否主动策略、哪些成功、哪些失败、未来是否继续做类似品。
4. 未经用户确认，不得写入正式画像 A/B/C 区块。

## 平台专项追问

| 平台 | 追问 |
|---|---|
| Amazon | 是否能接受广告起量？评论门槛最高接受多少？是否熟悉 FBA 和类目合规？ |
| SHEIN | 是否接受全托管供货模式？是否能快速找 1688 同款？是否避开证书/敏感/易损品？ |
| TikTok | 是否能拍短视频素材？是否接受测爆品？物流时效最长能接受多久？ |
| DTC / SEO | 是否有内容/SEO 能力？是否能持续做产品页、博客、测评和邮件营销？ |
| Reddit | 是否愿意先做社区需求验证？能否接受用户直接否定产品想法？ |
| 1688 | 是否有产业带资源？能否小批量打样？是否需要私模或包装定制？ |
