"""Mandatory YAML configuration with environment overrides."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
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
    spotify_client_id: str | None = None
    spotify_client_secret: str | None = None
    spotify_scope: str = (
        "playlist-read-private playlist-read-collaborative playlist-modify-public "
        "playlist-modify-private ugc-image-upload"
    )
    spotify_redirect_uri: str | None = None
    spotify_token_path: Path | None = None
    spotify_playlist_limit: int = Field(default=50, gt=0)
    spotify_timezone: str = "Europe/Madrid"
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    notification_timeout_seconds: float = Field(default=10, gt=0)
    log_file_path: Path = Path("data/kexp2spotify.log")
    log_level: str = "INFO"
    log_file_max_bytes: int = Field(default=10_485_760, gt=0)
    log_file_backup_count: int = Field(default=5, ge=0)
    log_console: bool = True

    @field_validator("database_path", "config_file", "log_file_path")
    @classmethod
    def non_empty_path(cls, value: Path) -> Path:
        if not str(value):
            raise ValueError("path must not be empty")
        return value

    @field_validator("log_level")
    @classmethod
    def valid_log_level(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("log_level must be DEBUG, INFO, WARNING, ERROR, or CRITICAL")
        return normalized

    @field_validator(
        "spotify_client_id", "spotify_client_secret", "spotify_scope", "spotify_timezone"
    )
    @classmethod
    def non_empty_spotify_text(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Spotify value must not be empty")
        return value.strip() if value is not None else value

    @field_validator("spotify_redirect_uri")
    @classmethod
    def valid_spotify_redirect_uri(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not value.startswith("http://127.0.0.1:") or not value.endswith("/callback"):
            raise ValueError("spotify_redirect_uri must use http://127.0.0.1:<port>/callback")
        return value


def load_settings(config_path: str | Path | None = None) -> Settings:
    """Load current-directory .env, required YAML, then environment overrides."""

    load_dotenv(Path.cwd() / ".env", override=False)
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
    for key in (
        "kexp_plays_url",
        "fetch_limit",
        "deduplication_window",
        "database_path",
        "request_timeout_seconds",
        "log_file_path",
        "log_level",
        "log_file_max_bytes",
        "log_file_backup_count",
        "log_console",
    ):
        env_key = f"KEXP2SPOTIFY_{key.upper()}"
        if env_key in os.environ:
            values[key] = os.environ[env_key]
    for key in (
        "client_id",
        "client_secret",
        "scope",
        "redirect_uri",
        "token_path",
        "playlist_limit",
        "timezone",
    ):
        env_key = f"SPOTIFY_{key.upper()}"
        legacy_key = f"KEXP2SPOTIFY_{env_key}"
        if env_key in os.environ:
            values[f"spotify_{key}"] = os.environ[env_key]
        elif legacy_key in os.environ:
            values[f"spotify_{key}"] = os.environ[legacy_key]
    for key, env_key in (
        ("telegram_bot_token", "KEXP2SPOTIFY_TELEGRAM_BOT_TOKEN"),
        ("telegram_chat_id", "KEXP2SPOTIFY_TELEGRAM_CHAT_ID"),
        ("notification_timeout_seconds", "KEXP2SPOTIFY_NOTIFICATION_TIMEOUT_SECONDS"),
    ):
        if env_key in os.environ:
            values[key] = os.environ[env_key]
    try:
        return Settings.model_validate(values)
    except ValidationError as exc:
        raise ConfigurationError(f"invalid configuration: {exc}") from exc
