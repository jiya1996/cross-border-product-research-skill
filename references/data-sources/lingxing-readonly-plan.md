# 领星只读数据接入与 90 天回测计划

核验日期：2026-07-12。

本文件定义领星 ERP 进入 `product-research` 的唯一合规路径。领星数据属于当前卖家的第一方经营数据，来源角色固定为 `seller_first_party_data`：可以验证当前卖家的销量、利润、库存、广告和售后表现，但不得外推成整个 Amazon 市场的需求或竞争事实。

## 1. 不可突破的边界

- 接入只用于查询、导出和离线回测；不上架、不改价、不改广告、不改库存、不改采购、不改订单、不触发发货或利润重算。
- 无论 HTTP 方法是 GET 还是 POST，都按“业务效果”判断读写。领星多个查询接口使用 POST，请求方法本身不能替代能力白名单。
- 真实服务器 URL、AppID、AppSecret、access token、X-Mcp-Key、店铺名和可复用认证头不得写入仓库。
- 每次数据进入评分前都必须满足 `adapter-contract.md`：绑定 `seller_id`，记录站点、时间窗口、币种、指标口径、采集时间和缺失项。
- 领星中的利润、ROI、ACoS、TACoS、库存天数等计算结果属于 ERP 计算口径；保存时使用 `measurement_kind=derived`，不得伪装成未经计算的原始观测。

