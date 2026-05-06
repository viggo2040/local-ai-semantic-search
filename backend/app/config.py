from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
CHROMA_DIR = DATA_DIR / "chroma"
REGISTRY_DB = DATA_DIR / "registry.sqlite"

COLLECTION_NAME = "local_documents"

OLLAMA_BASE_URL = "http://127.0.0.1:11434"
OLLAMA_EMBED_MODEL = "nomic-embed-text"
OLLAMA_CHAT_MODEL = "llama3.1:8b"

SUPPORTED_EXTENSIONS = {
    ".txt",
    ".md",
    ".csv",
    ".pdf",
    ".docx",
}

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150

DATA_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)
