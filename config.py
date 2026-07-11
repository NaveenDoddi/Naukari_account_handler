from pathlib import Path
import os


def _load_env_file():
    env_path = Path(__file__).resolve().parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file()

EMAIL = os.getenv("EMAIL", "")
PASSWORD = os.getenv("PASSWORD", "")

RESUME_PATH = Path(
    "C:\\Users\\reddy\\naukariUpdate\\Naveen_python_developer.pdf"
).resolve()

HEADLESS = False
WAIT_TIME = 15
