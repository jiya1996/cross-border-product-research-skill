# 选品数据适配器契约

本契约把“数据怎么来”和“Agent 怎么判断”分开。MCP、浏览器采集、用户导入和合成测试数据都必须先归一化，再进入 `product-research`。

机器可读结构见 `references/schemas/candidate-batch.schema.json`，工具能力白名单见 `tool-role-registry.json`，人类可读边界见 `ecosystem-tool-role-map.md`。

## 1. 批次级必填字段

| 字段 | 含义 | 纪律 |
|---|---|---|
| `schema_version` | 当前为 `1.1` | 1.0 批次必须补齐来源角色后再进入评分 |
| `batch_id` | 本次采集唯一 ID | 同一卖家不同运行不得复用 |
| `seller_id` | 数据归属卖家 | 必须与任务 seller_id 一致 |
| `platform` | 需求平台或验证来源 | amazon/shein/tiktok/dtc-seo/reddit/1688 |
| `market` | 国家/站点 | 不明确时填 `unknown`，不得猜 |
| `collected_at` | ISO 8601 采集时间 | 用于缓存和时效判断 |
| `mode` | 数据模式 | live_mcp/verified_import/browser_assisted/synthetic_demo |
| `sources` | 来源清单 | 每条事实通过 `source_id` 回指 |
| `candidates` | 候选数组 | 每条至少含稳定 ID、名称与证据 |

## 2. 来源记录

每个 `sources[]` 项至少包含：

- `source_id`：批次内唯一；
- `provider`：如 sellersprite、sorftime、1688、reddit、user_import；
- `source_type`：mcp、api、browser、csv、json、reference、synthetic；
- `locator`：ASIN、关键词、公开 URL、导入文件路径或 reference 路径；
- `collected_at`：采集时间；
- `scope`：该来源能支持的结论，例如“Amazon US 关键词需求”或“1688 供给价格”；
- `synthetic`：是否为合成数据。
- `source_role`：`direct_market_data`、`seller_first_party_data`、`official_reference`、`experience_reference`、`discovery_only`、`capability_context`、`transformation_only` 或 `collection_only`；
- `allowed_dimensions`：该来源可影响的评分维度；无资格参与评分时必须为空数组；
- `read_only`：本次实际使用能力是否只读；只有 `true` 的来源才能进入批次；
- `measurement_kind`：`observed`、`estimated`、`derived`、`declared` 或 `unknown`。

按需补充：

- `tool_name`：实际 MCP/API 工具名，不写泛化品牌名；
- `provider_variant`：同品牌多类产品的明确变体，例如 `linkfox_creative`；
- `original_provider`：聚合器或搬运工具背后的原始数据系统；
- `collector`：如 `hubu_rpa`，只记录搬运者，不覆盖原 provider；
- `transformations`：如 `google_translate`，只记录转换过程；
- `data_window`、`metric_definition`：指标时间窗口与口径；
- `account_scope_id`：不可反推真实店铺的本地别名，用于隔离卖家私域数据。

Cookie、Token、认证头、真实 MCP 地址不得进入批次。

### 2.1 来源角色门禁

| 来源角色 | 能否被 `evidence[]` 引用 | 评分边界 |
|---|---|---|
| `direct_market_data` | 可以 | 仅限 `allowed_dimensions`，必须有站点、日期、窗口与指标口径 |
| `seller_first_party_data` | 可以 | 只代表该卖家/店铺历史范围，不得外推全市场 |
| `official_reference` | 可以引用规则/定义 | 不直接产生市场需求分；数字必须有版本与适用市场 |
| `experience_reference` | 不得作为事实值 | 只进入 `observations.kind=experience` |
| `discovery_only` | 不得 | 继续追到原始来源 |
| `capability_context` | 不得作为市场事实 | 画像确认后只影响 capability_fit |
| `transformation_only` | 不得 | 保留原始 source_id；转换不升级事实等级 |
| `collection_only` | 不得替代原来源 | 使用 `original_provider`/`collector` 分开记录 |

AMZ123、Google 翻译、虎步 RPA、紫鸟和 LinkFox 创意能力不得成为销量、搜索量、利润或市场规模的事实 provider。卖家精灵/SIF/LinkFox 等品牌若同时包含写能力，必须按具体 `tool_name` 做 allowlist，不能按品牌整包授权。

## 3. 候选记录

每个 `candidates[]` 项分四层：

1. `identity`：`candidate_id`、名称、类目、平台链接或稳定 ID；
2. `facts`：价格、销量/互动、MOQ、重量、尺寸、评论、交期等原始事实；
3. `evidence`：事实字段、值、单位、`source_id`、采集日期；
4. `derived`：只保存带公式的可复算值，不保存无依据的模型猜测。

风险、内容钩子和差异化描述可放 `observations`，但必须标注为 `fact`、`experience`、`user_profile` 或 `inference`。

## 4. 缺失与冲突

- 未返回的字段写入 `missing_fields`，不要写 0、行业均值或中性分；
- 同一字段来源冲突时保留全部证据，在 `conflicts` 中记录；
- 运费、平台费、税费、认证、合规费用只有命中 `references/` 事实条目或用户核实来源时才能进入精确公式；
- 只有部分成本时，字段名必须是 `known_cost_margin`，不得叫 `actual_margin`；
- 1688 销量属于供应侧信号，不能映射为目标平台 demand；
- Reddit 讨论热度属于需求假设，不能单独映射为最终商业分。
- 卖家精灵、SIF 等同一指标口径不一致时保留双方，不得擅自平均；
- RPA 下载或翻译处理后的文件仍以原系统为 provider；
- 社区帖子中的日销、CPC、认证费和利润只能记为经验说法，不能进入 `facts`。

## 5. 缓存与隔离

- 缓存路径建议为 `reports/{seller_id}/raw/{batch_id}/`；
- 同一 ASIN、关键词、类目 7 天内可复用，但报告必须显示原采集时间；
- 用户要求刷新、平台变化剧烈或来源已失效时不得复用；
- 任何缓存读写都必须校验 `seller_id`，不得跨目录拼接；
- `seller_id` 只允许字母、数字、下划线、连字符，禁止 `.`、`/`、`..`。

## 6. 适配器验收

一个数据适配器只有同时满足以下条件才算可用：

- 只读；
- 不把秘密写盘；
- 能输出本契约字段；
- 对缺失字段显式标记；
- 能记录来源与采集日期；
- 不把来源角色夸大，例如把供应侧销量当消费需求；
- 能区分 provider、collector、transformation 和 capability context；
- 对混合读写品牌使用能力级 allowlist，并记录被拒绝的写操作；
- 用合成 fixture 可以离线重放；
- 多卖家并发时输出目录不冲突。
