from typing import Any, Dict, List, Optional
from ..db.oracle_pool import OraclePoolManager
from ..security.data_masker import DataMasker
from .schema_service import SchemaService

class QueryService:
    def __init__(self, db_pool: OraclePoolManager, schema_service: SchemaService, mask_sensitive: bool = True):
        self.db = db_pool
        self.schema = schema_service
        self.mask_sensitive = mask_sensitive

    def query_audited_view(
        self,
        table_name: str,
        columns: Optional[List[str]] = None,
        filter_dict: Optional[Dict[str, Any]] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Safely query a whitelisted table with parameterized filters and data masking.
        """
        table_upper = table_name.strip().upper()
        # Whitelist validation
        self.db.validator.validate_table_whitelist(table_upper)

        tbl_info = self.schema.get_table_info(table_upper)
        cols_clause = "*"
        if columns:
            safe_cols = [c.strip().upper() for c in columns if c.strip().isalnum() or "_" in c]
            if safe_cols:
                cols_clause = ", ".join(safe_cols)

        # Build parameterized where clause
        where_clauses = []
        params = {}
        if filter_dict:
            for idx, (k, v) in enumerate(filter_dict.items()):
                k_clean = k.strip().upper()
                param_name = f"p_{idx}"
                where_clauses.append(f"{k_clean} = :{param_name}")
                params[param_name] = v

        where_str = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        sql = f"SELECT {cols_clause} FROM {table_upper}{where_str}"

        # Execute
        records, duration_ms = self.db.execute_query(sql, params=params, max_rows=limit)

        # Mask sensitive data
        if self.mask_sensitive:
            mask_types = self.schema.get_masking_map_for_table(table_upper)
            records = DataMasker.mask_records(records, mask_types)

        # Annotate enums if available in dictionary
        if tbl_info:
            enums_map = {}
            for c in tbl_info.get("columns", []):
                if "enums" in c:
                    enums_map[c.get("name")] = c.get("enums")

            if enums_map:
                for r in records:
                    for col_name, enum_def in enums_map.items():
                        if col_name in r and r[col_name] is not None:
                            val = r[col_name]
                            if val in enum_def or str(val) in enum_def:
                                label = enum_def.get(val, enum_def.get(str(val)))
                                r[f"{col_name}_DESC"] = label

        return {
            "table_name": table_upper,
            "table_alias": tbl_info.get("alias") if tbl_info else "",
            "total_fetched": len(records),
            "execution_time_ms": duration_ms,
            "is_mock": self.db.is_mock_active,
            "records": records
        }
