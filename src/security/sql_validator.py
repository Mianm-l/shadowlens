import re
from typing import List, Tuple

FORBIDDEN_KEYWORDS = [
    r"\bINSERT\b", r"\bUPDATE\b", r"\bDELETE\b", r"\bDROP\b",
    r"\bALTER\b", r"\bTRUNCATE\b", r"\bCREATE\b", r"\bRENAME\b",
    r"\bGRANT\b", r"\bREVOKE\b", r"\bEXEC\b", r"\bEXECUTE\b",
    r"\bDECLARE\b", r"\bBEGIN\b", r"\bCALL\b", r"\bLOCK\b",
    r"\bMERGE\b", r"\bUPSERT\b"
]

FORBIDDEN_SYS_PATTERNS = [
    r"\bSYS\.", r"\bSYSTEM\.", r"\bDBA_", r"\bALL_USERS\b", r"\bV\$"
]

class SQLValidationError(Exception):
    pass

class SQLValidator:
    def __init__(self, allowed_tables: List[str]):
        self.allowed_tables = set(t.upper() for t in allowed_tables)

    def validate_select_only(self, sql: str) -> None:
        """Validate that the SQL statement is strictly a read-only SELECT."""
        clean_sql = sql.strip()
        if not clean_sql:
            raise SQLValidationError("SQL 语句不能为空")

        # Reject multiple statements
        if ";" in clean_sql:
            raise SQLValidationError("为防范 SQL 注入，严禁传入包含分号 (;) 的多语句")

        # Reject SQL comments
        if "--" in clean_sql or "/*" in clean_sql or "*/" in clean_sql:
            raise SQLValidationError("为防范逃逸攻击，严禁包含 SQL 注释符 (-- 或 /* */)")

        # Must start with SELECT or WITH (for CTEs)
        upper_sql = clean_sql.upper()
        if not (upper_sql.startswith("SELECT") or upper_sql.startswith("WITH")):
            raise SQLValidationError("受控只读代理仅允许 SELECT 或 WITH ... SELECT 查询语句")

        # Check for forbidden mutation keywords
        for pattern in FORBIDDEN_KEYWORDS:
            if re.search(pattern, upper_sql):
                raise SQLValidationError(f"检测到违规写操作或高危关键字: {pattern}")

        # Check for forbidden system schemas
        for pattern in FORBIDDEN_SYS_PATTERNS:
            if re.search(pattern, upper_sql):
                raise SQLValidationError(f"安全拦截：严禁直接查询 Oracle 系统字典或内部视图: {pattern}")

    def validate_table_whitelist(self, table_name: str) -> None:
        """Validate if the table is in the allowed whitelist."""
        clean_name = table_name.strip().upper()
        if self.allowed_tables and clean_name not in self.allowed_tables:
            raise SQLValidationError(
                f"安全拦截：数据表 '{table_name}' 不在受控白名单范围内！"
                f"允许的表包括: {sorted(list(self.allowed_tables))}"
            )