领星官方说明 AppID/AppSecret 可访问企业数据，并要求妥善保管；OpenAPI 接入还要求公网 IP 白名单。[API 信息与安全说明](https://apidoc.lingxing.com/docs/Guidance/AppID.md)

## 2. 三阶段接入

| 阶段 | 目的 | 数据路径 | 上线条件 |
|---|---|---|---|
| E0：人工导出 | 最快完成真人数据试点和字段核对 | 受限账号导出 CSV/XLSX → 哈希与字段校验 → `verified_import` | 无 API 凭证；文件有 seller_id、窗口、币种和来源清单 |
| M1：官方 MCP | 低代码完成小范围实时只读查询 | 专用只读子账号 → 领星 MCP → 适配器归一化 | 付费账号已启用 MCP；账号权限和工具白名单均通过验收 |
| A2：OpenAPI | 稳定、可复现地批量拉取经营快照与回测数据 | 受控适配服务 → 精确接口白名单 → 不可变快照 | 独立凭证、固定 IP、接口权限和零写审计均通过验收 |

### 2.1 E0：先用导出跑真人试点

领星官方支持：

- 自定义报表可选择最近 90 天等动态区间并导出；被分享人可以只获得查看权限。[自定义报表](https://www.lingxing.com/help/article/customReport)
- 新版利润报表支持按店铺、Listing 和字段控制权限，成本与毛利润字段可单独限制，并支持自定义列导出。[利润报表](https://www.lingxing.com/help/article/ProfitStatementnew1)
- 本地仓和海外仓库存报表支持按时间段、数量/成本及汇总/明细查看和导出。[库存报表](https://www.lingxing.com/help/article/stockReport-local)
- 下载中心支持查看下载记录，并可定时生成利润报表；是否能使用受利润报表导出权限控制。[下载中心](https://www.lingxing.com/help/article/DownloadCenter1)

导入纪律：

1. 使用专用子账号，只授予目标店铺、目标 Listing 和必要字段的查看/导出权限。领星官方角色管理支持功能权限、店铺权限以及采购成本等数据权限设置。[角色管理](https://www.lingxing.com/help/article/UsersAndRoles)
2. 原始文件写入私有路径 `reports/{seller_id}/raw/{batch_id}/`，不得进入公开提交。
3. 生成 SHA-256，并记录导出人、本地导出时间、领星报表名称、筛选条件、币种、时间窗口、行数和字段列表。
4. 归一化来源写为 `provider=lingxing`、`source_type=xlsx|csv`、`source_role=seller_first_party_data`、`mode=verified_import`。
5. 若文件由其他工具搬运，仍以 `lingxing` 为 provider；搬运器单独写入 `collector`。

### 2.2 M1：官方 MCP

领星官方 MCP 仅限付费用户，由超级管理员启用；服务器 URL 和 `X-Mcp-Key` 与当前领星账号绑定，查询范围继承该账号在 ERP 内的数据权限。官方同时说明每个 Tool 的 QPS 为 1。[领星 MCP](https://www.lingxing.com/help/article/mcp)

MCP 不是天然只读。官方工具清单包含 `add_custom_indicator` 和 `update_custom_indicator` 等写工具，因此必须：

1. 为试点卖家建立专用子账号，不复用超级管理员账号；
2. 在领星中只授予目标店铺、Listing、SKU、仓库和必要成本字段的查看权限；
3. 在 Codex/MCP 客户端再次按工具名做 allowlist；
4. 只把查询结果交给适配器，不让模型获得密钥或修改权限；
5. MCP 工具清单发生变化时默认拒绝新工具，重新人工审计后才能启用。

首批允许的官方查询工具名如下；仅当本地实际返回的名称、参数和业务效果一致时才能启用：

| 工具 | 允许用途 |
|---|---|
| `get_my_sids` | 获取当前受限账号可见的店铺范围并映射为本地别名 |
| `get_fba_stock_list` | 查询 FBA 库存，不执行库存调整 |
| `erp_listing` | 查询 Listing、ASIN、MSKU 和经营表现 |
| `get_custom_report_list` | 查询账号有权限查看的自定义报表清单 |
| `get_custom_report_by_id` | 读取已存在的自定义报表 |
| `get_custom_indicator_list` | 读取现有指标定义 |
| `get_custom_indicator_field` | 读取指标字段枚举，不新增或修改指标 |

工具名称与官方用途来源：[领星 MCP 工具能力](https://www.lingxing.com/help/article/mcp)。任何不在表内或名称变化的工具默认拒绝。

### 2.3 A2：OpenAPI

OpenAPI 适合固定日期窗口、稳定分页和可复现回测。官方接入要求 AppID/AppSecret、access token、签名及公网 IP 白名单；API 请求域名为 `https://openapi.lingxing.com`。[OpenAPI 接入指南](https://apidoc.lingxing.com/docs/Guidance/newInstructions.md)

只读接口采用“精确路径白名单”，首批仅允许：

| 用途 | 方法与精确路径 | 约束 | 官方文档 |
|---|---|---|---|
| 店铺范围映射 | `GET /erp/sc/data/seller/lists` | 返回结果立即映射为不可反推真实店铺的 `account_scope_id` | [查询店铺列表](https://apidoc.lingxing.com/docs/BasicData/SellerLists.md) |
| 单日销量/订单/销售额 | `POST /erp/sc/data/sales_report/asinDailyLists` | 必须指定 sid、站点日期和 ASIN/MSKU 维度 | [销量统计](https://apidoc.lingxing.com/docs/Statistics/AsinDailyLists.md) |
| 产品表现 | `POST /bd/productPerformance/openApi/asinList` | 必须指定 sid、开始/结束日期和汇总维度；单次窗口不超过 92 天 | [产品表现](https://apidoc.lingxing.com/docs/Statistics/AsinListNew.md) |
| MSKU 利润 | `POST /bd/profit/report/open/report/msku/list` | 日维度单次不超过 31 天；90 天必须分段且保留原分段 | [MSKU 利润](https://apidoc.lingxing.com/docs/Finance/bdMSKU.md) |
| FBA 库存 | `POST /basicOpen/openapi/storage/fbaWarehouseDetail` | 必须限制 sid；只读取数量和成本字段 | [FBA 库存](https://apidoc.lingxing.com/docs/Warehouse/FBAStock_v2.md) |
| SP 广告活动报告 | `POST /pb/openapi/newad/spCampaignReports` | 必须指定 sid/profile、报告日期和分页；不得调用广告管理接口 | [SP 活动报告](https://apidoc.lingxing.com/docs/newAd/report/spCampaignReports.md) |
| 买家之声 | `POST /basicOpen/customerService/voiceOfBuyer/list` | 仅查询退货/不满意原因与比率，不执行售后动作 | [买家之声](https://apidoc.lingxing.com/docs/Service/voiceOfBuyerList.md) |
| 领星预测基线 | `POST /erp/sc/routing/fbaSug/asin/getDailySalesInfoFeature` | 只保存为外部预测基线，不当作实际结果 | [未来销量和库存预测](https://apidoc.lingxing.com/docs/FBASug/DailySalesInfoFeatureASIN.md) |

白名单之外一律拒绝，尤其是名称或文档含“创建、修改、编辑、更新、删除、作废、重算、提交、发货、调价、刊登、上传”的接口。新增只读接口必须逐项审计业务效果、输入范围和返回字段，不能使用 `/bd/*`、`/pb/*` 等路径通配授权。

## 3. 90 天历史数据不是预测

`最近 90 天销量/利润`回答的是“已经发生了什么”，不能证明“未来 90 天会发生什么”。产品表现接口允许单次查询不超过 92 天，因此它适合历史回看；这只是查询窗口能力，不是预测能力。[产品表现时间窗口](https://apidoc.lingxing.com/docs/Statistics/AsinListNew.md)

严禁以下表述：

- “查了最近 90 天，所以已经验证未来 90 天预测准确”；
- “历史毛利率就是新品未来毛利率”；
- “领星补货建议就是本项目预测的真实答案”。

有效的预测验证必须形成两个不可变时间点：

1. **T0 预测快照**：在做出推荐时保存候选、预测区间、预测销量/毛利/库存、公式、假设、数据窗口、来源和生成时间；
2. **T+90 实际快照**：90 天后从领星拉取相同 seller_id、站点、ASIN/MSKU、币种和口径的实际销量、利润、广告、退货和库存数据；
3. **误差计算**：分别计算销量误差、毛利误差、缺货天数、广告依赖和退货风险，不用一个总分掩盖单项失真；
4. **决策回写**：预测偏差和实际经营结果写入决策日志，经 `profile-update` 生成候选规则，仍需人工确认后才能影响下一轮排序。

领星补货建议接口公开提供未来销量和库存预测并返回按天数据，可作为 `external_forecast_baseline=lingxing` 保存；它不能替代 T+90 实际结果，也不能在缺少生成时间和当时参数时用于事后声称预测准确。[补货建议预测接口](https://apidoc.lingxing.com/docs/FBASug/DailySalesInfoFeatureASIN.md)

## 4. 字段映射

| 字段组 | 必须保留 | 进入决策的边界 |
|---|---|---|
| 身份与范围 | `seller_id`、`account_scope_id`、platform、market、sid 本地映射、ASIN、MSKU、SKU | 不保存真实店铺名；不得跨 seller_id 合并 |
| 时间与口径 | `collected_at`、`data_window`、站点时区、币种、汇率口径、订单状态、汇总维度 | 缺任一项时不得进行跨期比较 |
| 销售 | 销量、订单量、销售额、净销售额、均价 | 只代表该卖家经营历史，不产生全市场需求分 |
| 利润 | 采购成本、头程成本、其他成本、平台费、广告费、毛利润、毛利率、ROI | 保存领星字段名和计算口径；成本不全时只能写 `known_cost_margin` |
| 库存 | FBA 可售、预留、在途、不可售、可售天数、缺货天数 | 只影响 capability_fit、cashflow 和 risk |
| 广告 | 展示、点击、花费、广告销售/订单、CPC、ACoS、TACoS、ROAS | 广告归因窗口必须明确；不把广告数据外推到全市场 |
| 售后 | 退款/退货量与比率、NCX、不满意原因、评分 | 仅在明确 ASIN/MSKU 和时间窗口时进入风险验证 |
| 外部预测基线 | provider、generated_at、horizon、预测销量、预测库存、参数/版本 | 永远和 `actual` 分开存储，未知参数写 `unknown` |
| 溯源 | source_id、source_type、locator、request_id、接口/报表名称、原始文件 SHA-256 | 每个事实可回指；密钥和认证头不得进入 locator |

## 5. 已确认与待商务确认

### 已确认

- OpenAPI 可由超级管理员在开放接口后台获取 AppID/AppSecret，并要求公网 IP 白名单；官方提示凭证可访问企业数据。[API 信息与配置](https://apidoc.lingxing.com/docs/Guidance/AppID.md)
- AppID 存在接口权限、启停和有效期控制；权限不足会返回对应错误。[OpenAPI 常见问题](https://apidoc.lingxing.com/docs/Guidance/QA.md)
- 官方 MCP 仅限付费用户，查询范围继承当前账号权限，URL 与 X-Mcp-Key 缺一不可。[领星 MCP](https://www.lingxing.com/help/article/mcp)
- 自定义报表、利润报表和库存报表均有官方导出能力。[自定义报表](https://www.lingxing.com/help/article/customReport)、[利润报表](https://www.lingxing.com/help/article/ProfitStatementnew1)、[库存报表](https://www.lingxing.com/help/article/stockReport-local)

### 待商务或实施顾问书面确认

- 当前卖家套餐是否包含 MCP、上述 OpenAPI 接口及全部所需字段；
- OpenAPI 的费用、审核时间、调用配额和是否提供测试企业/沙箱；
- 能否为独立 AppID 精确限制到指定店铺、指定查询接口和指定字段；公开文档说明存在接口权限，但同时警告企业凭证可访问企业数据；
- 利润、广告、订单和库存数据的实际历史保留期限及补数规则；
- 接口字段、报表计算口径或 MCP Tool 变更时是否提供版本通知；
- 数据处理、跨境传输、日志留存和账号停用后的删除机制。

未获得确认前，对应项在报告中写“需人工核实”，不得自行假设套餐、费用或权限边界。

## 6. 上线验收

领星适配器只有同时通过以下项目才能标记为 `live_verified=true`：

1. 专用子账号只看得到测试卖家授权的店铺、Listing、仓库和必要字段；
2. MCP 实际工具清单或 OpenAPI 路径与本文件白名单逐项匹配，写工具调用数为 0；
3. 真实密钥仅来自环境变量或本地密钥管理器，仓库扫描无 URL、Token、AppSecret 和认证头；
4. 一个测试 ASIN/MSKU 的销量、利润、库存和广告查询均返回站点、日期、币种与 request_id，缺失字段显式记录；
5. 导出文件与 API/MCP 的相同口径抽样核对通过；差异被记录而不是自动平均；
6. 90 天利润查询按官方限制拆成不超过 31 天的原始分段，聚合公式可复算；产品表现窗口不超过 92 天；
7. 每个批次符合 `candidate-batch.schema.json`，并能离线重放合成 fixture；
8. 两个 seller_id 并发运行时，原始目录、缓存、日志和报告无交叉；
9. 回测报告明确区分 `forecast_snapshot`、`external_forecast_baseline` 与 `actual_snapshot`；无 T0 快照时不得报告预测准确率；
10. 禁用任一写能力的负向测试通过，最终审计记录 `write_operations_invoked=[]`。
