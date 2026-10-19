import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional

class SchemaService:
    def __init__(self, dictionary_path: str):
        self.dictionary_path = dictionary_path
        self.data: Dict[str, Any] = {}
        self.modules: List[Dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        p = Path(self.dictionary_path)
        if not p.is_absolute():
            base_dir = Path(__file__).resolve().parent.parent.parent
            p = base_dir / self.dictionary_path

        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                self.data = yaml.safe_load(f) or {}
                self.modules = self.data.get("modules", [])
        else:
            self.modules = []

    def get_table_info(self, table_name: str) -> Optional[Dict[str, Any]]:
        name_upper = table_name.strip().upper()
        for mod in self.modules:
            for tbl in mod.get("tables", []):
                if tbl.get("table_name", "").upper() == name_upper:
                    return {
                        "module_id": mod.get("id"),
                        "module_name": mod.get("name"),
                        **tbl
                    }
        return None

    def search_dictionary(
        self,
        module_id: Optional[str] = None,
        table_name: Optional[str] = None,
        keyword: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        results = []
        for mod in self.modules:
            if module_id and mod.get("id") != module_id:
                continue

            matched_tables = []
            for tbl in mod.get("tables", []):
                t_name = tbl.get("table_name", "")
                t_alias = tbl.get("alias", "")
                t_desc = tbl.get("description", "")

                if table_name and t_name.upper() != table_name.upper():
                    continue

                if keyword:
                    kw = keyword.lower()
                    text_blob = f"{t_name} {t_alias} {t_desc}".lower()
                    col_names = " ".join([c.get("chinese_name", "") + " " + c.get("name", "") for c in tbl.get("columns", [])]).lower()
                    if kw not in text_blob and kw not in col_names:
                        continue

                matched_tables.append(tbl)

            if matched_tables:
                results.append({
                    "module_id": mod.get("id"),
                    "module_name": mod.get("name"),
                    "description": mod.get("description"),
                    "tables": matched_tables
                })

        return results

    def get_masking_map_for_table(self, table_name: str) -> Dict[str, str]:
        """Returns mapping of column_name -> mask_type for a given table."""
        tbl = self.get_table_info(table_name)
        if not tbl:
            return {}
        res = {}
        for col in tbl.get("columns", []):
            if col.get("is_sensitive"):
                res[col.get("name")] = col.get("mask_type", "all_mask")
        return res
