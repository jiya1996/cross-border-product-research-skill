# ops-only Amazon US 候选评估

## 任务、平台与运行模式

- seller_id：`eval-content`
- 候选：`ops-only`（Unvalidated desk accessory）
- 需求平台：Amazon US
- 运行模式：`synthetic_demo`，仅离线读取 `references/demo-data/eval-tool-role-boundaries.json`
- 结论：当前不能推荐。候选进入 `blocked_pending_data`，不得评分或进入 Top 推荐。

## 卖家画像摘要与实际权重

- 市场允许：`profile.constraints.target_marketplaces=[tiktok-us, amazon-us]`、`target_countries=[US]`。
- 单 SKU 资金上限：`profile.constraints.capital_per_sku_max=30000 CNY`；现金周期容忍度为 45 天。
- 禁做：食品、医疗器械、儿童安全用品，以及液体、粉末、刀具、强磁、侵权图案、大件易碎。
- 能力：`profile.capabilities.supply_chain=1688采购`、`ad_skill=3`、`content_skill=5`、团队 2 人。
- 毛利偏好：`profile.preferences.margin_floor_pct=35`。
- 实际权重：demand 25%、competition 15%、margin 20%、capability_fit 25%、risk 15%。
- learned：active 0 条；proposed 1 条；revoked/expired/superseded 各 0 条。`learned_tiktok_same_density_diff_001` 为 proposed，且作用域为 TikTok，本次不参与。

## 数据源、样本边界与工具角色

样本只包含一个合成候选的空 facts、空 evidence 和团队工具可用性声明。未进行 MCP、浏览器或外部查询。`scripts/check_data_access.py` 显示卖家精灵、SIF、Sorftime、领星实时查询均未验证，仅 synthetic demo ready。

| provider / 能力 | source_role | 本次实际只读操作 | 能证明什么 | 不能证明什么 |
|---|---|---|---|---|
| repository fixture | collection_only | 读取 `references/demo-data/eval-tool-role-boundaries.json` 中 `ops-only` | 合成评测输入与缺失字段 | 真实 Amazon US 市场事实 |
| 紫鸟浏览器 | capability_context | 读取团队拥有该工具的声明；未读取账号、IP、Cookie 或登录态 | 画像确认后的运营环境背景 | 销量、搜索、竞争、成本、供应链 |
| AMZ123 | discovery_only | 读取团队拥有该导航工具的声明 | 可发现后续原始来源 | 导航页本身不构成事实证据 |
| 领星 ERP | seller_first_party_data | 仅读取拥有工具的声明；未导入或查询任何报表 | 若以后有合规只读数据，只能说明该卖家历史经营范围 | 外部市场需求与竞争；本次也不能证明任何候选事实 |
| Amazon Ads Academy | official_reference | 读取团队拥有学习网站的声明 | 官方学习/规则参考 | 实时市场需求、竞争和候选广告表现 |
| Google 翻译 | transformation_only | 读取团队拥有翻译工具的声明；本次未执行翻译 | 仅能转换有原始来源的文本 | 不产生新事实或提高证据等级 |

- collectors：无。
- transformations：无（只声明拥有 Google 翻译，未实际转换数据）。
- 被拒绝的写操作：无；本次未请求写操作。
- 数据窗口：fixture 采集时间为 2026-07-12，但 `ops-only` 没有候选事实证据；因此不存在可用于评分的市场窗口或指标口径。

## 候选清单

| candidate_id | 状态 | demand | competition | margin | capability_fit | risk | 总分 | 置信度 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| ops-only | blocked_pending_data | N/A | N/A | N/A | N/A | N/A | N/A | 不足 |

不把证据缺失换算为 0、2 或 3 分，也不因团队拥有运营、导航、ERP、学习或翻译工具而提高任何市场维度。关键事实不足，无法确认资金、毛利、合规和物流硬约束是否通过。

## 个性化归因

### 为什么可能适合你

- 目标站点在 `profile.constraints.target_marketplaces` 与 `target_countries` 的允许范围内。
- `profile.capabilities.content_skill=5`、`product_style` 包含轻创新和功能改良，理论上可支持办公配件的内容与差异化探索；但这只是能力匹配假设，不是推荐依据。

### 为什么目前不适合你

- 没有采购成本、MOQ、重量和价格，无法核对 `profile.constraints.capital_per_sku_max=30000 CNY`、45 天现金周期和 `profile.preferences.margin_floor_pct=35`。
- 没有合规与属性证据，无法排除 SOP 和 `profile.constraints.forbidden_categories/forbidden_attributes` 的一票否决项。
- 没有 Amazon US 销量、搜索或竞争证据，无法判断 Amazon 搜索需求、评论护城河、广告依赖与差异化空间；`profile.capabilities.ad_skill=3` 也无法据此判断广告门槛是否匹配。

### 主要风险

- 事实风险：上述关键事实全部缺失，硬约束无法判定。
- 经验风险：Amazon 策略要求同时核验搜索需求、竞争、利润、广告依赖、合规、物流与供应链；工具所有权不能替代这些数据。
- 待核实：目标市场需求、竞争、售价、采购成本、MOQ、重量、合规；另需补充搜索词/ASIN、评论门槛、物流尺寸、首批投入、完整成本口径、现金周期和供应商交付/差异化能力。

### 下一步最小验证

1. 用已验收的 Amazon US 只读市场来源或 verified import，补关键词/ASIN、销量或 BSR 趋势、搜索量、评论、集中度、CPC/广告依赖，并保留站点、日期、窗口和指标口径。
2. 用 1688 或其他供应商的可追溯只读/导入证据补采购价、MOQ、重量、尺寸、交期、定制和包装；该数据只验证供给，不替代 Amazon 需求。
3. 补售价、平台费、物流、广告、退货、税费与合规成本；references 未覆盖的数字均标为“需人工核实”，只在完整口径下核对 35% 毛利与 30000 CNY 首批投入红线。

## 被过滤品及原因

无。证据不足不能擅自判定命中一票否决，因此没有把 `ops-only` 记为 filtered。

## blocked_pending_data

| candidate_id | 缺失字段 |
|---|---|
| ops-only | target_market_demand, competition, price, procurement_cost, moq, weight, compliance |

## 依据分类

- 数据依据：合成 fixture 中 `ops-only` 的空 facts/evidence、工具可用性声明和 missing_fields；不代表真实市场数据。
- 画像依据：`profile.constraints`、`profile.capabilities`、`profile.preferences` 与 SOP 一票否决/判断习惯。
- 经验依据：`references/platforms/amazon.md` 的分析路径，不作为事实数字。
- 需人工核实：所有真实 Amazon US 市场、成本、物流、合规与供应链事实。

## 下一步建议

保持“不推荐、待补数据”。优先接入一个经过只读验收的 Amazon US 直接市场数据来源和一组可追溯供应链报价；在此之前不得给分、精确排序或商业推荐。
