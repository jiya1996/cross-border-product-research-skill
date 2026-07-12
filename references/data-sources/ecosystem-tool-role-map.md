# 跨境工具角色与选品证据边界

核验日期：2026-07-12。机器可读注册表见 `tool-role-registry.json`。

本文件解决一个容易被忽略的问题：**工具有用，不等于它产出的任何内容都能进入选品评分。** 同一个品牌可能同时提供市场查询、内容生成、广告管理和自动上架，必须按具体能力做白名单，而不是按品牌整包授权。

## 1. 来源角色

| 角色 | 能否作为候选事实 | 可影响的范围 |
|---|---|---|
| `direct_market_data` | 可以，前提是站点、时间窗口、指标口径和来源完整 | demand、competition、risk |
| `seller_first_party_data` | 可以，但只代表当前卖家/店铺的历史范围 | margin、capability_fit、risk；有明确 ASIN/关键词范围时可辅助 demand/competition |
| `official_reference` | 可用于官方规则、定义和流程 | 不直接产生需求分；数字仍要带版本、市场和日期 |
| `experience_reference` | 不可以作为事实数字 | 只生成假设、问题和 `observations.kind=experience` |
| `discovery_only` | 不可以 | 只发现原始网站或工具，必须继续追到原始来源 |
| `capability_context` | 不可以作为市场事实 | 只有 profile/SOP 已确认时可影响 capability_fit |
| `transformation_only` | 不可以 | 翻译、抠图、换模特等转换；必须保留原始来源 |
| `collection_only` | 不可以替代原 provider | 只负责搬运/导出；事实来源仍是原系统 |
| `forbidden_write` | 不得调用 | 催评、提现、登录店铺、上架、调价、广告、库存、订单和履约写操作 |

只有 `direct_market_data`、`seller_first_party_data` 和满足知识政策的 `official_reference` 可以进入 `facts/evidence`。其他角色可以出现在来源审计或观察项中，但不能被包装成市场事实。

## 2. 十类工具怎么用

| 工具 | 允许进入 Skill 的能力 | 不能做什么 | 接入建议 |
|---|---|---|---|
| 卖家精灵 | 产品、市场、关键词、集中度、评论、流量、CPC 等只读研究 | 一键催评和任何店铺操作 | P0：优先只读 MCP；无 MCP 时导入核实后的 XLSX/CSV |
| 紫鸟浏览器 | 经画像确认的账号运营环境能力 | 不作为市场数据，不读取或记录账号/IP/Cookie/登录态，不登录店铺 | 不进入核心数据层 |
| SIF | 市场、关键词、流量结构、广告依赖等只读分析 | 不用单一流量结构证明完整市场需求 | P0：只读 MCP 或核实导出 |
| AMZ123 | 发现工具和原始网站 | 导航页不能成为事实来源 | 只作 `discovery_only` |
| 领星 ERP | 用户授权的销量、利润、库存、退货、广告等卖家私域历史数据 | 不把自身历史外推成全市场；不调用采购、库存、广告、自定义指标等写动作 | P1：先 verified CSV/XLSX 回测，再评估受限子账号 MCP/OpenAPI；见 `lingxing-readonly-plan.md` |
| 知无不言 | 人工阅读后的经验、反例、问题清单 | 不自动批量抓取，不把帖子数字当事实或硬阈值 | 只作 `experience_reference` |
| 亚马逊广告 | Academy 官方规则；用户导出的只读广告报告 | 学习案例不替代市场数据；不建活动、不改竞价/预算 | Academy 作 reference；报告作 seller first-party data |
| Google 翻译 | 评论、关键词、报告的语言转换 | 翻译结果不是新事实，不能丢失原文 | 只作 `transformation_only` |
| 虎步 RPA | 固定白名单下载型 RPA 的报表投递 | 不执行自动提现、广告、上架、消息、任意 UI 操作；不向 Agent 暴露通用任务创建权 | P2：仅作 collector，结果重新按 verified import 验收；见 `hubu-collector-boundary.md` |
| LinkFox | AI 作图用于素材验证；有上游来源的只读研究导出可作对照 | 作图不证明需求；不得调用自动上架、工厂下单或履约 | P2：创意层/外部对照；研究数据必须保留上游 provider |

### LinkFox 命名提醒

