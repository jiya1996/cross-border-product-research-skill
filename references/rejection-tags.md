# 决策标签注册表

本文件供 `recommendation-review` 将用户反馈归一化，供 `profile-update` 聚合候选规则，也供候选数据以 `rule_tag_ids` 声明可执行条件。

## 使用纪律

- `tag_id` 是机器契约，创建后不改名、不复用；中文标签只用于展示。
- 决策文件同时写 `归类标签ID` 和规范 `归类标签`；聚合与规则执行只使用 ID。
- 用户使用 alias 时，保留原话，但写盘前必须映射为规范 ID/标签。
- 没有合适标签时可提议新 ID，但在人工确认并加入本表前，不得用于 learned 聚合或候选规则命中。
- 标签只用于聚合和候选规则生成，不得直接改写画像 A/B/C 区块。
- 同一条反馈可有多个 ID；`condition_tag_ids` 默认按合取解释。

## 规范标签

| tag_id | 规范标签 | aliases（写盘前归一） | 说明 | 常见涉及字段 |
|---|---|---|---|---|
| `ad_high_dependency` | 广告依赖度高 | 太吃广告, 投放依赖高 | 需要高预算投放才能起量 | `capabilities.ad_skill` |
| `cpc_over_budget` | CPC超预期 | CPC太高, 点击成本超预期 | 点击成本超出卖家承受能力 | `capabilities.ad_skill`, `preferences.margin_floor_pct` |
| `red_ocean_competition` | 红海竞争 | 红海, 竞争太卷 | 竞品过多或品牌集中 | `preferences.competition_tolerance` |
| `price_competition` | 价格竞争 | 价格战, 低价竞争, 价格卷 | 同质化低价导致利润承压 | `preferences.competition_tolerance`, `preferences.margin_floor_pct` |
| `review_moat_high` | 评论门槛高 | 评论壁垒高 | 头部竞品评论数超过可接受门槛 | `preferences.review_moat_max` |
| `same_product_density_high` | 同款过多 | 同款太多, 同款高, 同款极多, 同款中高 | 平台同款供给密度高 | `preferences.competition_tolerance` |
| `differentiation_space_low` | 差异化空间小 | 差异化不足, 差异化弱, 没有差异 | 产品太标准化，难以做出可感知差异 | `preferences.product_style` |
| `margin_below_floor` | 毛利不足 | 利润太低, 毛利低于红线 | 扣除已核实成本后低于毛利红线 | `preferences.margin_floor_pct` |
| `capital_occupancy_high` | 资金占用高 | 首批投入太高, MOQ太高 | 货款、MOQ、广告或库存占用过高 | `constraints.capital_per_sku_max` |
| `cash_cycle_too_long` | 回款周期长 | 回款太慢 | 资金回笼超过卖家承受周期 | `constraints.cash_cycle_tolerance_days` |
| `logistics_out_of_scope` | 物流超限 | 物流属性不适合, 太重, 太大 | 重量、体积、时效、易碎或运输属性不适合 | `constraints.logistics_modes` |
| `certification_barrier_high` | 认证门槛高 | 认证太麻烦, 资质不足 | 需要卖家不具备的认证、检测或资质 | `capabilities.compliance_experience` |
| `ip_infringement_risk` | 侵权风险 | 专利风险, 商标风险, 版权风险 | 商标、专利、版权或图片风险 | `constraints.forbidden_attributes` |
| `platform_fit_low` | 平台不适配 | 平台不合适 | 产品不适合目标平台流量或规则 | `constraints.target_marketplaces` |
| `platform_rule_unfavorable` | 平台规则不利 | 平台机制不利 | 发品额度、供货价、审核或考核机制不利 | `sop.md` |
| `content_unfilmable` | 素材不可拍 | 素材不好拍, 没有演示空间 | 缺少短视频演示或内容表达空间 | `capabilities.content_skill` |
| `content_memory_weak` | 素材记忆点弱 | 内容记忆点弱, 视频没记忆点 | 可拍但缺少可感知的记忆点 | `capabilities.content_skill` |
| `community_demand_invalid` | 社区需求不成立 | 社区反对明显, Reddit需求弱 | 社区反馈显示需求弱或反对明显 | `sop.md` |
| `supply_chain_unreachable` | 供应链够不着 | 供应链做不了, 采购不了 | 采购、MOQ、交期、定制或品控无法落地 | `capabilities.supply_chain` |
| `returns_high` | 退货率高 | 退货风险, 尺寸退货高 | 使用、尺寸、质量或预期差导致退货 | `sop.md` |
| `seasonality_risk` | 季节性风险 | 窗口太短, 节后滞销 | 销售窗口短或备货节奏难控 | `preferences.risk_appetite` |
| `packaging_fragile` | 易损/包装风险 | 易损, 包装风险, 易碎 | 破损、包装要求或售后赔付风险高 | `constraints.forbidden_attributes` |
| `personal_dislike` | 个人不喜欢 | 我不喜欢, 主观不看好 | 用户主观不认可且原因尚未结构化 | `sop.md` |

## 辅助状态标签

下列 ID 可记录 `watchlist` 或正向反馈，但不得作为拒绝规则证据：

| tag_id | 规范标签 | aliases | 说明 |
|---|---|---|---|
| `content_filmability_strong` | 素材可拍性强 | 视频效果好, 内容可拍 | 候选具备明确演示钩子 |
| `compliance_needs_verification` | 合规待核实 | 认证待核实, 安全待确认 | 只表示需补事实，不表示已违规 |
| `logistics_needs_verification` | 物流属性待核实 | 运输待核实 | 只表示需补运输属性 |

## 别名兼容要求

- `差异化不足` 和 `差异化弱` 必须统一写盘为 `differentiation_space_low` / `差异化空间小`。
- 旧决策文件可在读取时做 alias 映射用于展示和人工迁移；映射结果不得自动补齐 executable `condition_tag_ids`。未显式写 `归类标签ID` 的旧日志不能成为 active 规则证据。
- 新决策只写规范 ID。人类标签与 ID 冲突时，以 ID 为机器聚合依据，并报告数据质量错误。
