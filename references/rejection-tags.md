# 拒绝原因标签集

本文件供 `recommendation-review` 归类用户反馈，供 `profile-update` 聚合候选画像规则。

## 使用纪律

- 用户拒绝推荐时，优先从本文件选择标签。
- 可新增标签，但必须保留用户原话证据。
- 标签只能用于聚合和候选规则生成，不得直接改写画像 A/B/C 区块。
- 同一条反馈可以有多个标签。

## 初始标签

| 标签 | 说明 | 常见涉及字段 |
|---|---|---|
| 广告依赖度高 | 需要高预算投放或高 CPC 才能起量 | `capabilities.ad_skill` |
| CPC超预期 | 关键词点击成本超出卖家承受能力 | `capabilities.ad_skill`, `preferences.margin_floor_pct` |
| 红海竞争 | 竞品过多、品牌集中或价格战严重 | `preferences.competition_tolerance` |
| 评论门槛高 | 头部竞品评论数超过卖家可接受门槛 | `preferences.review_moat_max` |
| 毛利不足 | 扣除成本后低于毛利红线 | `preferences.margin_floor_pct` |
| 资金占用高 | 首批货、MOQ、广告或库存占用过高 | `constraints.capital_per_sku_max` |
| 回款周期长 | 资金回笼超过卖家承受周期 | `constraints.cash_cycle_tolerance_days` |
| 物流超限 | 重量、体积、时效、易碎或运输属性不适合 | `constraints.logistics_modes` |
| 认证门槛高 | 需要卖家不具备的认证、检测或资质 | `capabilities.compliance_experience` |
| 侵权风险 | 商标、专利、版权、图片或宗教敏感风险 | `constraints.forbidden_attributes` |
| 平台不适配 | 产品不适合目标平台的流量或规则 | `constraints.target_marketplaces` |
| 平台规则不利 | 发品额度、供货价、审核、考核等平台机制不利 | `sop.md` |
| 素材不可拍 | 缺少短视频演示、视觉冲击或内容表达空间 | `capabilities.content_skill` |
| 同款过多 | 平台上同款供给太多，缺少稀缺性 | `preferences.competition_tolerance` |
| 社区需求不成立 | Reddit/社区反馈显示用户需求弱或反对明显 | `sop.md` |
| 供应链够不着 | 采购、MOQ、交期、定制或品控无法落地 | `capabilities.supply_chain` |
| 差异化空间小 | 产品太标准化，难以做出可感知差异 | `preferences.product_style` |
| 退货率高 | 使用复杂、尺寸适配、质量或预期不符导致退货风险 | `sop.md` |
| 季节性风险 | 窗口短、节后滞销或备货节奏难控制 | `preferences.risk_appetite` |
| 易损/包装风险 | 破损、包装要求或售后赔付风险高 | `constraints.forbidden_attributes` |
| 个人不喜欢 | 用户主观不认可，但原因尚未结构化 | `sop.md` |
