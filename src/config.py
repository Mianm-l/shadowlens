import os
import yaml
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field

class ServerConfig(BaseModel):
    name: str = "shadowlens-oracle-mcp"
    host: str = "0.0.0.0"
    port: int = 8000
    transport: str = "sse"

class OracleConfig(BaseModel):
    user: str = "SHADOW_RO"
    password: str = "SecretReadOnly123"
    dsn: str = "localhost:1521/ORCLPDB1"
    min_pool: int = 1
    max_pool: int = 5
    timeout_seconds: int = 5
    dry_run_mode: bool = True

class SecurityConfig(BaseModel):
    max_rows_per_query: int = 200
    force_read_only_session: bool = True
    mask_sensitive_data: bool = True
    allowed_tables: List[str] = Field(default_factory=list)

class PathsConfig(BaseModel):
    dictionary_file: str = "config/schema-dictionary.yaml"
    reconciliation_file: str = "config/reconciliation-rules.yaml"

class AppConfig(BaseModel):
    server: ServerConfig = Field(default_factory=ServerConfig)
    oracle: OracleConfig = Field(default_factory=OracleConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)

def load_config(config_path: Optional[str] = None) -> AppConfig:
    """Load configuration from YAML file or environment variables."""
    base_dir = Path(__file__).resolve().parent.parent
    if not config_path:
        env_path = os.getenv("SHADOWLENS_CONFIG")
        if env_path and Path(env_path).exists():
            config_path = env_path
        else:
            default_yaml = base_dir / "config" / "config.yaml"
            if default_yaml.exists():
                config_path = str(default_yaml)
            else:
                return AppConfig()

    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    # Allow environment variable overrides
    if "ORACLE_DSN" in os.environ:
        data.setdefault("oracle", {})["dsn"] = os.environ["ORACLE_DSN"]
    if "ORACLE_USER" in os.environ:
        data.setdefault("oracle", {})["user"] = os.environ["ORACLE_USER"]
    if "ORACLE_PASSWORD" in os.environ:
        data.setdefault("oracle", {})["password"] = os.environ["ORACLE_PASSWORD"]
    if "SHADOWLENS_DRY_RUN" in os.environ:
        val = os.environ["SHADOWLENS_DRY_RUN"].lower() in ("1", "true", "yes")
        data.setdefault("oracle", {})["dry_run_mode"] = val

    return AppConfig(**data)
