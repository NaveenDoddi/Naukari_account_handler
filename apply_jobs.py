import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from logger import logger
from sidebar import answer_sidebar, sidebar_visible
from utils import take_screenshot


def ensure_recommended_jobs_page(driver, wait):
    driver.get("https://www.naukri.com/mnjuser/recommendedjobs")
    time.sleep(5)


def apply_jobs(driver, wait):
    logger.info("========== Automation Started ==========")
    logger.info("Browser launched successfully.")

    ensure_recommended_jobs_page(driver, wait)

    checkboxes = wait.until(
        EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, "div.saveJobContainer.tuple-check-box")
        )
    )
    for i in range(5):
        checkboxes[i].click()
        time.sleep(1)

    apply_button = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.multi-apply-button"))
    )
    apply_button.click()
    time.sleep(3)

    if sidebar_visible(driver):
        logger.info("Sidebar Detected")
        answer_sidebar(driver, wait)
    else:
        logger.info("Application Submitted Successfully")

    logger.info("Automation completed.")
    screenshot = take_screenshot(driver, "completed")
    logger.info(f"Screenshot saved : {screenshot}")
