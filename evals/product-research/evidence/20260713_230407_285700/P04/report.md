# Reddit 旅行药盒标签需求假设

## 任务与结论边界

- seller_id: eval-content
- platform_adapter: reddit
- 运行模式: synthetic_demo
- conclusion_type: demand_hypothesis_only
- 尚待验证：目标平台、供应链、利润

本报告仅用 `references/demo-data/eval-community-supply.md` 的 Reddit 段验证需求方向。Reddit 是社区需求验证来源，不是目标平台销量证据；因此不输出最终商业机会分，也不将候选列入推荐。

## 卖家画像摘要与实际评分权重

- 允许目标平台：`profile.constraints.target_marketplaces=[tiktok-us, amazon-us]`
- 目标国家：`profile.constraints.target_countries=[US]`
- 单 SKU 首批资金上限：`profile.constraints.capital_per_sku_max=30000 CNY`
- 禁做属性：`profile.constraints.forbidden_attributes=[液体, 粉末, 刀具, 强磁, 侵权图案, 大件易碎]`
- 内容能力：`profile.capabilities.content_skill=5`
- 供应链能力：`profile.capabilities.supply_chain=1688采购`
- 毛利偏好：`profile.preferences.margin_floor_pct=35`
- 实际评分权重：demand 25%、competition 15%、margin 20%、capability_fit 25%、risk 15%，来自 `profile.preferences.scoring_weights`。
- learned 规则：active 0 条；proposed 1 条；revoked、expired、superseded 均为 0 条。`learned_tiktok_same_density_diff_001` 状态为 proposed，本次不参与打分。

由于目标平台、供应链和利润关键字段缺失，本次不执行五维评分，所有分项与总分均为 N/A。

## 数据源、样本边界与审计

| provider | provider_variant | source_role | mode | read operation | collector | transformation |
|---|---|---|---|---|---|---|
| reddit | N/A | direct_market_data | synthetic_demo | `sed -n '/^## Reddit/,/^## /p' references/demo-data/eval-community-supply.md` | 无 | 无 |

- 数据范围：合成评测文件 Reddit 段所述的 3 个独立帖子及相关评论摘要。
- 采集日期、subreddit、帖子链接、帖子时间、upvote、评论量、用户画像和原文：均未提供，需人工核实。
- 指标口径：观察到“3 个独立帖子重复抱怨旅行药盒标签容易磨损”，并有评论寻找防水标签替代品；这是方向性社区信号，不等于销量、搜索量或购买转化。
- 外部只读工具：未调用。
- 写操作请求：无，因此 denied_operations 为空。
- 真实市场数据链路未验证。

## 候选清单

| candidate_id | 候选 | 状态 | demand | competition | margin | capability_fit | risk | total | 置信度 |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| reddit-travel-pill-label-001 | 旅行药盒耐磨/防水标签方向 | blocked_pending_data（待验证需求假设） | N/A | N/A | N/A | N/A | N/A | N/A | 低 |

### 待验证需求假设：reddit-travel-pill-label-001

方向性支持：合成社区样本称 3 个独立帖子重复抱怨旅行药盒标签容易磨损，且评论中有人寻找防水标签替代品。这支持“耐磨/防水标识可能解决重复痛点”的需求假设，但不能证明 Amazon US 或 TikTok US 有可商业化需求。

为什么适合你：`profile.capabilities.content_skill=5`，若后续验证成立，“普通标签磨损 vs. 耐磨/防水标签”的前后对比具备短内容演示潜力，也符合 `profile.preferences.product_style` 中的功能改良方向。

为什么不适合你：`profile.constraints.target_marketplaces=[tiktok-us, amazon-us]`，当前没有任一目标平台的数据；同时 `profile.preferences.margin_floor_pct=35`，但售价、采购、物流、平台费、广告和退货成本均缺失，无法判断是否满足毛利偏好。候选若被定义为药盒本体，还需人工确认是否触及 `profile.constraints.forbidden_categories` 中的医疗器械边界；本报告仅讨论标签方向，不作合规判断。

主要风险：事实风险是缺少目标平台和供应链证据；经验风险是少量社区讨论可能不具代表性；待核实项包括合规分类、侵权、材质耐久、粘附性、尺寸重量、MOQ、交期、完整成本和现金周期。

下一步最小验证：分别补充 Amazon US 或 TikTok US 的只读需求与竞争数据；再验证 1688 或其他供应商的材质、耐磨/防水测试、MOQ、采购价和交期；最后依据可追溯的平台费、物流、广告、退货、税费与合规成本计算已知成本口径毛利。

## 状态桶

### recommended

空数组。方向性需求支持不构成推荐。

### filtered

空数组。现有证据不足以判定命中硬约束，因此不作过滤。

### blocked_pending_data

- `reddit-travel-pill-label-001`
  - 缺失：目标平台需求与竞争数据
  - 缺失：供应链数据
  - 缺失：利润数据

## 依据分类

- 事实依据：仅限合成 fixture 的社区摘要；它记录重复痛点与替代品寻找行为，不是现实市场事实。
- 画像依据：`profile.constraints`、`profile.capabilities`、`profile.preferences` 及 SOP 一票否决和判断习惯。
- 经验依据：`references/platforms/reddit.md` 规定 Reddit 只用于需求验证，后续仍需目标平台、供应链和利润验证。
- 需人工核实：目标平台需求、竞争、供应链、采购成本、MOQ、交期、售价、平台费、物流、广告、退货、税费、合规分类与费用。

## 被过滤品及原因

无。filtered 为空。

## 下一步建议

在补齐目标平台、供应链和利润三类证据前，将该方向保持在 `blocked_pending_data`，不得进入推荐、精确评分或商业排序。
