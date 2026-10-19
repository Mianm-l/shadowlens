import json
import unittest
from pathlib import Path
import sys

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.config import load_config
from src.security.sql_validator import SQLValidator, SQLValidationError
from src.security.data_masker import DataMasker
from src.db.oracle_pool import OraclePoolManager
from src.services.schema_service import SchemaService
from src.services.query_service import QueryService
from src.services.reconciler import ReconciliationService
from src.services.workflow_monitor import WorkflowMonitorService

class TestShadowLensCore(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load_config(str(BASE_DIR / "config" / "config.yaml"))
        cls.config.oracle.dsn = "mock"
        cls.validator = SQLValidator(allowed_tables=cls.config.security.allowed_tables)
        cls.schema_svc = SchemaService(str(BASE_DIR / cls.config.paths.dictionary_file))
        cls.db_pool = OraclePoolManager(cls.config.oracle, cls.config.security)
        cls.query_svc = QueryService(cls.db_pool, cls.schema_svc)
        cls.reconcile_svc = ReconciliationService(
            cls.db_pool, cls.schema_svc, str(BASE_DIR / cls.config.paths.reconciliation_file)
        )
        cls.wf_monitor = WorkflowMonitorService(cls.db_pool, cls.schema_svc)

    def test_sql_validator_blocks_mutations(self):
        """Test SQL security validator rejects all write operations."""
        evil_queries = [
            "DELETE FROM CT_PURCHASE_ORDER WHERE 1=1",
            "UPDATE CT_PURCHASE_ORDER SET TOTAL_AMOUNT = 0",
            "INSERT INTO CT_PURCHASE_ORDER VALUES ('1', 'bad')",
            "DROP TABLE CT_PURCHASE_ORDER",
            "SELECT * FROM CT_PURCHASE_ORDER; DROP TABLE CT_RECEIVING_BILL",
            "SELECT * FROM CT_PURCHASE_ORDER -- comment out",
            "SELECT * FROM SYS.ALL_USERS",
            "SELECT * FROM V$SESSION"
        ]
        for q in evil_queries:
            with self.subTest(query=q):
                with self.assertRaises(SQLValidationError):
                    self.validator.validate_select_only(q)

    def test_sql_validator_whitelist(self):
        """Test table whitelist enforcement."""
        # Whitelisted
        self.validator.validate_table_whitelist("CT_PURCHASE_ORDER")
        # Not whitelisted
        with self.assertRaises(SQLValidationError):
            self.validator.validate_table_whitelist("SECRET_SALARY_TABLE")

    def test_data_masker(self):
        """Test data masking functions."""
        self.assertEqual(DataMasker.mask_phone("13812345678"), "138****5678")
        self.assertEqual(DataMasker.mask_idcard("110101199001011234"), "110101********1234")
        self.assertEqual(DataMasker.mask_bank_card("6222021234567890"), "622202********7890")

    def test_schema_service_dictionary(self):
        """Test schema dictionary search and resolution."""
        results = self.schema_svc.search_dictionary(keyword="采购")
        self.assertTrue(len(results) > 0)
        table_info = self.schema_svc.get_table_info("CT_PURCHASE_ORDER")
        self.assertIsNotNone(table_info)
        self.assertEqual(table_info.get("primary_key"), "ORDER_ID")

    def test_query_service_with_masking_and_enums(self):
        """Test audited querying and automatic masking/enums."""
        res = self.query_svc.query_audited_view("CT_PURCHASE_ORDER", limit=10)
        records = res["records"]
        self.assertTrue(len(records) > 0)
        first_row = records[0]
        # Check phone is masked
        self.assertIn("****", first_row["CONTACT_PHONE"])
        # Check enum translated
        self.assertIn("ORDER_STATUS_DESC", first_row)
        self.assertIn("审批", first_row["ORDER_STATUS_DESC"])

    def test_reconciliation_detects_discrepancies(self):
        """Test reconciliation detects missing records and amount differences."""
        res = self.reconcile_svc.reconcile("procurement_vs_receiving")
        self.assertEqual(res["rule_id"], "procurement_vs_receiving")
        self.assertTrue(res["discrepancy_count"] > 0)
        
        # Check discrepancy codes exist
        codes = [d["discrepancy_code"] for d in res["discrepancies"]]
        self.assertIn("AMOUNT_MISMATCH", codes)
        self.assertIn("MISSING_RECORD", codes)

    def test_workflow_monitor_finds_stuck_approvals(self):
        """Test detection of long stuck workflow approvals."""
        res = self.wf_monitor.find_stuck_workflows(min_stuck_hours=48)
        self.assertTrue(res["total_stuck_detected"] >= 2)
        top_stuck = res["stuck_list"][0]
        self.assertGreater(top_stuck["stuck_hours"], 48)
        self.assertIn("****", top_stuck["handler_phone"])

if __name__ == "__main__":
    unittest.main()
