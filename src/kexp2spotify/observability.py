"""Run history, retries, and operator notifications."""

from __future__ import annotations

import logging
import traceback
from collections.abc import Callable
from datetime import date, datetime, timedelta
from typing import Any, Protocol
from zoneinfo import ZoneInfo

import httpx

from .config import Settings
from .logging import redact


class Notifier(Protocol):
    def send(self, message: str) -> None: ...


class TelegramNotifier:
    def __init__(self, token: str, chat_id: str, timeout: float) -> None:
        self.url = f"https://api.telegram.org/bot{token}/sendMessage"
        self.chat_id = chat_id
        self.timeout = timeout

    def send(self, message: str) -> None:
        response = httpx.post(
            self.url, json={"chat_id": self.chat_id, "text": message}, timeout=self.timeout
        )
        response.raise_for_status()
        body = response.json()
        if not body.get("ok", False):
            raise RuntimeError("Telegram rejected the notification")


def notifier_from_settings(settings: Settings) -> Notifier | None:
    if settings.telegram_bot_token and settings.telegram_chat_id:
        return TelegramNotifier(
            settings.telegram_bot_token,
            settings.telegram_chat_id,
            settings.notification_timeout_seconds,
        )
    return None


def safe_notify(notifier: Notifier | None, logger: logging.Logger, message: str) -> bool:
    if notifier is None:
        logger.info("notification skipped reason=telegram_not_configured")
        return False
    try:
        notifier.send(message)
        logger.info("notification sent")
        return True
    except Exception as exc:  # notification must not hide the run result
        logger.error("notification failed error_type=%s", type(exc).__name__)
        return False


def previous_local_day(now: datetime, timezone: str) -> date:
    return (now.astimezone(ZoneInfo(timezone)) - timedelta(days=1)).date()


def daily_summary_message(day: date, summary: dict[str, Any]) -> str:
    return (
        f"KEXP2Spotify — resumen del {day.isoformat()}\n"
        f"Ejecuciones: {summary['runs']} (correctas: {summary['successful']}, "
        f"fallidas: {summary['failed']})\n"
        f"Canciones recibidas: {summary['received']}\n"
        f"Canciones nuevas: {summary['inserted']}\n"
        f"Playlists mostradas: {summary['shows']}\n"
        f"Tracks añadidos a Spotify: {summary['appended']}"
    )


def failure_message(command: str, attempts: int, exc: BaseException) -> str:
    trace = redact("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
    # Telegram accepts 4096 characters. Preserve the exception header and tail of the trace.
    if len(trace) > 3400:
        trace = trace[:1200] + "\n... [traza truncada] ...\n" + trace[-2100:]
    return f"KEXP2Spotify — ejecución fallida\nComando: {command}\nIntentos: {attempts}\n\n{trace}"


def run_with_retries(
    operation: Callable[[], Any], attempts: int = 4, delay_seconds: float = 1.0
) -> tuple[Any, int]:
    """Run an operation once plus three retries, preserving the final exception."""

    import time

    for attempt in range(1, attempts + 1):
        try:
            return operation(), attempt
        except Exception:
            if attempt == attempts:
                raise
            time.sleep(delay_seconds * attempt)
    raise AssertionError("unreachable")


def build_run_summary(command: str, result: Any) -> dict[str, int | str]:
    values: dict[str, int | str] = {"command": command}
    for key in ("received", "inserted", "shows", "appended_tracks"):
        values[key] = int(getattr(result, key, 0))
    return values
