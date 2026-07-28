import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from logger import logger
from sidebar import answer_sidebar, sidebar_visible
from utils import take_screenshot

from selenium.common.exceptions import (
    ElementNotInteractableException,
    ElementClickInterceptedException,
    StaleElementReferenceException,
    TimeoutException,
)


def navigate_to_recommended_jobs_page(driver, wait):
    driver.get("https://www.naukri.com/mnjuser/recommendedjobs")
    time.sleep(5)


def switch_to_tab(driver, wait, tab_id):
    logger.info(f"Switching to tab '{tab_id}'.")
    selectors = [
        f"div.tabs-container div.tab-wrapper#{tab_id}",
        f"div.tabs-container div.tab-wrapper#{tab_id} div.tab-list-item",
        f"div.tab-wrapper#{tab_id}",
        f"div.tab-wrapper#{tab_id} div.tab-list-item",
    ]

    tab = None
    for selector in selectors:
        try:
            tab = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            if tab is not None:
                break
        except TimeoutException:
            continue

    if tab is None:
        logger.warning(
            "Could not find tab element for '%s'. Skipping this tab.", tab_id
        )
        return False

    try:
        driver.execute_script("arguments[0].scrollIntoView(true);", tab)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", tab)
    except Exception as exc:
        logger.warning(
            "JS click failed for tab '%s': %s. Trying native click.", tab_id, exc
        )
        try:
            tab.click()
        except Exception as exc2:
            logger.warning(
                "Native click also failed for tab '%s': %s. Skipping this tab.",
                tab_id,
                exc2,
            )
            return False

    time.sleep(2)
    return True


def apply_jobs_in_current_tab(driver, wait, max_jobs=10):
    logger.info("Scanning current tab for jobs to apply.")
    time.sleep(2)

    checkboxes = driver.find_elements(
        By.CSS_SELECTOR, "div.saveJobContainer.tuple-check-box"
    )
    if not checkboxes:
        logger.info("No job checkboxes found in current tab. Moving to next tab.")
        return 0

    logger.info(f"Found {len(checkboxes)} job checkboxes in current tab.")

    selected = 0

    for checkbox in checkboxes:
        if selected >= max_jobs:
            break

        try:
            if checkbox.find_elements(By.CSS_SELECTOR, "i.naukicon-ot-Checked"):
                logger.info("Job already selected. Skipping.")
                continue

            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});", checkbox
            )
            time.sleep(0.3)

            if not checkbox.is_displayed():
                logger.info("Checkbox not visible. Skipping.")
                continue

            if not checkbox.is_enabled():
                logger.info("Checkbox disabled. Skipping.")
                continue

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

    logger.info(f"Selected {selected} jobs in current tab.")

    if selected == 0:
        logger.info("No selectable jobs found in current tab.")
        return 0

    apply_button = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.multi-apply-button"))
    )

    driver.execute_script("arguments[0].click();", apply_button)
    logger.info("Clicked Apply button.")
    time.sleep(3)

    if sidebar_visible(driver):
        logger.info("Sidebar detected; answering required questions.")
        answer_sidebar(driver, wait)
    else:
        logger.info("Application submitted successfully.")

    screenshot = take_screenshot(driver, f"completed_{int(time.time())}")
    logger.info(f"Screenshot saved : {screenshot}")
    return selected


def apply_jobs(driver, wait):
    logger.info("========== Automation Started ==========")
    logger.info("Browser launched successfully.")

    navigate_to_recommended_jobs_page(driver, wait)

    tab_sequence = [
        ("apply", "Recommended"),
        ("profile", "Profile"),
        ("top_candidate", "Top Candidate"),
        ("preference", "Preferences"),
    ]

    total_applied = 0

    for tab_id, tab_name in tab_sequence:
        if tab_id != "apply":
            switched = switch_to_tab(driver, wait, tab_id)
            if not switched:
                logger.info(
                    "Skipping tab '%s' because it could not be selected.", tab_name
                )
                continue

        applied_in_tab = apply_jobs_in_current_tab(driver, wait, max_jobs=10)
        total_applied += applied_in_tab

        logger.info(f"Applied {applied_in_tab} jobs in '{tab_name}' tab.")

        # If we applied any jobs, the site may navigate to a confirmation
        # page. Ensure we return to the recommended jobs listing before
        # continuing to the next tab so selectors remain consistent.
        if applied_in_tab > 0:
            logger.info("Returning to recommended jobs page after apply batch.")
            try:
                navigate_to_recommended_jobs_page(driver, wait)
            except Exception:
                logger.exception(
                    "Failed to navigate back to recommended jobs page after applying."
                )
        if applied_in_tab < 10:
            logger.info(
                f"Fewer than 10 jobs were applied in '{tab_name}'. Moving to the next tab."
            )

    logger.info(f"Total applied jobs across tabs: {total_applied}")
    logger.info("Automation completed.")
    return total_applied > 0
