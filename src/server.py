import argparse
import json
import logging
import sys
from typing import Any, Dict, List, Optional
from mcp.server.fastmcp import FastMCP

from .config import load_config
from .db.oracle_pool import OraclePoolManager
from .services.query_service import QueryService
from .services.reconciler import ReconciliationService
from .services.schema_service import SchemaService
from .services.workflow_monitor import WorkflowMonitorService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger("shadowlens.server")

# 1. Load application config
app_cfg = load_config()

# 2. Initialize infrastructure & services
db_pool = OraclePoolManager(app_cfg.oracle, app_cfg.security)
schema_svc = SchemaService(app_cfg.paths.dictionary_file)
query_svc = QueryService(db_pool, schema_svc, mask_sensitive=app_cfg.security.mask_sensitive_data)
reconcile_svc = ReconciliationService(db_pool, schema_svc, app_cfg.paths.reconciliation_file)
wf_monitor = WorkflowMonitorService(db_pool, schema_svc)

# 3. Create FastMCP server
mcp = FastMCP(
    name=app_cfg.server.name,
    host=app_cfg.server.host,
    port=app_cfg.server.port
)

@mcp.tool()
def test_db_connection() -> str:
    """
    检查内网 Oracle 数据库连通性、当前模式 (Thin Mode / 仿真模式) 与网络延迟。
    """
    res = db_pool.test_connection()
    return json.dumps(res, ensure_ascii=False, indent=2)

@mcp.tool()
def get_table_dictionary(
    module_id: Optional[str] = None,
    table_name: Optional[str] = None,
    keyword: Optional[str] = None
) -> str:
    """
    检索指定业务模块或表名的数据字典、字段中文定义、业务枚举与关联关系。
    
    参数:
    - module_id: 模块ID (例如: 'procurement', 'finance', 'collaboration_oa')
    - table_name: 数据表名 (例如: 'CT_PURCHASE_ORDER', 'OA_COL_AFFAIR')
    - keyword: 搜索关键字 (例如: '供应商', '入库', '审批')
    """
    results = schema_svc.search_dictionary(module_id=module_id, table_name=table_name, keyword=keyword)
    return json.dumps(results, ensure_ascii=False, indent=2)

@mcp.tool()
def query_audited_view(
    table_name: str,
    filter_field: Optional[str] = None,
    filter_value: Optional[str] = None,
    limit: int = 50
) -> str:
    """
    在受控白名单表/视图中按条件查询数据（带自动脱敏、枚举反显与超时熔断）。
    
    参数:
    - table_name: 必须在白名单内的表名 (例如: 'CT_PURCHASE_ORDER')
    - filter_field: 筛选字段名 (可选, 例如: 'ORDER_STATUS' 或 'SUPPLIER_NAME')
    - filter_value: 筛选值 (可选, 例如: '2')
    - limit: 最多返回行数 (默认50，最大200)
    """
    filters = {}
    if filter_field and filter_value is not None:
        filters[filter_field] = filter_value

    try:
        res = query_svc.query_audited_view(
            table_name=table_name,
            filter_dict=filters,
            limit=min(limit, app_cfg.security.max_rows_per_query)
        )
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)

@mcp.tool()
def list_reconciliation_rules() -> str:
    """
    获取当前已配置的全部跨表自动化对账规则清单。
    """
    rules = reconcile_svc.list_rules()
    return json.dumps(rules, ensure_ascii=False, indent=2)

@mcp.tool()
def reconcile_cross_tables(rule_id: str, max_check: int = 50) -> str:
    """
    执行配置化跨表双向对账，检测漏单、金额不一致及异常状态。
    
    参数:
    - rule_id: 对账规则ID (例如: 'procurement_vs_receiving' 或 'receiving_vs_voucher')
    - max_check: 最大分析记录数 (默认50)
    """
    try:
        res = reconcile_svc.reconcile(rule_id=rule_id, max_check=max_check)
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)

@mcp.tool()
def fetch_stuck_workflows(min_stuck_hours: int = 48, limit: int = 50) -> str:
    """
    盘点协同 OA / 业务审批流中停留超过指定时长的卡点待办与当前责任人（带手机号脱敏）。
    
    参数:
    - min_stuck_hours: 停滞超时阈值(小时)，默认 48 小时
    - limit: 最大返回数量 (默认 50)
    """
    res = wf_monitor.find_stuck_workflows(min_stuck_hours=min_stuck_hours, limit=limit)
    return json.dumps(res, ensure_ascii=False, indent=2)

def main():
    parser = argparse.ArgumentParser(description="ShadowLens Oracle MCP Microservice")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default=app_cfg.server.transport,
        help="MCP 传输协议: 'sse' (内网微服务模式) 或 'stdio' (命令行管道模式)"
    )
    parser.add_argument("--host", default=app_cfg.server.host, help="绑定 IP 地址")
    parser.add_argument("--port", type=int, default=app_cfg.server.port, help="监听端口")
    args = parser.parse_args()

    mcp.settings.host = args.host
    mcp.settings.port = args.port

    logger.info("=" * 65)
    logger.info("  ShadowLens Enterprise Oracle MCP Microservice v1.0.0")
    logger.info(f"  Transport: {args.transport.upper()}")
    if args.transport == "sse":
        logger.info(f"  Intranet SSE Endpoint: http://{args.host}:{args.port}/sse")
    logger.info(f"  Oracle DB Mode: {'Thin Mode (Mock Active)' if db_pool.is_mock_active else 'Thin Mode (Physical Connected)'}")
    logger.info("=" * 65)

    mcp.run(transport=args.transport)

if __name__ == "__main__":
    main()
