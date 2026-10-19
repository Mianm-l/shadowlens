import logging
import time
from typing import Any, Dict, List, Optional, Tuple
import oracledb

from ..config import OracleConfig, SecurityConfig
from ..security.sql_validator import SQLValidator, SQLValidationError

logger = logging.getLogger("shadowlens.db")

class OraclePoolManager:
    def __init__(self, oracle_cfg: OracleConfig, sec_cfg: SecurityConfig):
        self.cfg = oracle_cfg
        self.sec = sec_cfg
        self.pool: Optional[oracledb.ConnectionPool] = None
        self.is_mock_active = False
        self.validator = SQLValidator(allowed_tables=sec_cfg.allowed_tables)
        self._init_pool()

    def _init_pool(self) -> None:
        """Initialize oracledb connection pool in Thin Mode."""
        if self.cfg.dsn.lower().startswith("mock"):
            logger.info("DSN 设置为 mock，直接启用内置高保真业务仿真只读数据集 (Dry-Run Mock Engine)")
            self.is_mock_active = True
            return

        logger.info(f"正在以 Thin Mode 初始化 Oracle 连接池 (DSN: {self.cfg.dsn})...")
        try:
            # Thin mode is default in python-oracledb
            self.pool = oracledb.create_pool(
                user=self.cfg.user,
                password=self.cfg.password,
                dsn=self.cfg.dsn,
                min=self.cfg.min_pool,
                max=self.cfg.max_pool,
                increment=1,
                timeout=self.cfg.timeout_seconds,
                tcp_connect_timeout=2.0
            )
            # Test acquire a connection to verify physical reachability
            with self.pool.acquire() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1 FROM DUAL")
                    cur.fetchone()
            self.is_mock_active = False
            logger.info("Oracle 物理只读连接池初始化并验证成功！")
        except Exception as e:
            if self.cfg.dry_run_mode:
                logger.warning(
                    f"无法直连内网 Oracle ({e})，已按配置平滑切换至内置高保真业务仿真只读数据集 (Dry-Run Mock Engine)"
                )
                self.is_mock_active = True
                self.pool = None
            else:
                logger.error(f"Oracle 数据库连接池初始化失败: {e}")
                raise e

    def execute_query(
        self, sql: str, params: Optional[Dict[str, Any]] = None, max_rows: Optional[int] = None
    ) -> Tuple[List[Dict[str, Any]], float]:
        """
        Execute read-only query safely with timeout and max row limits.
        Returns: (records, execution_time_ms)
        """
        # 1. SQL security validation
        self.validator.validate_select_only(sql)

        limit = max_rows or self.sec.max_rows_per_query
        start_time = time.perf_counter()

        if self.is_mock_active or self.pool is None:
            records = self._execute_mock_query(sql, params, limit)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return records, duration_ms

        try:
            with self.pool.acquire() as conn:
                if self.sec.force_read_only_session:
                    try:
                        with conn.cursor() as cur:
                            cur.execute("SET TRANSACTION READ ONLY")
                    except Exception as e:
                        logger.debug(f"设置 READ ONLY 事务失败 (若已设置可忽略): {e}")

                with conn.cursor() as cursor:
                    if params:
                        cursor.execute(sql, params)
                    else:
                        cursor.execute(sql)

                    columns = [col[0] for col in cursor.description] if cursor.description else []
                    rows = cursor.fetchmany(limit)
                    records = [dict(zip(columns, row)) for row in rows]

            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return records, duration_ms
        except Exception as e:
            if self.cfg.dry_run_mode:
                logger.warning(f"物理 Oracle 连接发生异常 ({e})，已自动降级至仿真数据集")
                self.is_mock_active = True
                records = self._execute_mock_query(sql, params, limit)
                duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                return records, duration_ms
            raise e

    def test_connection(self) -> Dict[str, Any]:
        """Test database connection health."""
        if self.is_mock_active:
            return {
                "status": "MOCK_ACTIVE",
                "message": "Oracle 处于内网仿真模式 (Dry-Run Mock)，全部模拟业务数据就绪",
                "thin_mode": oracledb.is_thin_mode(),
                "dsn": self.cfg.dsn,
                "latency_ms": 0.5
            }

        start = time.perf_counter()
        try:
            assert self.pool is not None
            with self.pool.acquire() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1 FROM DUAL")
                    cursor.fetchone()
            latency = round((time.perf_counter() - start) * 1000, 2)
            return {
                "status": "CONNECTED",
                "message": "内网 Oracle 物理连接正常",
                "thin_mode": oracledb.is_thin_mode(),
                "dsn": self.cfg.dsn,
                "latency_ms": latency
            }
        except Exception as e:
            return {
                "status": "ERROR",
                "message": str(e),
                "thin_mode": oracledb.is_thin_mode(),
                "dsn": self.cfg.dsn
            }

    def _execute_mock_query(
        self, sql: str, params: Optional[Dict[str, Any]], limit: int
    ) -> List[Dict[str, Any]]:
        """High fidelity mock enterprise dataset for offline testing."""
        from .mock_data import MOCK_DATASET
        upper_sql = sql.upper()

        for tbl, rows in MOCK_DATASET.items():
            if tbl in upper_sql:
                # Simple condition filtering simulation
                res = list(rows)
                if params:
                    filtered = []
                    for r in res:
                        match = True
                        for k, v in params.items():
                            if k.upper() in r and str(r[k.upper()]) != str(v):
                                match = False
                                break
                        if match:
                            filtered.append(r)
                    res = filtered
                return res[:limit]

        return []
