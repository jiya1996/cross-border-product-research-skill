# 虎步 RPA 受控报表投递边界

核验日期：2026-07-12。

虎步在本项目中的角色固定为 `collection_only`：它只负责把原系统已经存在的报表投递到卖家隔离目录，不拥有报表中的事实，也不参与选品打分和最终决策。

例如，虎步下载 Amazon Ads 报表时应记录：

- `provider=amazon_ads`
- `collector=hubu_rpa`
- `source_role=seller_first_party_data`
- `source_type=xlsx|csv`

不得写成 `provider=hubu_rpa`，也不得因为虎步完成了搬运就提升事实等级。

## 1. 为什么不能把通用虎步能力直接交给 Agent

虎步官方 API 的工作方式是创建 RPA 执行计划、运行任务，再查询执行结果；多数结果以 Excel、CSV 等文件输出。它不是一个纯查询数据库。[API 入门指南](https://support.huburpa.com/cc8e/bc56/6708)

同一产品也公开提供自动提现、广告自动操作等 UI 写能力，并支持定制选品逻辑、广告分析、财务统计和跨系统操作。[虎步 RPA 简介](https://support.huburpa.com/7d8f/806d) 官方帮助目录还列有创建促销、广告调控、自动投放、上架和消息回复等配置模板。[虎步帮助中心](https://support.huburpa.com/designer)

因此：

- 不向 `product-research` 暴露通用“创建 RPA 任务”工具；
- 不允许模型提交任意 `rpaId`、`runWith`、店铺或计划周期；
- 不使用名称模糊匹配决定是否安全；
- 只有经过人工动作审计、固定版本和固定参数的下载型 RPA 才能进入本地白名单。

## 2. 固定架构

```text
人工审核并登记下载型 RPA
          ↓
受控采集器按本地白名单提交任务
          ↓
虎步只执行指定店铺/站点的报表下载
          ↓
隔离区校验文件、元数据与 SHA-256
          ↓
reports/{seller_id}/raw/{batch_id}/
          ↓
适配器以 verified_import 读取
          ↓
product-research 只分析，不触发 RPA
```

虎步官方自用 API 需要 BOSS 账号在“管理设置 → API 管理 → API 自用申请”开通包含创建任务的接口，并配置调用方 IP 白名单；AppID/AppSecret 用于换取 AppToken。[企业自用 API 对接流程](https://support.huburpa.com/cc8e/bc56/75f7) 由于这组凭证具备创建任务能力，只能由隔离的采集器持有，不能写入仓库、报告或模型上下文。

## 3. RPA 白名单

仓库只提交结构示例 `config/hubu-rpa-allowlist.example.yaml`。真实白名单保存在本地安全配置中，不提交真实 RPA ID、店铺 ID、AppID、AppSecret 或 AppToken。

一个 RPA 只有满足全部条件才可启用：

1. `enabled=true` 前已有人工审核人和审核日期；
2. 从官方 RPA 详情读取准确的 ID、名称、参数、收费单位和输出类型；官方查询接口可以按 RPA ID 返回详情和运行参数。[查询 RPA 详情](https://support.huburpa.com/cc8e/4bc8/9fde)
3. 审核者实际查看其 UI 动作，确认业务效果只有下载/读取，不包含填写、提交、上传、修改、确认或付款；
4. 固定允许的卖家、店铺别名、站点和参数值，禁止 `ALL`/全部店铺；
5. 固定输出类型和字段最小集；
6. 记录已审核版本或可识别的版本信息；版本无法固定或发生变化时自动禁用；
7. 负向测试证明任意未登记 RPA ID、未登记参数、未登记站点都会在请求虎步之前被拒绝。

允许的业务效果只有：

- 生成既有平台报表；
- 下载既有报表文件；
- 读取页面上已有数据并保存为本地文件；
- 查询下载任务状态与结果。

永久拒绝的业务效果包括：

- 自动提现、付款或任何资金操作；
- 创建、启停、调价、调预算或修改广告；
- 上架、刊登、上传商品资料、创建促销或修改 Listing；
- 修改库存、采购、订单、物流、发货或履约；
- 催评、回复消息、联系买家或达人；
- 上传文件、填写表单后提交、确认弹窗或执行任意未审计 UI 动作；
- 由模型新建、修改、启用、停用、删除或重试周期计划。

虎步官方云任务指南明确说明任务既可能“获取数据”也可能“做操作”，并以自动提现为周期操作示例，因此不能把“运行 RPA”整体视为只读。[云任务使用指南](https://support.huburpa.com/)

## 4. 执行约束

受控采集器必须执行以下检查：

1. 调用前校验 `seller_id` 格式，只允许字母、数字、下划线和连字符；拒绝 `.`, `/`, `..`；
2. `seller_id` 必须映射到单一 `account_scope_id` 和显式站点清单；
3. `rpa_alias` 必须命中启用的本地白名单，外部请求不能直接提供 `rpa_id`；
4. 运行参数只能从白名单模板生成，拒绝额外参数和自由文本覆盖；
5. 单次任务只允许一个 seller_id，不跨卖家合并；
6. Agent 不创建周期计划；如确需定时采集，由人工在独立运维层预先配置并审计；
7. 只允许查询任务状态、查询结果和下载文件；不得使用计划修改、启停、删除或任意写型 RPA；
8. 下载完成后立即进行哈希、类型、大小、字段和卖家归属校验，校验失败的文件留在隔离区且不进入分析；
9. 下载 URL 不写入长期报告。官方结果接口说明成功文件的下载地址有效三天，再次查询会刷新地址。[任务执行结果](https://support.huburpa.com/cc8e/4bc8/42de)

官方说明 RPA 会受到网络、设备和店铺状态影响，无法保证 100% 成功。[API 入门指南](https://support.huburpa.com/cc8e/bc56/6708) 因此失败、空文件、重复结果和重试结果都不能被当作“零销量”或“无风险”；必须标记采集状态并等待人工处置。

## 5. 文件与清单元数据

每个原始文件旁必须保存一个同名 manifest。最少字段如下：

| 字段 | 要求 |
|---|---|
| `schema_version` | 当前采集清单版本 |
| `batch_id` | 本次采集唯一 ID |
| `seller_id` | 与目录和任务 seller_id 完全一致 |
| `account_scope_id` | 不可反推真实店铺的本地别名 |
| `platform`、`market` | 原平台与站点 |
| `original_provider` | 如 `amazon_ads`、`amazon_seller_central` |
| `collector` | 固定为 `hubu_rpa` |
| `rpa_alias` | 本地白名单别名 |
| `rpa_id`、`rpa_version` | 仅保存在私有 raw 元数据；公开报告必须脱敏 |
| `plan_id`、`task_id`、`task_record_id` | 便于审计重复和重试；公开报告必须脱敏 |
| `requested_at`、`collected_at` | ISO 8601 时间 |
| `data_window` | 报表覆盖的开始/结束日期及站点时区 |
| `file_name`、`content_type`、`size_bytes` | 文件基本信息 |
| `sha256` | 64 位小写十六进制 SHA-256 |
| `row_count`、`column_names` | 解析后的结构校验 |
| `source_locator` | 报表类型与本地相对路径，不含临时下载 URL 和认证信息 |
| `read_only` | 必须为 `true` |
| `write_operations_invoked` | 必须为空数组 |
| `status` | `downloaded`、`verified`、`quarantined` 或 `failed` |
| `error_code`、`error_message` | 失败时记录；不得把失败转换为事实值 |

虎步结果 API 会返回店铺、站点、RPA、任务、结果类型、报表时间窗口和下载地址，可用于构造上述私有清单。[任务执行结果字段](https://support.huburpa.com/cc8e/4bc8/42de)

## 6. 文件布局与卖家隔离

```text
reports/{seller_id}/raw/{batch_id}/
├── source-file.csv
├── source-file.csv.manifest.json
└── collection-audit.json
```

规则：

- 路径中的 seller_id 必须与 manifest、调用参数和任务映射一致；
- 禁止把多个卖家的原始文件放入同一 batch；
- 禁止通过软链接、`..` 或绝对路径逃逸卖家目录；
- 原始财务、订单、广告和买家相关文件不得提交公开仓库；
- 合并报表前逐文件验证 seller_id、站点、窗口和哈希；
- 即使虎步支持多店铺批量与文件合并，本项目也只允许在同一 seller_id 内合并。虎步官方说明支持多店铺下载和部分文件合并，但该能力不改变本项目的隔离要求。[云任务使用指南](https://support.huburpa.com/)

## 7. 进入选品流程

只有 `status=verified` 的文件才能进入适配器：

1. 将数据转换为 `candidate-batch.schema.json`；
2. `mode=verified_import`；
3. `collector=hubu_rpa`，保留原始 provider；
4. `source_role` 由原始来源决定，虎步自身始终为 `collection_only`；
5. 缺失字段写入 `missing_fields`，采集失败不得填 0；
6. 数据只用于当前卖家的历史经营验证，不外推全市场；
7. `product-research` 只读取落地文件，不回调虎步创建或重试任务。

## 8. 已确认与待商务确认

### 已确认

- 自用 API 由 BOSS 账号申请，使用 AppID/AppSecret 换取 AppToken，并要求 IP 白名单。[企业自用 API 对接](https://support.huburpa.com/cc8e/bc56/75f7)
- API 可以创建 RPA 计划、执行任务并获取 Excel/CSV 等结果文件。[API 入门指南](https://support.huburpa.com/cc8e/bc56/6708)
- 官方 RPA 详情接口返回当前应用有权限的 RPA、参数和收费信息。[查询 RPA 详情](https://support.huburpa.com/cc8e/4bc8/9fde)
- 云任务按文件或成功次数等方式计费，具体价格以应用市场详情为准。[官方价格表](https://support.huburpa.com/7d8f/dcd7)
- 虎步同时包含数据下载和平台写操作，不能整包授权。[虎步简介](https://support.huburpa.com/7d8f/806d)

### 待商务或技术支持书面确认

- 自用 API 应用能否只授权指定 RPA ID，而不是开放全部可执行 RPA；
- 能否提供 RPA 版本号、动作清单、版本变更通知和固定版本能力；
- API 开通费用、审核时长、调用限额、数据留存与删除机制；
- 是否能在企业层彻底禁用自动提现、广告、上架、促销、消息、订单和库存等写型 RPA；
- 定制 RPA 的动作验收、源码或知识产权归属、维护方式和安全责任；
- 文件下载、回调、临时 URL 和运行日志的安全与保留周期。

未书面确认前，本项目仍按“本地精确白名单 + 外部隔离采集器 + 默认拒绝”执行。

## 9. 验收标准

1. 示例配置可解析，且默认 `enabled=false`、`rpa_id=null`、允许站点为空；
2. 无本地真实白名单时，所有任务在访问虎步前被拒绝；
3. 未登记 RPA ID、额外参数、`ALL` 店铺、未登记站点和跨 seller_id 请求全部拒绝；
4. 用合成 fixture 完成一次下载、SHA-256、manifest 和 verified import 流程；
5. 篡改任意文件字节后哈希校验失败，文件不能进入分析；
6. 两个 seller_id 并发采集时目录、manifest、缓存和报告不交叉；
7. 采集失败、超时或空文件不会生成销量为 0 的事实；
8. 来源审计保持 `original_provider` 与 `collector=hubu_rpa` 分离；
9. 真实 smoke test 的 `write_operations_invoked=[]`，平台业务状态前后无变化；
10. 仓库扫描不含 AppID、AppSecret、AppToken、真实 RPA ID、店铺 ID、Cookie、临时下载 URL 或买家敏感原始数据。
