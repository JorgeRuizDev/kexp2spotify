"""Mandatory YAML configuration with environment overrides."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import AnyHttpUrl, BaseModel, Field, ValidationError, field_validator

from .errors import ConfigurationError


class Settings(BaseModel):
    """Validated runtime settings."""

    kexp_plays_url: AnyHttpUrl
    fetch_limit: int = Field(gt=0)
    deduplication_window: int = Field(gt=0)
    database_path: Path
    request_timeout_seconds: float = Field(gt=0)
    config_file: Path

    @field_validator("database_path", "config_file")
    @classmethod
    def non_empty_path(cls, value: Path) -> Path:
        if not str(value):
            raise ValueError("path must not be empty")
        return value


def load_settings(config_path: str | Path | None = None) -> Settings:
    """Load required YAML, then apply KEXP_ environment overrides."""

    selected = Path(config_path or os.environ.get("KEXP2SPOTIFY_CONFIG_FILE", "config.yml"))
    if not selected.is_file():
        raise ConfigurationError(f"configuration file is missing or unreadable: {selected}")
    try:
        raw = yaml.safe_load(selected.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigurationError(f"could not read configuration YAML: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigurationError("configuration YAML must contain a mapping")
    values: dict[str, Any] = dict(raw)
    values["config_file"] = selected
    for key in ("kexp_plays_url", "fetch_limit", "deduplication_window", "database_path", "request_timeout_seconds"):
        env_key = f"KEXP2SPOTIFY_{key.upper()}"
        if env_key in os.environ:
            values[key] = os.environ[env_key]
    try:
        return Settings.model_validate(values)
    except ValidationError as exc:
        raise ConfigurationError(f"invalid configuration: {exc}") from exc
