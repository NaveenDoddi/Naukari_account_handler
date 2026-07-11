import os
from datetime import datetime

from login import get_driver, login_user, is_login_page
import config
from logger import logger
from utils import take_screenshot
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time


DAILY_MARKER_PATH = os.path.join("logs", "resume_update_marker.txt")


def should_update_resume_today():
    if not os.path.exists(DAILY_MARKER_PATH):
        return True

    with open(DAILY_MARKER_PATH, "r", encoding="utf-8") as handle:
        try:
            last_run_date = handle.read().strip()
        except Exception:
            return True

    return last_run_date != datetime.now().strftime("%Y-%m-%d")


def mark_resume_updated_today():
    with open(DAILY_MARKER_PATH, "w", encoding="utf-8") as handle:
        handle.write(datetime.now().strftime("%Y-%m-%d"))


def main():
    logger.info("========== Automation Started ==========")

    driver = None

    try:
        driver = get_driver(config.HEADLESS)

        wait = WebDriverWait(driver, 20)

        logger.info("Browser launched successfully.")

        if not should_update_resume_today():
            logger.info("Resume update already done today. Skipping.")
            return

        def ensure_profile_page():
            driver.get("https://www.naukri.com/mnjuser/profile")
            time.sleep(5)

            if is_login_page(driver, wait):
                logger.info("User not logged in; performing login.")
                login_user(driver, wait, config.EMAIL, config.PASSWORD)
                driver.get("https://www.naukri.com/mnjuser/profile")
                time.sleep(5)
            else:
                logger.info("Already logged in; now on profile page.")

        ensure_profile_page()

        delete_button = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "span[data-title='delete-resume']")
            )
        )

        delete_button.click()
        time.sleep(2)

        # print(driver.page_source)

        wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "div.lightbox.model_open")
            )
        )

        # Click Delete button
        delete_confirm_button = wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//div[contains(@class,'model_open')]//button[normalize-space()='Delete']",
                )
            )
        )
        time.sleep(2)

        delete_confirm_button.click()
        time.sleep(5)

        file_input = wait.until(EC.presence_of_element_located((By.ID, "attachCV")))

        file_input.send_keys(str(config.RESUME_PATH))
        time.sleep(30)
        # # -----------------------------------------------------

        mark_resume_updated_today()
        logger.info("Automation steps completed successfully.")

        screenshot = take_screenshot(driver, "completed")
        logger.info(f"Screenshot saved : {screenshot}")

    except Exception as e:
        logger.exception("Automation failed.")

        if driver:
            screenshot = take_screenshot(driver, "error")
            logger.error(f"Failure screenshot : {screenshot}")

    finally:
        if driver:
            driver.quit()

        logger.info("Browser closed.")
        logger.info("========== Automation Finished ==========\n")


if __name__ == "__main__":
    main()
