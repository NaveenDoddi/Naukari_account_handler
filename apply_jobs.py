import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from logger import logger
from sidebar import answer_sidebar, sidebar_visible
from utils import take_screenshot

from selenium.common.exceptions import (
    ElementNotInteractableException,
    ElementClickInterceptedException,
    StaleElementReferenceException,
    TimeoutException,
)


def ensure_recommended_jobs_page(driver, wait):
    driver.get("https://www.naukri.com/mnjuser/recommendedjobs")
    time.sleep(5)


def switch_to_profile_tab(driver, wait):
    profile_tab = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable(
            (By.XPATH, "//div[@id='profile']//div[contains(text(),'Profile')]")
        )
    )

    profile_tab.click()
    time.sleep(5)


def apply_jobs(driver, wait):
    should_stop = False

    logger.info("========== Automation Started ==========")
    logger.info("Browser launched successfully.")
    # switch_to_profile_tab(driver, wait)

    ensure_recommended_jobs_page(driver, wait)

    checkboxes = wait.until(
        EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, "div.saveJobContainer.tuple-check-box")
        )
    )

    selected = 0
    max_jobs = 5

    logger.info(f"Found {len(checkboxes)} job checkboxes.")

    if len(checkboxes) <= max_jobs:
        switch_to_profile_tab(driver, wait)
        logger.info("Continuing after profile-tab switch.")
        
        checkboxes = wait.until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "div.saveJobContainer.tuple-check-box")
            )
        )
        # return False

    for checkbox in checkboxes:
        if selected >= max_jobs:
            break

        try:
            # Skip if already selected
            if checkbox.find_elements(By.CSS_SELECTOR, "i.naukicon-ot-Checked"):
                logger.info("Job already selected. Skipping.")
                continue

            # Scroll into view
            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});", checkbox
            )

            time.sleep(0.3)

            # Skip invisible checkboxes
            if not checkbox.is_displayed():
                logger.info("Checkbox not visible. Skipping.")
                continue

            # Skip disabled/non-interactable checkboxes
            if not checkbox.is_enabled():
                logger.info("Checkbox disabled. Skipping.")
                continue

            # Click using JavaScript (more reliable)
            driver.execute_script("arguments[0].click();", checkbox)

            selected += 1

            logger.info(f"Selected Job {selected}")

            time.sleep(0.5)

        except (
            ElementNotInteractableException,
            ElementClickInterceptedException,
            StaleElementReferenceException,
            TimeoutException,
        ):
            logger.info("Checkbox not clickable. Skipping.")
            continue

        except Exception as e:
            logger.info(f"Skipping checkbox due to: {e}")
            continue

    logger.info(f"Successfully selected {selected} jobs.")

    if selected == 0:
        logger.info("No selectable jobs found.")
        return False

    apply_button = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.multi-apply-button"))
    )

    apply_button.click()

    logger.info("Clicked Apply button.")

    time.sleep(3)

    if sidebar_visible(driver):
        logger.info("Sidebar Detected")

        answer_sidebar(driver, wait)

    else:
        logger.info("Application Submitted Successfully")

    # if selected >= max_jobs:
    #     switch_to_profile_tab(driver, wait)

    logger.info("Automation completed.")

    screenshot = take_screenshot(driver, "completed")

    logger.info(f"Screenshot saved : {screenshot}")
    return should_stop
