import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
from ..db.oracle_pool import OraclePoolManager
from ..security.data_masker import DataMasker
from .schema_service import SchemaService

class ReconciliationService:
    def __init__(self, db_pool: OraclePoolManager, schema_svc: SchemaService, rules_file: str):
        self.db = db_pool
        self.schema = schema_svc
        self.rules_file = rules_file
        self.rules: List[Dict[str, Any]] = []
        self._load_rules()

    def _load_rules(self) -> None:
        p = Path(self.rules_file)
        if not p.is_absolute():
            base_dir = Path(__file__).resolve().parent.parent.parent
            p = base_dir / self.rules_file

        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                self.rules = data.get("rules", [])
        else:
            self.rules = []

    def list_rules(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": r.get("id"),
                "name": r.get("name"),
                "description": r.get("description"),
                "primary_table": r.get("primary_table"),
                "secondary_table": r.get("secondary_table")
            }
            for r in self.rules
        ]

    def reconcile(self, rule_id: str, max_check: int = 100) -> Dict[str, Any]:
        rule = next((r for r in self.rules if r.get("id") == rule_id), None)
        if not rule:
            available = [r.get("id") for r in self.rules]
            raise ValueError(f"对账规则 '{rule_id}' 不存在！可用规则: {available}")

        prim_tbl = rule.get("primary_table")
        sec_tbl = rule.get("secondary_table")
        prim_key = rule.get("primary_join_key")
        sec_key = rule.get("secondary_join_key")

        # 1. Fetch primary table records
        prim_records, _ = self.db.execute_query(f"SELECT * FROM {prim_tbl}", max_rows=max_check)
        # 2. Fetch secondary table records
        sec_records, _ = self.db.execute_query(f"SELECT * FROM {sec_tbl}", max_rows=max_check)

        # Index secondary records by sec_key
        sec_map = {}
        for s in sec_records:
            k = s.get(sec_key)
            if k is not None:
                sec_map[str(k)] = s

        # Discrepancy analysis
        discrepancies = []
        matched_count = 0

        for p in prim_records:
            pk_val = str(p.get(prim_key, ""))
            sec_item = sec_map.get(pk_val)

            if not sec_item:
                # Discrepancy: Missing in secondary
                discrepancies.append({
                    "rule_id": rule_id,
                    "discrepancy_code": "MISSING_RECORD",
                    "primary_key_value": pk_val,
                    "description": f"主表记录 ({prim_tbl}) 已存在，但在从表 ({sec_tbl}) 中完全缺失对应的关联记录",
                    "primary_data": p,
                    "secondary_data": None
                })
            else:
                # Check for amount mismatch
                p_amt = p.get("TOTAL_AMOUNT", p.get("ACTUAL_AMOUNT"))
                s_amt = sec_item.get("ACTUAL_AMOUNT", sec_item.get("VOUCHER_AMOUNT"))

                if p_amt is not None and s_amt is not None:
                    diff = abs(float(p_amt) - float(s_amt))
                    if diff > 0.01:
                        discrepancies.append({
                            "rule_id": rule_id,
                            "discrepancy_code": "AMOUNT_MISMATCH",
                            "primary_key_value": pk_val,
                            "description": f"主表金额 ({p_amt}) 与从表金额 ({s_amt}) 不一致，差额: {round(diff, 2)}",
                            "primary_data": p,
                            "secondary_data": sec_item
                        })
                        continue

                # Check for status issues (e.g. unposted voucher)
                if sec_item.get("POST_STATUS") == 0:
                    discrepancies.append({
                        "rule_id": rule_id,
                        "discrepancy_code": "UNPOSTED_STATUS",
                        "primary_key_value": pk_val,
                        "description": f"从表 ({sec_tbl}) 凭证记录处于未过账/未结账草稿状态",
                        "primary_data": p,
                        "secondary_data": sec_item
                    })
                    continue

                matched_count += 1

        # Apply data masking on discrepancies
        for d in discrepancies:
            if d.get("primary_data"):
                mask_p = self.schema.get_masking_map_for_table(prim_tbl)
                d["primary_data"] = DataMasker.mask_records([d["primary_data"]], mask_p)[0]
            if d.get("secondary_data"):
                mask_s = self.schema.get_masking_map_for_table(sec_tbl)
                d["secondary_data"] = DataMasker.mask_records([d["secondary_data"]], mask_s)[0]

        return {
            "rule_id": rule_id,
            "rule_name": rule.get("name"),
            "total_primary_checked": len(prim_records),
            "clean_matches": matched_count,
            "discrepancy_count": len(discrepancies),
            "discrepancies": discrepancies
        }
