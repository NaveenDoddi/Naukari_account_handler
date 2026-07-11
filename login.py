import os
import tempfile
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    TimeoutException,
)
from webdriver_manager.chrome import ChromeDriverManager
import time


def get_driver(headless=False):
    options = webdriver.ChromeOptions()

    options.add_argument("--disable-extensions")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--remote-allow-origins=*")
    options.add_experimental_option(
        "excludeSwitches", ["enable-automation", "enable-logging"]
    )
    options.add_experimental_option("useAutomationExtension", False)

    user_data_dir = os.getenv("CHROME_USER_DATA_DIR")
    profile_dir = os.getenv("CHROME_PROFILE_DIR")

    if user_data_dir:
        options.add_argument(f"--user-data-dir={user_data_dir}")
    elif not headless:
        temp_profile_dir = Path(tempfile.gettempdir()) / "naukari_automation_profile"
        temp_profile_dir.mkdir(parents=True, exist_ok=True)
        options.add_argument(f"--user-data-dir={temp_profile_dir}")

    if profile_dir:
        options.add_argument(f"--profile-directory={profile_dir}")

    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")
    else:
        options.add_argument("--start-maximized")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options,
    )

    return driver


def _wait_for_any_element(driver, wait, selectors, timeout=15):
    last_error = None

    for selector in selectors:
        try:
            return wait.until(EC.visibility_of_element_located(selector))
        except TimeoutException as exc:
            last_error = exc

    if last_error is not None:
        raise last_error

    raise TimeoutException("Could not find login form element")


def is_login_page(driver, wait):
    if "nlogin/login" in driver.current_url:
        return True

    try:
        wait.until(EC.visibility_of_element_located((By.ID, "usernameField")))
        return True
    except TimeoutException:
        return False


def login_user(driver, wait, email, password):
    if not email or not password:
        raise ValueError("EMAIL and PASSWORD must be set in config")

    driver.get("https://www.naukri.com/nlogin/login")
    time.sleep(3)

    wait.until(
        lambda d: (
            "nlogin/login" in d.current_url.lower()
            or "naukri.com" in d.current_url.lower()
        )
    )

    email_input = _wait_for_any_element(
        driver,
        wait,
        [
            (By.ID, "usernameField"),
            (By.NAME, "username"),
            (By.NAME, "email"),
            (By.ID, "email"),
            (By.CSS_SELECTOR, "input[type='email']"),
            (By.CSS_SELECTOR, "input[placeholder*='email' i]"),
        ],
        timeout=15,
    )
    email_input.clear()
    email_input.send_keys(email)

    password_input = _wait_for_any_element(
        driver,
        wait,
        [
            (By.ID, "passwordField"),
            (By.NAME, "password"),
            (By.CSS_SELECTOR, "input[type='password']"),
        ],
        timeout=15,
    )
    password_input.clear()
    password_input.send_keys(password)

    login_button = _wait_for_any_element(
        driver,
        wait,
        [
            (By.XPATH, "//button[@type='submit']"),
            (
                By.XPATH,
                "//button[contains(@class, 'login') or normalize-space()='Login']",
            ),
            (By.CSS_SELECTOR, "button[type='submit']"),
        ],
        timeout=15,
    )

    try:
        login_button.click()
    except ElementClickInterceptedException:
        driver.execute_script("arguments[0].click();", login_button)

    time.sleep(5)
