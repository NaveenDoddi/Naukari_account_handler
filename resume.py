from pathlib import Path

from config import RESUME_PATH


def get_resume_path():
    return Path(RESUME_PATH)
