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
    logger.info("Switching to tab '%s'.", tab_id)
    selector = f"div.tab-wrapper#{tab_id} .tab-list-item"
    try:
        tab = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
    except Exception:
        try:
            tab = driver.find_element(By.CSS_SELECTOR, selector)
        except Exception:
            logger.warning("Could not find tab element for '%s'.", tab_id)
            return False

    try:
        driver.execute_script("arguments[0].scrollIntoView(true);", tab)
        time.sleep(0.3)
        driver.execute_script("arguments[0].click();", tab)
    except Exception as exc:
        logger.warning("Failed to click tab '%s': %s", tab_id, exc)
        try:
            tab.click()
        except Exception as exc2:
            logger.warning("Native click failed for tab '%s': %s", tab_id, exc2)
            return False

    time.sleep(2)
    active_selector = f"div.tab-wrapper#{tab_id} .tab-list-item.tab-list-active"
    active_tabs = driver.find_elements(By.CSS_SELECTOR, active_selector)
    if not active_tabs:
        logger.warning("Tab '%s' did not become active after click.", tab_id)
        return False

    return True


def _find_job_click_target(container):
    selectors = [
        "label",
        "input[type='checkbox']",
        "button",
        "[role='checkbox']",
        "span",
        "div",
    ]

    candidates = []
    for selector in selectors:
        try:
            candidates.extend(container.find_elements(By.CSS_SELECTOR, selector))
        except Exception:
            continue

    for candidate in candidates:
        try:
            if candidate.is_displayed() and candidate.is_enabled():
                return candidate
        except Exception:
            continue

    try:
        if container.is_displayed() and container.is_enabled():
            return container
    except Exception:
        pass

    return candidates[0] if candidates else container


def apply_jobs_in_current_tab(driver, wait, max_jobs=5):
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

            click_target = _find_job_click_target(checkbox)
            logger.info(
                "Using click target %s for job checkbox.",
                click_target.get_attribute("outerHTML")[:200]
                if click_target is not None
                else "<none>",
            )

            if not click_target.is_displayed():
                logger.info("Checkbox not visible. Skipping.")
                continue

            if not click_target.is_enabled():
                logger.info("Checkbox disabled. Skipping.")
                continue

            driver.execute_script("arguments[0].click();", click_target)
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
        sidebar_success = answer_sidebar(driver, wait)
        if not sidebar_success:
            logger.warning("Sidebar interaction failed before completion.")
            screenshot = take_screenshot(driver, f"sidebar_failed_{int(time.time())}")
            logger.info(f"Failure screenshot saved : {screenshot}")
        else:
            logger.info("Sidebar interaction completed successfully.")
            screenshot = take_screenshot(driver, f"completed_{int(time.time())}")
            logger.info(f"Screenshot saved : {screenshot}")
    else:
        logger.info("Application submitted successfully.")
        screenshot = take_screenshot(driver, f"completed_{int(time.time())}")
        logger.info(f"Screenshot saved : {screenshot}")
    return selected


def apply_jobs(driver, wait):
    logger.info("========== Automation Started ==========")
    logger.info("Browser launched successfully.")

    navigate_to_recommended_jobs_page(driver, wait)

    total_applied = apply_jobs_in_current_tab(driver, wait, max_jobs=5)
    logger.info(f"Applied {total_applied} jobs on the current page.")

    if switch_to_tab(driver, wait, "profile"):
        logger.info("Switched to profile tab after apply phase.")
        profile_applied = apply_jobs_in_current_tab(driver, wait, max_jobs=5)
        total_applied += profile_applied
        logger.info(f"Applied {profile_applied} jobs on the profile tab.")
    else:
        logger.warning("Could not switch to profile tab after apply phase.")

    logger.info("Automation completed.")
    return total_applied > 0
