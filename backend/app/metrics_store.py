"""
Almacen runtime de metricas operacionales.

Fase 11.2:
- metricas runtime en memoria;
- contadores simples thread-safe;
- snapshot para endpoints de monitoreo.

No usa Ollama.
No usa LLM remoto.
"""

from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
import time


class MetricsStore:
    """Almacen thread-safe de metricas runtime."""

    def __init__(self) -> None:
        self._lock = Lock()
        self.started_at_epoch = time.time()
        self.started_at_utc = datetime.now(timezone.utc)

        self._metrics = {
            "indexed_files": 0,
            "indexed_chunks": 0,
            "generated_embeddings": 0,
            "search_requests": 0,
            "search_errors": 0,
            "index_errors": 0,
            "watcher_events": 0,
            "index_time_total_seconds": 0.0,
            "search_time_total_seconds": 0.0,
        }

    def increment(self, key: str, value: int = 1) -> None:
        """Incrementa contador numerico."""

        with self._lock:
            current_value = self._metrics.get(key, 0)
            self._metrics[key] = current_value + value

    def add_time(self, key: str, value: float) -> None:
        """Acumula tiempo en segundos."""

        with self._lock:
            current_value = self._metrics.get(key, 0.0)
            self._metrics[key] = current_value + value

    def snapshot(self) -> dict:
        """Retorna copia consistente de metricas."""

        with self._lock:
            now = datetime.now(timezone.utc)
            uptime_seconds = int(time.time() - self.started_at_epoch)

            search_requests = int(self._metrics.get("search_requests", 0))
            indexed_files = int(self._metrics.get("indexed_files", 0))

            search_time_total = float(
                self._metrics.get("search_time_total_seconds", 0.0)
            )
            index_time_total = float(
                self._metrics.get("index_time_total_seconds", 0.0)
            )

            avg_search_time = (
                search_time_total / search_requests
                if search_requests > 0
                else 0.0
            )

            avg_index_time = (
                index_time_total / indexed_files
                if indexed_files > 0
                else 0.0
            )

            return {
                "status": "ok",
                "started_at_utc": self.started_at_utc.isoformat(),
                "current_time_utc": now.isoformat(),
                "uptime_seconds": uptime_seconds,
                "metrics": dict(self._metrics),
                "average_search_time_seconds": avg_search_time,
                "average_index_time_seconds": avg_index_time,
            }


metrics_store = MetricsStore()
