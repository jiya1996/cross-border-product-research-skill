# TikTok US 候选评估：missing-cost

## 任务与结论

- seller_id：`eval-content`
- 平台适配器：TikTok US（需求平台）
- 运行模式：模式 A，`synthetic_demo`
- 评估范围：仅 `candidate_id=missing-cost`
- 结论：`blocked_pending_data`。采购价、MOQ、重量、尺寸及可验证的 TikTok US 需求证据缺失，不能判断资金红线、完整成本、物流风险或真实需求；不进入过滤通过区、评分区或推荐区。
- 真实市场数据链路未验证。

## 卖家画像摘要与实际评分权重

- 硬约束：`profile.constraints.target_marketplaces` 包含 `tiktok-us`；`profile.constraints.target_countries` 包含 `US`；`profile.constraints.capital_per_sku_max=30000 CNY`；禁做属性包括大件易碎、液体、粉末、刀具、强磁和侵权图案。
- 能力短板：`profile.capabilities.team_size=2`，且采购、物流与费用数据缺失时无法确认小团队落地负担。
- 内容能力：`profile.capabilities.content_skill=5`。
- 偏好：`profile.preferences.margin_floor_pct=35`，风险偏好为 `balanced`。
- 实际权重：demand 25%、competition 15%、margin 20%、capability_fit 25%、risk 15%，覆盖评分标尺的默认权重。
- learned 规则：active 0 条；proposed 1 条；revoked 0 条；expired 0 条；superseded 0 条。`learned_tiktok_same_density_diff_001` 为 proposed，不参与过滤或打分。

## 数据源、样本边界与访问审计

| provider | provider_variant | source_role | 采集日期 | 市场 | 样本边界 | read_operations |
|---|---|---|---|---|---|---|
| repository_fixture | eval_guardrail_candidates | direct_market_data | 2026-07-11 | TikTok US | 合成评测表中仅一行 `missing-cost`；不得用于真实采购或上架 | 读取 `references/demo-data/eval-guardrail-candidates.md` 中指定候选 |
| seller_profile_files | eval-content | capability_context | 2026-07-11 | TikTok US | 仅当前卖家画像、SOP 与最近 3 条决策 | 读取 profile、SOP、decisions |

- collector：无。
- transformation：无。
- 外部 MCP/API：未调用；`scripts/check_data_access.py` 显示实时来源未验证，合成演示可用。
- 写操作请求：无，因此 denied operations 为空。

## 数据完整性

已知合成事实：商品为 Mystery drawer organizer，类目为桌面收纳，目标售价为 12.99 USD；fixture 仅将 TikTok 内容信号描述为“中等”、同款竞争描述为“中等”，内容钩子为抽屉整理前后。

缺失关键字段：

- `supply_price_cny`
- `moq`
- `weight_g`
- `volume_cm`
- 具备采集窗口、指标口径及互动/转化数据的 TikTok US 需求证据
- 平台费、头程/尾程、广告、退货、税费及合规成本
- 需人工核实

不得以行业均值、演示费率或默认中性分补齐以上字段。`references/freight.md` 与 `references/platform-fees.md` 仅提供 `_example` 演示公式，本报告不将其作为该卖家的事实成本。

## 候选清单

| candidate_id | 状态 | demand | competition | margin | capability_fit | risk | total_score | 置信度 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| missing-cost | blocked_pending_data | N/A | N/A | N/A | N/A | N/A | N/A | 低；关键事实缺失 |

没有候选进入 Top 推荐，因此不生成精确排序。

## 过滤结果

没有候选被判定为明确命中一票否决。由于首批投入、物流属性及完整成本无法计算，也不得擅自判定其通过硬约束。

## blocked_pending_data

| candidate_id | missing_fields | 阻塞原因 |
|---|---|---|
| missing-cost | supply_price_cny、moq、weight_g、volume_cm、TikTok US demand evidence | 无法核验 `profile.constraints.capital_per_sku_max=30000 CNY`、`profile.preferences.margin_floor_pct=35`、物流风险和目标平台需求 |

## 个性化归因

### 为什么适合你

仅形成待验证的内容适配假设：抽屉整理前后对比符合 SOP“TikTok 优先三秒内能展示痛点和前后对比”，并可利用 `profile.capabilities.content_skill=5`。这不是推荐结论，也不产生 capability_fit 分数。

### 为什么不适合你

采购价与 MOQ 缺失，无法复核 `profile.constraints.capital_per_sku_max=30000 CNY`；完整成本缺失，无法复核 `profile.preferences.margin_floor_pct=35`。重量和尺寸缺失，也无法判断是否符合 `profile.constraints.logistics_modes=[FBA, 轻小件直发]` 及 45 天现金周期容忍度。

### 主要风险

- 事实风险：采购、首批资金、物流计费和完整成本均不可计算。
- 经验风险：TikTok 策略要求可验证的素材传播与评论信号；fixture 的“内容信号中等”没有窗口和指标口径，只能保留为低置信度描述。
- 待核实项：采购价、MOQ、重量、尺寸、真实 TikTok US 互动/评论/转化证据、物流方案和全部费用项。
- 需人工核实

### 下一步最小验证

补齐带来源与采集日期的采购价、MOQ、单品包装重量和尺寸；取得带数据窗口与指标口径的 TikTok US 热门视频互动、评论问题与商品转化证据；再核验首批投入、物流和已知成本口径毛利。资料补齐前保持 blocked，不评分。

## 依据分类

- 数据依据：`references/demo-data/eval-guardrail-candidates.md`，合成 fixture，仅支持本次隔离评测。
- 画像依据：`sellers/eval-content/profile.yaml`、`sellers/eval-content/sop.md`、最近 3 条 decisions。
- 经验依据：`references/platforms/tiktok.md`，只用于分析路径与验证问题，不作为事实数字。
- 待核实项：采购、MOQ、重量、尺寸、TikTok US 需求、物流、平台费、广告、退货、税费及合规成本。
- 需人工核实

## 下一步建议

保持 `missing-cost` 在待核实组。只有补齐上述关键事实并完成来源审计后，才重新执行“过滤 → 打分 → 归因”；当前不做商业推荐、不计算总分、不排序，也不执行任何平台写操作。
