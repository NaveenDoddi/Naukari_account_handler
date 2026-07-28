import os
import tempfile
import time
from pathlib import Path

from selenium.webdriver.support.ui import WebDriverWait

from apply_jobs import apply_jobs
from config import EMAIL, HEADLESS, PASSWORD, WAIT_TIME
from logger import logger
from login import get_driver, login_user, is_login_page


def get_fresh_driver(headless=False):
    profile_dir = Path(
        tempfile.mkdtemp(prefix="naukri_main_", dir=tempfile.gettempdir())
    )
    os.environ["CHROME_USER_DATA_DIR"] = str(profile_dir)
    os.environ["CHROME_PROFILE_DIR"] = "Default"
    logger.info("Using fresh browser profile for main automation run.")
    return get_driver(headless)


def run_once(driver, wait):
    """Run a single automation iteration using an existing driver.

    On error, try to recover by navigating back to the recommended jobs page
    instead of quitting the browser.
    Returns True on success, False on handled error (recovered), and may
    raise if recovery is impossible.
    """
    try:
        logger.info("Using existing signed-in session.")
        driver.get("https://www.naukri.com/mnjuser/recommendedjobs")
        time.sleep(5)

        apply_jobs(driver, wait)
        logger.info("Automation run completed.")
        return True
    except Exception as exc:
        logger.exception("Automation failed: %s", exc)

        # Attempt a lightweight recovery: navigate back to the recommended jobs page
        try:
            logger.info("Attempting recovery: redirecting to recommended jobs page...")
            driver.get("https://www.naukri.com/mnjuser/recommendedjobs")
            # shorter wait for recovery
            time.sleep(5)
            return False
        except Exception:
            logger.exception("Recovery navigation failed; browser may be unusable.")
            # Let caller recreate the browser
            raise


def ensure_logged_in(driver, wait):
    driver.get("https://www.naukri.com/mnjuser/recommendedjobs")
    time.sleep(5)

    if is_login_page(driver, wait):
        logger.info("Session not signed in, performing login.")
        login_user(driver, wait, EMAIL, PASSWORD)
        driver.get("https://www.naukri.com/mnjuser/recommendedjobs")
        time.sleep(5)
    else:
        logger.info("Already signed in, continuing automation.")


def main(loop: bool = True, interval: int = 10):
    driver = None
    wait = None

    try:
        # Create a single browser instance and reuse across iterations
        driver = get_fresh_driver(HEADLESS)
        wait = WebDriverWait(driver, WAIT_TIME)
        ensure_logged_in(driver, wait)

        while True:
            try:
                success = run_once(driver, wait)
            except Exception:
                # Driver appears unusable; recreate it and continue
                try:
                    if driver:
                        driver.quit()
                except Exception:
                    pass

                logger.info("Recreating browser instance after failure...")
                driver = get_fresh_driver(HEADLESS)
                wait = WebDriverWait(driver, WAIT_TIME)
                ensure_logged_in(driver, wait)
                # Short pause before retrying
                time.sleep(5)
                continue

            logger.info("========== Automation Finished ==========")

            if not loop:
                break

            logger.info(f"Sleeping {interval} seconds before next run...")
            time.sleep(interval)
    except KeyboardInterrupt:
        logger.info("Interrupted by user. Exiting loop.")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--once", action="store_true", help="Run a single automation iteration and exit"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=50,
        help="Seconds to wait between runs when looping",
    )
    args = parser.parse_args()

    main(loop=not args.once, interval=args.interval)
