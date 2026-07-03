"""
Watcher de filesystem.

Este modulo usa watchdog para supervisar una carpeta local. Cuando detecta
creacion o modificacion de archivos soportados, ejecuta la indexacion del
archivo afectado.

No usa Ollama.
No usa LLM.
"""

from pathlib import Path
from threading import Lock

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .indexer import SUPPORTED_EXTENSIONS, index_file
from .logger_config import log_error, log_info


class LocalSearchEventHandler(FileSystemEventHandler):
    """Manejador de eventos del filesystem."""

    def on_created(self, event) -> None:
        """Procesa archivos creados."""

        if event.is_directory:
            return

        handle_file_event(event.src_path, "created")

    def on_modified(self, event) -> None:
        """Procesa archivos modificados."""

        if event.is_directory:
            return

        handle_file_event(event.src_path, "modified")


watcher_lock = Lock()
watcher_observer: Observer | None = None
watcher_folder: str | None = None


def is_supported_file(file_path: str) -> bool:
    """Indica si el archivo tiene extension soportada."""

    path = Path(file_path)

    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def handle_file_event(file_path: str, event_type: str) -> None:
    """Indexa un archivo detectado por el watcher."""

    path = Path(file_path)

    if not path.exists():
        return

    if not path.is_file():
        return

    if not is_supported_file(str(path)):
        return

    try:
        log_info(f"WATCHER {event_type.upper()} | {path}")

        index_file(str(path))

    except Exception as exc:
        log_error(f"WATCHER ERROR | {path} | {exc}")


def start_watcher(folder_path: str) -> dict:
    """Inicia supervision de carpeta."""

    global watcher_observer
    global watcher_folder

    folder = Path(folder_path).expanduser().resolve()

    if not folder.exists():
        raise FileNotFoundError(f"Folder does not exist: {folder}")

    if not folder.is_dir():
        raise ValueError(f"Path is not a folder: {folder}")

    with watcher_lock:
        if watcher_observer is not None:
            return {
                "status": "already_running",
                "folder_path": watcher_folder,
            }

        event_handler = LocalSearchEventHandler()

        observer = Observer()

        observer.schedule(
            event_handler,
            str(folder),
            recursive=True,
        )

        observer.start()

        watcher_observer = observer
        watcher_folder = str(folder)

    log_info(f"WATCHER STARTED | {folder}")

    return {
        "status": "started",
        "folder_path": str(folder),
        "recursive": True,
    }


def stop_watcher() -> dict:
    """Detiene supervision activa."""

    global watcher_observer
    global watcher_folder

    with watcher_lock:
        if watcher_observer is None:
            return {
                "status": "not_running",
                "folder_path": None,
            }

        watcher_observer.stop()
        watcher_observer.join(timeout=10)

        stopped_folder = watcher_folder

        watcher_observer = None
        watcher_folder = None

    log_info(f"WATCHER STOPPED | {stopped_folder}")

    return {
        "status": "stopped",
        "folder_path": stopped_folder,
    }


def watcher_status() -> dict:
    """Retorna estado actual del watcher."""

    is_running = watcher_observer is not None

    return {
        "status": "ok",
        "running": is_running,
        "folder_path": watcher_folder,
        "supported_extensions": sorted(SUPPORTED_EXTENSIONS),
    }
