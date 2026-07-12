# 真实卖家的私有部署与 Git 审计

## 先说结论

本公开仓库为了防止商业数据泄漏，默认忽略真实 `sellers/*` 和 `reports/*`，只跟踪 `_example` 虚构数据。因此：

- 公开仓库中的真实卖家文件**不会**被 Git 记录；
- “画像、SOP、决策和规则可 diff/可回滚/可审计”只有在真实卖家目录进入**私有 Git 仓库**后才成立；
- 仅在本地文件夹中存在、但 `git ls-files` 看不到的文件，不得宣称有 Git 审计轨迹。

## 推荐部署方式

1. 保留本公开仓库作为无真实数据的 Skill/代码源。
2. 为生产使用创建受限访问的私有 fork 或独立私有仓库，仅授权实际运营人员。
3. 只在私有仓库内调整 `.gitignore`，显式纳入已批准卖家的：
   - `sellers/{seller_id}/profile.yaml`
   - `sellers/{seller_id}/sop.md`
   - `sellers/{seller_id}/decisions/*.md`
   - 已脱敏的 `reports/{seller_id}/*.md`
4. 即使在私有仓库，也不提交 `.env`、Token、Cookie、真实 MCP 地址、未脱敏原始报表或 `reports/{seller_id}/raw/`。
5. 用 `git ls-files sellers/{seller_id} reports/{seller_id}` 核对应跟踪清单；只有命令实际返回文件时，该卖家才具备 Git 变更历史。

## 私有仓库忽略策略示意

以下规则只是私有 fork 的示意，不要提交回本公开仓库：

```gitignore
# 先继承默认隔离，再仅放行已批准 seller_id。
!sellers/approved-seller/
!sellers/approved-seller/**
!reports/approved-seller/
!reports/approved-seller/*.md

# 原始导出和凭证始终不入 Git。
reports/approved-seller/raw/
```

放行前使用虚构目录验证 ignore 效果，并对首次提交做人工敏感信息审查。

## learned 规则的审计表达

- `proposed` 未生效；只有经过显式确认迁移的 `active` 规则参与打分和排序。硬过滤仍只由 `constraints` 和 SOP 决定。
- `confirmed_by` / `revoked_by` 是命令调用者填写的自报审计字段，不能证明真实身份或授权。生产环境必须用仓库权限、受保护分支、Git review 或独立操作者命令落实人工审批；一键合成视频只模拟这一步。
- `revoked / expired / superseded` 不参与推荐，但必须保留在 profile 和 Git 历史中。
- 推荐报告分别列出“已应用 active 规则”与“未应用规则”。后者至少显示 `rule_id`、status、scope 以及撤销/过期/取代原因。
- 撤销不等于删除。需要恢复旧思路时，创建新 revision 并通过 `supersedes` 建立关系，不篡改历史 evidence。

## 还需要宿主平台能力

Git commit 能证明文件如何变化，但不能单独证明谁读取过商业数据。生产部署还应开启代码托管平台的私有仓库访问控制、审计日志、多因素认证和最小权限。