用户熟悉的 LinkFox 是 AI 模特、商品图、换场景和抠图工具；其官方产品现也包含聚合多数据源的 Agent 和自动上架/履约能力。批次中必须写清 `provider_variant`：

- `linkfox_creative`：只允许出现在 `transformations` 或 capability context；
- `linkfox_agent_gateway`：只能作为 collector，必须保留卖家精灵、SIF、Keepa 等 `original_provider`；
- 自动上架、订单、工厂和物流能力永久禁用。

## 3. Amazon 第一阶段字段映射

### 卖家精灵

| 能力 | 进入字段 | 注意事项 |
|---|---|---|
| 产品/竞品 | ASIN、价格、评分、评论、BSR/销量趋势 | 销量与 BSR 换算默认标记 `estimated` |
| 市场 | 类目规模、增长、价格分布、新品占比 | 记录类目节点、站点、样本范围和数据窗口 |
| 集中度 | 商品、品牌、卖家 Top N 占比 | 必须记录 N 和分母，不能只写“集中度低” |
| 关键词/ABA | 搜索量、趋势、购买率、点击集中度 | 记录周/月口径和匹配方式 |
| CPC/流量 | CPC、自然/广告流量结构、流量词 | 支持广告依赖和竞争判断，不等于实际转化 |

### SIF

| 能力 | 进入字段 | 注意事项 |
|---|---|---|
| 市场/关键词 | 搜索量、竞争密度、需求结构、趋势 | 与卖家精灵冲突时保留双方，不擅自平均 |
| 流量 | 自然/广告流量、流量词、异常趋势 | 主要支持 competition 和 ad dependency |
| 广告 | Campaign/Ad Group/关键词窗口表现 | 绑定 seller_id、非敏感 account_scope_id 和时间窗口 |

## 4. 搬运、翻译与聚合不得改写来源

例：虎步下载了一份 Amazon Ads XLSX，并用 Google 翻译处理了搜索词。

- `provider=amazon_ads`
- `source_type=xlsx`
- `source_role=seller_first_party_data`
- `collector=hubu_rpa`
- `transformations=[google_translate]`
- `account_scope_id` 使用不可反推真实店铺的本地别名

不能写成 `provider=hubu_rpa` 或 `provider=google_translate`。搬运工具和转换工具不拥有事实。

注意：来源经过虎步搬运后，`source_role` 仍应继承原报表的事实角色，例如 Amazon Ads 店铺报表仍为 `seller_first_party_data`；`hubu_rpa` 只出现在 `collector`。`collection_only` 描述的是虎步自身能力，不是对被搬运事实降格或改名。

## 5. 能力级只读验收

接入任何品牌前都必须完成：

1. 列出实际 MCP/API/RPA 工具名；
2. 逐项标记 read/write 和来源角色；
3. 只启用注册表中 `direction=read` 且业务需要的能力；
4. 对含写能力的平台建立显式 denylist；
5. 用合成 fixture 验证 provider、collector、transformation 不会混淆；
6. 用最小真实查询验证字段、站点、日期、缺失值与零写操作；
7. 报告显示实际使用来源及被拒绝的操作。

未经上述验收，不得在报告中写“已接入”或“实时数据已验证”。

## 6. 官方核验入口

- 卖家精灵开放平台：<https://open.sellersprite.com/mcp>
- SIF MCP：<https://mcp.sif.com/>
- 紫鸟帮助：<https://www.ziniao.com/help/docs/Overview>
- AMZ123 关于：<https://www.amz123.com/about>
- 领星帮助/API：<https://www.lingxing.com/help/index>、<https://apidoc.lingxing.com/>
- 领星官方 MCP：<https://www.lingxing.com/help/article/mcp>
- 知无不言：<https://www.wearesellers.com/page/aboutus>
- Amazon Ads Academy：<https://advertising.amazon.com/academy/catalog?activeLocale=zh-cn>
- Google Translate：<https://support.google.com/translate/>
- 虎步 RPA：<https://support.huburpa.com/7d8f/806d>
- 虎步 API 入门：<https://support.huburpa.com/cc8e/bc56/6708>
- LinkFox Agent：<https://www.linkfox.com/agent>

官方页面只能证明“该能力被产品方公开描述”，不能自动证明具体查询结果准确。实际数据仍需通过 `adapter-contract.md` 保存口径、日期、范围和缺失项。
