# 旅行药盒 / 防水标签药盒：1688 供给侧验证

- seller_id: eval-content
- platform_adapter: 1688
- run_mode: synthetic_demo
- conclusion_type: supply_validation_only
- 结论：当前只能确认两条供给线索，不能确认目标市场需求，也不能形成商业推荐或精确排序；两个候选均因关键字段缺失进入 `blocked_pending_data`。

## 任务与边界

本报告只使用 `references/demo-data/eval-community-supply.md` 的“1688 信号”段进行供给侧验证。该段是合成评测数据，不使用同文件 Reddit 段，也没有调用实时 MCP、浏览器或外部平台数据。

1688 数据只能回答供给可行性，不能证明 Amazon US 或 TikTok US 有需求。真实市场数据链路未验证。

## 卖家画像摘要与实际评分权重

- 目标：`profile.constraints.target_marketplaces=[tiktok-us, amazon-us]`，`profile.constraints.target_countries=[US]`。
- 资金红线：`profile.constraints.capital_per_sku_max=30000 CNY`；SOP 同样规定首批已知投入超过 30000 CNY 不进入测试。
- 禁做边界：`profile.constraints.forbidden_categories=[食品, 医疗器械, 儿童安全用品]`，`profile.constraints.forbidden_attributes=[液体, 粉末, 刀具, 强磁, 侵权图案, 大件易碎]`。
- 能力：`profile.capabilities.supply_chain=1688采购`、`profile.capabilities.content_skill=5`、`profile.capabilities.team_size=2`。
- 偏好：`profile.preferences.margin_floor_pct=35`、`profile.preferences.product_style=[轻创新, 功能改良, 情绪价值]`。
- 实际权重：demand 25%、competition 15%、margin 20%、capability_fit 25%、risk 15%，覆盖默认权重；但本次仅有 1688 供给数据且关键字段不足，因此不计算分项分或总分。
- learned 规则：active 0 条；proposed 1 条；revoked/expired/superseded 各 0 条。`learned_tiktok_same_density_diff_001` 为 proposed，不参与过滤或打分。

## 数据源、第一屏样本与数据缺口

| 项目 | 本次记录 |
|---|---|
| provider | 1688 synthetic fixture |
| provider_variant | `eval-community-supply:1688-section` |
| source_role | `direct_market_data`（仅供给侧） |
| read operation | 读取 `references/demo-data/eval-community-supply.md` 的“1688 信号”段 |
| collector | 无 |
| transformations | 无 |
| 采集日期 | 2026-07-11 |
| 搜索词 | 旅行药盒；防水标签药盒 |
| 第一屏范围 | 每个搜索词只查看第一屏，合计 42 条 |
| 样本性质 | **便利样本，不代表市场全貌** |
| 账号/区域影响 | 未提供，需人工核实 |
| 每词具体条数 | 未提供，需人工核实 |
| 被拦截数量 | 未提供，需人工核实 |
| 解析失败/空白行数量 | 未提供，需人工核实 |

因此不得把本样本描述为全网供给、主流价格带或完整供应商分布。

## 候选清单

| 线索顺序 | candidate_id | 客观字段 | 语义匹配判断 | 状态 | demand | competition | margin | capability_fit | risk | 总分/置信度 |
|---:|---|---|---|---|---|---|---|---|---|---|
| 1 | 1688-s1 | 主营收纳盒；可做防水贴纸；MOQ 500；交期未返回 | 主营与旅行药盒的收纳场景较接近，且存在贴纸差异化线索；仍不能确认其为专业药盒供应商 | blocked_pending_data | N/A | N/A | N/A | N/A | N/A | 不计算 / 低 |
| 2 | 1688-s2 | 主营包装印刷；药盒是边缘产品；MOQ 200；重量、尺寸未返回 | 防水标签/包装能力可能相关，但药盒不是主营，成品供给专业度弱于 S1 | blocked_pending_data | N/A | N/A | N/A | N/A | N/A | 不计算 / 低 |

线索顺序只表示现有供给语义的优先核实顺序，不是商业机会排名。样本未提供去重前后条数、稳定商品 URL 或更多商品 ID，无法复核 42 条样本的去重结果。

## 逐候选归因与最小验证

### 1688-s1

**为什么适合你**

