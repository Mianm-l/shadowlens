import re
from typing import Any, Dict, List, Optional

PHONE_REGEX = re.compile(r"^1[3-9]\d{9}$")
ID_CARD_REGEX = re.compile(r"^\d{17}[\dXx]$")
EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")

class DataMasker:
    @staticmethod
    def mask_phone(val: str) -> str:
        """Mask mobile phone: 13812345678 -> 138****5678"""
        if not val or len(val) < 11:
            return val
        return f"{val[:3]}****{val[-4:]}"

    @staticmethod
    def mask_idcard(val: str) -> str:
        """Mask Chinese ID Card: 110101199001011234 -> 110101********1234"""
        if not val or len(val) < 18:
            return val
        return f"{val[:6]}********{val[-4:]}"

    @staticmethod
    def mask_bank_card(val: str) -> str:
        """Mask Bank Card Number: 6222021234567890 -> 622202********7890"""
        if not val or len(val) < 12:
            return val
        return f"{val[:6]}********{val[-4:]}"

    @staticmethod
    def mask_email(val: str) -> str:
        """Mask Email: test@example.com -> t***@example.com"""
        if not val or "@" not in val:
            return val
        parts = val.split("@")
        name = parts[0]
        domain = parts[1]
        if len(name) <= 2:
            masked_name = name[0] + "***"
        else:
            masked_name = name[0] + "***" + name[-1]
        return f"{masked_name}@{domain}"

    @classmethod
    def mask_value(cls, val: Any, mask_type: Optional[str] = None, field_name: Optional[str] = None) -> Any:
        if val is None or not isinstance(val, str):
            return val

        str_val = str(val).strip()

        # Explicit mask_type specified in schema
        if mask_type == "phone":
            return cls.mask_phone(str_val)
        elif mask_type == "idcard":
            return cls.mask_idcard(str_val)
        elif mask_type == "bank_card":
            return cls.mask_bank_card(str_val)
        elif mask_type == "email":
            return cls.mask_email(str_val)

        # Field name heuristics
        if field_name:
            fn = field_name.upper()
            if any(k in fn for k in ["PHONE", "MOBILE", "TEL"]):
                return cls.mask_phone(str_val)
            if any(k in fn for k in ["IDCARD", "ID_CARD", "CERT_NO"]):
                return cls.mask_idcard(str_val)
            if any(k in fn for k in ["BANK_ACC", "ACCOUNT_NO", "CARD_NO"]):
                return cls.mask_bank_card(str_val)
            if any(k in fn for k in ["PASSWORD", "PWD", "SECRET", "TOKEN"]):
                return "******"

        # Pattern heuristics
        if PHONE_REGEX.match(str_val):
            return cls.mask_phone(str_val)
        if ID_CARD_REGEX.match(str_val):
            return cls.mask_idcard(str_val)

        return val

    @classmethod
    def mask_records(
        cls, records: List[Dict[str, Any]], field_mask_types: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        field_mask_types = field_mask_types or {}
        masked = []
        for r in records:
            item = {}
            for col, val in r.items():
                mtype = field_mask_types.get(col)
                item[col] = cls.mask_value(val, mask_type=mtype, field_name=col)
            masked.append(item)
        return masked
