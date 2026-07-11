import logging
import os
from datetime import datetime

LOG_FOLDER = "logs"
os.makedirs(LOG_FOLDER, exist_ok=True)

log_file = os.path.join(
    LOG_FOLDER,
    f"{datetime.now().strftime('%Y-%m-%d')}.log"
)

logger = logging.getLogger("AutomationLogger")
logger.setLevel(logging.INFO)

if not logger.handlers:
    file_handler = logging.FileHandler(log_file)
    console_handler = logging.StreamHandler()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )

    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)