"""
Configuracion centralizada de logging y monitoreo.

Fase 11.1:
- logging rotativo;
- lectura controlada de logs;
- resumen de logs por nivel;
- metricas basicas de archivo de log;
- uptime de backend.

No usa Ollama.
No usa LLM remoto.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from logging.handlers import RotatingFileHandler
import logging
import os
import sys


BASE_DIR = Path(__file__).resolve().parents[2]
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOGS_DIR / "backend.log"
MAX_LOG_BYTES = 5 * 1024 * 1024
BACKUP_COUNT = 5
SERVICE_STARTED_AT = datetime.now(timezone.utc)

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

logger = logging.getLogger("local_search")
logger.setLevel(logging.INFO)
logger.propagate = False


def _build_file_handler() -> RotatingFileHandler:
    """Crea handler rotativo para logs persistentes."""

    handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=MAX_LOG_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    return handler


def _build_stream_handler() -> logging.StreamHandler:
    """Crea handler para salida por consola."""

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    return handler


def configure_logging() -> None:
    """Configura logging una sola vez."""

    if logger.handlers:
        return

    logger.addHandler(_build_file_handler())
    logger.addHandler(_build_stream_handler())


configure_logging()


def utc_now_iso() -> str:
    """Retorna timestamp UTC ISO 8601."""

    return datetime.now(timezone.utc).isoformat()


def log_info(message: str) -> None:
    """Registra mensaje informativo."""

    logger.info(message)


def log_warning(message: str) -> None:
    """Registra advertencia."""

    logger.warning(message)


def log_error(message: str) -> None:
    """Registra mensaje de error."""

    logger.error(message)


def log_exception(message: str) -> None:
    """Registra excepcion con traceback."""

    logger.exception(message)


def _safe_lines_value(lines: int) -> int:
    """Normaliza cantidad de lineas solicitadas."""

    if lines < 1:
        return 1

    if lines > 5000:
        return 5000

    return lines


def _read_all_log_lines() -> list[str]:
    """Lee todas las lineas del log principal."""

    if not LOG_FILE.exists():
        return []

    return LOG_FILE.read_text(
        encoding="utf-8",
        errors="ignore",
    ).splitlines()


def _line_matches_level(line: str, level: str | None) -> bool:
    """Indica si una linea corresponde al nivel solicitado."""

    if not level:
        return True

    clean_level = level.strip().upper()

    if not clean_level:
        return True

    return f"| {clean_level} |" in line


def _line_matches_contains(line: str, contains: str | None) -> bool:
    """Indica si una linea contiene el texto solicitado."""

    if not contains:
        return True

    clean_contains = contains.strip().lower()

    if not clean_contains:
        return True

    return clean_contains in line.lower()


def read_logs(
    lines: int = 200,
    level: str | None = None,
    contains: str | None = None,
) -> dict:
    """Retorna lineas recientes del log principal."""

    normalized_lines = _safe_lines_value(lines)
    all_lines = _read_all_log_lines()

    filtered_lines = [
        line
        for line in all_lines
        if _line_matches_level(line, level)
        and _line_matches_contains(line, contains)
    ]

    selected_lines = filtered_lines[-normalized_lines:]

    return {
        "status": "ok",
        "log_file": str(LOG_FILE),
        "requested_lines": normalized_lines,
        "returned_lines": len(selected_lines),
        "total_lines": len(all_lines),
        "filtered_lines": len(filtered_lines),
        "level": level,
        "contains": contains,
        "lines": selected_lines,
    }


def log_summary() -> dict:
    """Retorna resumen del archivo de log."""

    all_lines = _read_all_log_lines()

    counters = {
        "INFO": 0,
        "WARNING": 0,
        "ERROR": 0,
        "CRITICAL": 0,
        "OTHER": 0,
    }

    for line in all_lines:
        matched = False
        for level in ("INFO", "WARNING", "ERROR", "CRITICAL"):
            if f"| {level} |" in line:
                counters[level] += 1
                matched = True
                break

        if not matched:
            counters["OTHER"] += 1

    latest_line = all_lines[-1] if all_lines else None

    return {
        "status": "ok",
        "log_file": str(LOG_FILE),
        "exists": LOG_FILE.exists(),
        "size_bytes": LOG_FILE.stat().st_size if LOG_FILE.exists() else 0,
        "total_lines": len(all_lines),
        "levels": counters,
        "latest_line": latest_line,
    }


def backend_runtime_metrics() -> dict:
    """Retorna metricas basicas del proceso backend."""

    now = datetime.now(timezone.utc)
    uptime_seconds = int((now - SERVICE_STARTED_AT).total_seconds())

    return {
        "status": "ok",
        "service_started_at": SERVICE_STARTED_AT.isoformat(),
        "current_time_utc": now.isoformat(),
        "uptime_seconds": uptime_seconds,
        "process_id": os.getpid(),
        "log_file": str(LOG_FILE),
        "log_size_bytes": LOG_FILE.stat().st_size if LOG_FILE.exists() else 0,
        "max_log_bytes": MAX_LOG_BYTES,
        "backup_count": BACKUP_COUNT,
    }
