import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROFILE_PATH = BASE_DIR / "knowledge" / "profile.json"


def load_profile():
    with PROFILE_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)
