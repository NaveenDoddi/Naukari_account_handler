from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
EMBEDDINGS_PATH = BASE_DIR / "knowledge" / "embeddings.faiss"


def get_embeddings_path():
    return EMBEDDINGS_PATH