- `profile.capabilities.supply_chain=1688采购`，团队具备继续询盘与打样的基础。
- `profile.preferences.product_style` 包含功能改良；“收纳盒 + 防水贴纸”与功能差异化方向相符。

**为什么不适合你**

- `profile.constraints.capital_per_sku_max=30000 CNY`，但缺采购价、样品费和其他成本，无法判断 MOQ 500 是否越过资金红线。
- `profile.capabilities.team_size=2`，交期和补货周期缺失会放大小团队的跟单与断货风险。

**主要风险**

- 事实风险：交期未返回；没有价格、重量、尺寸、材质、商品链接和供应商服务字段。
- 推断风险：主营“收纳盒”不等于主营“旅行药盒”，专业度仍需核实。
- 需求风险：没有 Amazon/TikTok/SHEIN 数据，不能确认美国市场需求。

**下一步最小验证**

索取稳定商品链接、完整阶梯价、MOQ 对应 SKU/单位、样品价、交期、重量尺寸材质、防水贴纸规格及最低定制量，并核实主营类目、地区、经营年限和跨境资料能力。

### 1688-s2

**为什么适合你**

- `profile.capabilities.supply_chain=1688采购` 可支持后续供应商询盘。
- MOQ 200 低于 S1 的 500，方向上更接近小批量测试，但缺价格，不能换算首批投入。

**为什么不适合你**

- SOP 要求同款过多时必须能从结构、套装或内容角度给出可感知差异；现有数据只显示包装印刷能力，未证明成品结构或套装差异化。
- `profile.constraints.forbidden_attributes` 禁止大件易碎，而重量和尺寸未返回，物流属性无法核验。

**主要风险**

- 事实风险：药盒只是供应商边缘产品；重量、尺寸未返回；价格、交期、材质、链接和跨境字段也缺失。
- 推断风险：包装印刷专业度不能替代药盒品控和稳定交付能力。
- 需求风险：没有目标平台数据，不能确认消费者会购买。

**下一步最小验证**

先确认供应商是否实际生产药盒或仅做印刷配套，再索取稳定商品链接、阶梯价、样品价、交期、重量尺寸材质、药盒品控资料、防水印刷方案、最低定制量和跨境经验。

## 被过滤品

无。现有事实不足以判定命中禁做类目、禁做属性或资金红线；不能把“尚未证明冲突”当作“已通过过滤”。

## blocked_pending_data

| candidate_id | 明确缺失字段 |
|---|---|
| 1688-s1 | 稳定商品链接/商品标题/类目属性、采购价与阶梯数量及单位、样品价或打样费、交期、重量、尺寸、材质与敏感属性、包装/Logo/颜色/模具及最低定制量、供应商地区/经营年限/服务字段、跨境经验与可提供资料、首批总投入、目标平台需求数据 |
| 1688-s2 | 稳定商品链接/商品标题/类目属性、采购价与阶梯数量及单位、样品价或打样费、交期、重量、尺寸、材质与敏感属性、包装/Logo/颜色/模具及最低定制量、供应商地区/经营年限/服务字段、药盒生产与品控能力、跨境经验与可提供资料、首批总投入、目标平台需求数据 |

## 依据分层

- 数据依据：指定 fixture 的 1688 段，仅支持上述搜索词、42 条第一屏便利样本、S1/S2 的主营方向、MOQ 及明确缺失描述。
- 画像依据：`sellers/eval-content/profile.yaml`、`sellers/eval-content/sop.md` 和最近 3 条决策记录。
- 经验依据：`references/platforms/1688-supply-chain.md` 与 `references/data-sources/1688-supply-validation.md` 的供给验证框架，不作为事实数字。
- 待核实项：全部候选缺失字段、样本采集环境、去重与拦截统计、目标平台需求、物流/平台费/广告/退货/合规/税费及真实毛利。

## 下一步建议

1. 优先补齐 S1 的价格、交期和定制字段，再补齐 S2 的成品生产关系、重量尺寸与价格字段。
2. 用报价与 MOQ 计算已知首批采购投入；其他成本未有合规事实来源前保持“需人工核实”。
3. 另行获取 Amazon US 或 TikTok US 的目标平台需求与竞争数据；在此之前维持 `supply_validation_only`，不输出商业推荐。

