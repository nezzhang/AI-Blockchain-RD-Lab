"""Lab configuration loading (config/*.yaml)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPO_ROOT / "config"


class LabMeta(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = "AI Blockchain R&D Lab"
    version: str = "0.1.0"
    principle: str = "LLM proposes. Code tests. Evidence decides."


class StorageConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    database: str = "database/lab.db"
    reports_dir: str = "reports"
    ideas_dir: str = "ideas"


class PipelineConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    discovery_count: int = 100
    post_prior_art: int = 20
    finalists: int = 5
    recommended: int = 1
    require_human_approval_for: list[str] = Field(default_factory=list)


class RuntimeConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    llm_provider: str = "mock"
    api_key_env: str = "LAB_LLM_API_KEY"
    max_concurrency: int = 4
    request_timeout_seconds: int = 120
    max_retries: int = 3
    retry_backoff_seconds: float = 2.0
    token_budget_per_run: int = 2_000_000


class LabConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    lab: LabMeta = LabMeta()
    storage: StorageConfig = StorageConfig()
    pipeline: PipelineConfig = PipelineConfig()
    runtime: RuntimeConfig = RuntimeConfig()


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return data if isinstance(data, dict) else {}


def load_config(config_dir: str | Path | None = None) -> LabConfig:
    """Load and validate lab configuration.

    Reads CONFIG_DIR at call time (tests may monkeypatch it). Missing files
    fall back to schema defaults, so a bare checkout works. Small file, so
    no caching — correctness over micro-performance.
    """
    base = Path(config_dir) if config_dir is not None else CONFIG_DIR
    merged: dict[str, Any] = {}
    data = _load_yaml(base / "lab.yaml")
    for section in ("lab", "storage", "pipeline", "runtime"):
        if section in data:
            merged[section] = data[section]
    return LabConfig.model_validate(merged)
