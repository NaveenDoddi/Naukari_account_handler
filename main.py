import time

from selenium.webdriver.support.ui import WebDriverWait

from apply_jobs import apply_jobs
from config import EMAIL, HEADLESS, PASSWORD, WAIT_TIME
from logger import logger
from login import get_driver, login_user, is_login_page


def main():
    driver = None
    try:
        driver = get_driver(HEADLESS)
        wait = WebDriverWait(driver, WAIT_TIME)

        driver.get("https://www.naukri.com/mnjuser/recommendedjobs")
        time.sleep(5)

        # if is_login_page(driver, wait):
        #     logger.info("User not logged in. Performing login...")
        #     login_user(driver, wait, EMAIL, PASSWORD)
        #     driver.get("https://www.naukri.com/mnjuser/recommendedjobs")
        #     time.sleep(5)
        # else:
        #     logger.info("User already logged in. Continuing to recommended jobs...")

        apply_jobs(driver, wait)
        logger.info("Automation run completed.")
    except Exception as exc:
        logger.exception("Automation failed: %s", exc)
    finally:
        if driver:
            driver.quit()
        time.sleep(50)
        logger.info("========== Automation Finished ==========")


if __name__ == "__main__":
    main()
