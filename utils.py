import os
from datetime import datetime


SCREENSHOT_FOLDER = "screenshots"
os.makedirs(SCREENSHOT_FOLDER, exist_ok=True)


def take_screenshot(driver, name="screenshot"):
    filename = f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    path = os.path.join(SCREENSHOT_FOLDER, filename)

    driver.save_screenshot(path)

    return path


def wait(seconds):
    import time
    time.sleep(seconds)