# MCP 接入说明

本项目优先使用卖家精灵 MCP 与 SIF MCP 作为 Amazon 只读市场/关键词/流量数据源，Sorftime MCP 可作为替代或交叉验证来源；领星 MCP 只用于当前卖家授权范围内的历史经营查询。MCP 禁止调用任何平台、广告、库存、订单或自定义指标写操作。

## 环境变量约定

在本地 shell 或安全的环境变量管理器中设置。API Key 是 Codex MCP 启动所需；URL 变量可供适配器脚本或其他客户端复用：

```bash
export SELLERSPRITE_MCP_URL="https://example.invalid/mcp"
export SELLERSPRITE_MCP_API_KEY="replace-with-local-secret"
```

- `SELLERSPRITE_MCP_URL`：卖家精灵 MCP 的 Streamable HTTP 地址。真实地址不要提交到仓库。
- `SELLERSPRITE_MCP_API_KEY`：卖家精灵 MCP 的访问令牌。必须只存在于本地环境变量或安全密钥管理器中。

如果使用 Sorftime MCP，可采用同样模式增加：

```bash
export SORFTIME_MCP_URL="https://example.invalid/mcp"
export SORFTIME_MCP_API_KEY="replace-with-local-secret"
```

如果使用 SIF MCP，采用独立变量，避免和其他提供方混用：

```bash
export SIF_MCP_URL="https://example.invalid/mcp"
export SIF_MCP_API_KEY="replace-with-local-secret"
```

如果试点领星官方 MCP，使用独立子账号和独立环境变量：

```bash
export LINGXING_MCP_URL="https://example.invalid/mcp"
export LINGXING_MCP_KEY="replace-with-local-secret"
```

领星官方使用 `X-Mcp-Key`，不能把企业主密钥写进仓库或静态 header。当前仓库未配置也未验证该连接；权限、套餐和店铺范围仍须以试点账号及领星官方说明为准。

## Codex 配置方式

Codex 的 MCP 配置位于 `~/.codex/config.toml`，也可以在可信项目中使用项目级 `.codex/config.toml`。本仓库不提交真实 MCP 配置文件，避免泄露地址或密钥。

Streamable HTTP MCP server 在 Codex 中使用 `url` 配置；Bearer Token 使用 `bearer_token_env_var`，自定义请求头使用 `env_http_headers` 指向环境变量，避免把密钥写入配置。

本地配置示例：

```toml
[mcp_servers.sellersprite]
url = "https://example.invalid/mcp"
bearer_token_env_var = "SELLERSPRITE_MCP_API_KEY"
startup_timeout_sec = 20
tool_timeout_sec = 120
enabled = true
default_tools_approval_mode = "prompt"
```

配置后，在 Codex 中使用 `/mcp` 检查服务器是否可用。

领星自定义请求头示例；`enabled_tools` 必须先查看试点账号实际返回工具后再填，不能照抄猜测名称：

```toml
[mcp_servers.lingxing]
url = "https://example.invalid/mcp"
env_http_headers = { "X-Mcp-Key" = "LINGXING_MCP_KEY" }
enabled = true
default_tools_approval_mode = "prompt"
```

卖家精灵与 SIF 的公开产品说明只能证明它们提供 MCP 能力，不代表本地已经接入。真实连接地址仍只写在本地配置或环境变量，不提交仓库。

## 三层就绪检查

先运行仓库自检：

```bash
python3 scripts/check_data_access.py
python3 scripts/check_data_access.py --json
```

脚本只检查环境变量和 Codex 配置是否存在，不输出值。它不会把“有配置”误报成“已查询成功”。真实接入必须连续通过三层：

1. **凭证配置就绪**：`[mcp_servers.*]` 中存在 URL 与 `bearer_token_env_var` 或 `env_http_headers` 绑定，且对应密钥环境变量存在；
2. **工具能力就绪**：在 `/mcp` 中能看到实际只读工具名，并确认没有启用上架、调价、广告、库存等写工具；
3. **最小查询就绪**：用一个公开关键词或测试 ASIN 跑一次只读查询，记录返回字段、站点、采集日期和缺失字段，但不把敏感原始响应提交仓库。

只有第 3 层通过后才可以在报告中写“live MCP 已验证”。当前仓库的合成演示就绪不代表真实 MCP 已接入。

## 只读工具策略

接入后先查看 MCP 暴露的工具清单，只启用读取、搜索、分析类工具。按 `references/data-sources/tool-role-registry.json` 做能力级白名单，不能因为某个品牌有选品能力就整包授权。若 MCP 暴露催评、登录店铺、上架、调价、广告、库存、订单、提现、Listing 或履约写操作，必须在本地配置中禁用或不要启用。

示例（工具名需按实际 MCP 返回值调整）：

```toml
[mcp_servers.sellersprite]
url = "https://example.invalid/mcp"
bearer_token_env_var = "SELLERSPRITE_MCP_API_KEY"
enabled_tools = ["search", "read", "analyze"]
disabled_tools = ["create_listing", "update_price", "update_ads", "update_inventory"]
```

不要直接照抄示例中的 `enabled_tools` 名称。先查看服务端实际工具清单，再建立“服务端工具名 → 来源角色 → `references/data-sources/adapter-contract.md` 字段 → 允许评分维度”的映射。映射未完成时，查询结果只能作为原始证据，不能直接进入自动评分。

## 数据归一化

所有 MCP 结果必须转换为 `references/schemas/candidate-batch.schema.json`，至少保留：

- `seller_id`、平台、站点和采集时间；
- 来源 provider、查询 locator 和事实适用范围；
- 来源角色、实际工具名、允许评分维度、数据窗口与指标口径；
- 若经过聚合、RPA 或翻译，分别记录 original_provider、collector 和 transformations；
- 候选稳定 ID；
- 每个事实字段的 `source_id`；
- 缺失字段和冲突字段；
- 是否为合成数据。

原始响应建议写入 `reports/{seller_id}/raw/{batch_id}/`，且该目录不得进入公开仓库。

## 密钥纪律

- 不要把真实 URL、API Key、Bearer Token、Cookie 或后台导出凭证写入仓库。
- 不要把 `.env` 文件提交到仓库。
- 报告中不得输出密钥、完整令牌或可复用的认证头。
- 如果 MCP 查询得到事实性费用、税费或合规要求，报告必须标注来源；若 `references/` 未覆盖，则输出"需人工核实"。
