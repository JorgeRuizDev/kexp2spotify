import logging
from pathlib import Path

from kexp2spotify.config import load_settings
from kexp2spotify.logging import configure_logging


def test_logging_configuration_is_loaded_from_yaml_and_environment(
    tmp_path: Path, monkeypatch
) -> None:
    config = tmp_path / "config.yml"
    config.write_text(
        "kexp_plays_url: https://example.com/plays\n"
        "fetch_limit: 5\n"
        "deduplication_window: 10\n"
        "database_path: db.sqlite\n"
        "request_timeout_seconds: 2\n"
        f"log_file_path: {tmp_path / 'yaml.log'}\n"
        "log_level: WARNING\n",
        encoding="utf-8",
    )
    log_path = tmp_path / "env" / "application.log"
    monkeypatch.setenv("KEXP2SPOTIFY_LOG_FILE_PATH", str(log_path))
    monkeypatch.setenv("KEXP2SPOTIFY_LOG_LEVEL", "DEBUG")

    logger = configure_logging(load_settings(config))
    logger.debug("configured")

    assert logger.level == logging.DEBUG
    assert log_path.read_text(encoding="utf-8").endswith("DEBUG kexp2spotify configured\n")
    assert "T" in log_path.read_text(encoding="utf-8").split()[0]


def test_logging_configuration_rejects_unknown_level(tmp_path: Path) -> None:
    config = tmp_path / "config.yml"
    config.write_text(
        "kexp_plays_url: https://example.com/plays\n"
        "fetch_limit: 5\n"
        "deduplication_window: 10\n"
        "database_path: db.sqlite\n"
        "request_timeout_seconds: 2\n"
        "log_level: TRACE\n",
        encoding="utf-8",
    )

    from kexp2spotify.errors import ConfigurationError

    try:
        load_settings(config)
    except ConfigurationError:
        pass
    else:
        raise AssertionError("invalid log level should fail configuration")
