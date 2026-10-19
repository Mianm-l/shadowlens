# ShadowLens (影子透镜) - 企业级 Oracle MCP 只读穿透微服务

> **零侵入 · 绝对只读安全 · 免装 Oracle 客户端 · 智能跨库穿透与对账**

ShadowLens 是专门为**政企与大中型企业老旧系统（致远协同 OA、用友 ERP/NCC、若依供应链等）**打造的私有化只读 MCP (Model Context Protocol) 微服务代理。

它帮助 AI Agent 在**完全不侵入生产代码、不依赖老系统排期开接口、零写操作风险**的前提下，通过语义字典外挂与受控查询原语，实现自然语言驱动的跨表数据穿透、审批卡点追溯与智能双向对账。

---

## 🌟 核心特性

1. **纯 Python Thin 模式，免装 Oracle Instant Client**
   - 彻底摒弃传统配置 `oracle-instantclient-basic`、设置 `LD_LIBRARY_PATH` / `OCI` 动态库的繁重工作。
   - 基于纯 Python TCP/IP Socket 直连 Oracle 11gR2 / 12c / 18c / 19c / 21c / 23c，极致轻量，单容器开箱即用。
2. **多层只读与注入拦截防线**
   - **连接层**：只读账号连接 + `SET TRANSACTION READ ONLY` 会话锁；
   - **应用层**：SQL 语法树严格校验，彻底阻断任何 `INSERT/UPDATE/DELETE/DROP/ALTER` 及存储过程调用；
   - **熔断防线**：单次查询默认 5s 强制超时，默认行数严格截断（防笛卡尔积打垮数据库）。
3. **外挂语义字典（Semantic Overlay）**
   - 通过 `config/schema-dictionary.yaml` 补充中文字段名、业务枚举（如 `0:草稿, 1:审批中, 2:已生效`）与关联链路，解决老旧系统字段命名反人类、无注释的顽疾。
4. **隐私与涉密动态脱敏（Automatic Masking）**
   - 手机号、身份证号、银行卡号、金额等级、密码敏感词自动打码（如 `138****5678`、`110101********1234`），满足国企与涉密数据合规要求。
5. **开箱即用的高保真仿真数据集（Dry-Run Mode）**
   - 内置离线高保真仿真业务数据集，在内网数据库未联通或离线演示时自动无缝接管，开发与测试零阻力。

---

## 📁 目录结构

```text
shadowlens/
├── config/
│   ├── config.yaml               # 数据库连接、安全阈值与微服务端口配置
│   ├── schema-dictionary.yaml    # 业务模块、表名、中文字段及枚举字典映射
│   └── reconciliation-rules.yaml # 跨表双向对账规则配置
├── docs/
│   └── ideas/
│       └── shadowlens-mcp.md     # 固化的项目论证与架构规格 One-Pager
├── src/
│   ├── config.py                 # 配置加载器
│   ├── server.py                 # FastMCP 服务端 (支持 SSE 与 Stdio)
│   ├── db/
│   │   ├── oracle_pool.py        # Oracle Thin Mode 连接池与只读执行器
│   │   └── mock_data.py          # 高保真离线仿真数据集
│   ├── security/
│   │   ├── sql_validator.py      # SQL 严格只读白名单校验器
│   │   └── data_masker.py        # 敏感数据动态脱敏引擎
│   └── services/
│       ├── schema_service.py     # 字典元数据检索服务
│       ├── query_service.py      # 受控参数化查询与枚举转换
│       ├── reconciler.py         # 跨表智能对账引擎
│       └── workflow_monitor.py   # 审批流长超时卡点监控
├── tests/
│   └── test_shadowlens.py        # 完备自动化测试套件
├── Dockerfile                    # 私有化轻量部署镜像
├── docker-compose.yml            # 客户内网单机一键启停编排
└── requirements.txt              # 核心依赖清单
```

---

## 🚀 客户内网私有化快速部署

### 方式一：Docker Compose 一键部署（推荐）

1. **修改数据库配置**：
   编辑 `docker-compose.yml` 中的环境变量，填入客户内网 Oracle 的只读用户与 DSN：
   ```yaml
   environment:
     - ORACLE_DSN=192.168.1.100:1521/ORCLPDB1
     - ORACLE_USER=SHADOW_RO
     - ORACLE_PASSWORD=ReadOnlyPassword#2026
     - SHADOWLENS_DRY_RUN=false
   ```
2. **启动服务**：
   ```bash
   docker compose up -d
   ```
3. **验证健康状态**：
   内网微服务将在 `http://<服务器IP>:8000/sse` 暴露标准 MCP SSE 端点。

---

### 方式二：原生 Python 运行

```bash
# 1. 安装依赖 (Python 3.10+)
pip install -r requirements.txt

# 2. 运行自动化测试
python -m unittest tests/test_shadowlens.py

# 3. 启动内网 SSE 微服务 (监听 8000 端口)
python -m src.server --transport sse --host 0.0.0.0 --port 8000
```

---

## 🔌 客户端与 AI IDE 接入指引

### 1. Antigravity / Cursor / Cherry Studio / Claude 接入配置

在 AI Agent 客户端的 MCP 配置文件（如 `mcp_settings.json`）中添加 SSE 远程微服务配置：

```json
{
  "mcpServers": {
    "shadowlens-oracle": {
      "url": "http://192.168.1.50:8000/sse"
    }
  }
}
```

*注：若使用本地开发模式，亦可配置为 Stdio 命令行模式：*
```json
{
  "mcpServers": {
    "shadowlens-local": {
      "command": "python",
      "args": ["-m", "src.server", "--transport", "stdio"],
      "cwd": "/path/to/shadowlens"
    }
  }
}
```

---

## 🛠️ 暴露给 Agent 的核心 Tools 清单

| 工具名称 | 功能描述 | 典型触发 Prompt 示例 |
| :--- | :--- | :--- |
| `get_table_dictionary` | 检索表字典、字段中文定义、业务枚举与关联关系 | *"查一下采购管理模块有哪些表，订单状态枚举分别代表什么？"* |
| `query_audited_view` | 在受控白名单表/视图中按条件查询（带自动脱敏与枚举反显） | *"查询订单状态为已审批的所有采购订单，返回前 20 条"* |
| `list_reconciliation_rules` | 获取系统已预配置的跨表自动化对账规则清单 | *"系统支持哪些跨系统对账规则？"* |
| `reconcile_cross_tables` | 执行配置化跨表双向对账，检测漏单、金额不一致及异常状态 | *"执行采购单与入库验收对账，找出有差异的批次"* |
| `fetch_stuck_workflows` | 盘点协同 OA / 业务审批流中停留超时（默认 >48h）的卡点单据与当前责任人 | *"帮我查一下当前卡在审批节点超过 48 小时的协同公文有哪些？"* |
| `test_db_connection` | 检查内网 Oracle 数据库连通性、当前模式 (Thin Mode) 与网络延迟 | *"检查当前数据库连接状态"* |

---

## 🔒 安全合规白皮书摘要

- **零写权限**：只读账号 + `SET TRANSACTION READ ONLY` 物理级会话隔离；
- **防注入与防全表扫描**：所有查询经过 AST/正则表达式白名单二次过滤，禁止注释符逃逸，强制绑定参数化变量；
- **隐私保护**：脱敏引擎按规则对联系电话、身份证件、银行账户等自动加掩码，防止高密级数据在对话界面泄露。
