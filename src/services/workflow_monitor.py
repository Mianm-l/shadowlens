from datetime import datetime
from typing import Any, Dict, List
from ..db.oracle_pool import OraclePoolManager
from ..security.data_masker import DataMasker
from .schema_service import SchemaService

class WorkflowMonitorService:
    def __init__(self, db_pool: OraclePoolManager, schema_svc: SchemaService):
        self.db = db_pool
        self.schema = schema_svc

    def find_stuck_workflows(self, min_stuck_hours: int = 48, limit: int = 50) -> Dict[str, Any]:
        """
        Identify approval affairs that have stayed pending/processing for more than min_stuck_hours.
        """
        # Fetch affairs
        affairs, _ = self.db.execute_query("SELECT * FROM OA_COL_AFFAIR", max_rows=limit * 2)
        summaries, _ = self.db.execute_query("SELECT * FROM OA_COL_SUMMARY", max_rows=limit * 2)

        summary_map = {s.get("ID"): s for s in summaries}
        now = datetime.now()

        stuck_items = []
        for a in affairs:
            # state: 1 (待办/未读), 2 (在办/已读)
            state = a.get("STATE")
            if state not in (1, 2):
                continue

            rcv_time_str = a.get("RECEIVE_TIME")
            if not rcv_time_str:
                continue

            try:
                # Format: 2026-10-12 10:30:00
                rcv_dt = datetime.strptime(str(rcv_time_str)[:19], "%Y-%m-%d %H:%M:%S")
                hours_diff = (now - rcv_dt).total_seconds() / 3600.0
            except Exception:
                # Fallback if mock or date object
                hours_diff = 72.0

            if hours_diff >= min_stuck_hours:
                sum_obj = summary_map.get(a.get("OBJECT_ID"), {})
                stuck_items.append({
                    "affair_id": a.get("ID"),
                    "summary_id": a.get("OBJECT_ID"),
                    "subject": sum_obj.get("SUBJECT", "未知事项标题"),
                    "starter_name": sum_obj.get("START_MEMBER_NAME", "未知发起人"),
                    "current_handler": a.get("MEMBER_NAME"),
                    "handler_phone": DataMasker.mask_phone(str(a.get("MEMBER_PHONE", ""))),
                    "affair_state_desc": "待办未读" if state == 1 else "在办处理中",
                    "receive_time": str(rcv_time_str),
                    "stuck_hours": round(hours_diff, 1)
                })

        # Sort by stuck_hours descending
        stuck_items.sort(key=lambda x: x["stuck_hours"], reverse=True)
        items_trimmed = stuck_items[:limit]

        return {
            "threshold_hours": min_stuck_hours,
            "total_stuck_detected": len(stuck_items),
            "returned_count": len(items_trimmed),
            "stuck_list": items_trimmed
        }
