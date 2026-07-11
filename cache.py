import json
from pathlib import Path

CACHE_PATH = Path(__file__).resolve().parent / "knowledge" / "history.json"


def read_cache():
    if not CACHE_PATH.exists():
        return []
    with CACHE_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)
