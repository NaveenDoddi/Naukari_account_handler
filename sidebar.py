import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    TimeoutException,
)

from knowledge import add_to_history, get_answer, save_missing_question
from logger import logger
from llm import ask_llm


def safe_click(driver, element):
    """Attempt to click an element safely, falling back to JS click if intercepted."""
    try:
        element.click()
        return
    except ElementClickInterceptedException:
        try:
            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});", element
            )
            driver.execute_script("arguments[0].click();", element)
            return
        except Exception:
            try:
                from selenium.webdriver.common.action_chains import ActionChains

                ActionChains(driver).move_to_element(element).click().perform()
                return
            except Exception:
                logger.exception("Failed to click element using fallbacks.")
                raise


# Messages that are NOT questions
IGNORE_MESSAGES = [
    "thank you for showing interest",
    "kindly answer all the recruiter's questions",
    "application submitted",
    "thank you",
    "welcome",
]


def sidebar_visible(driver):
    return (
        len(driver.find_elements(By.CSS_SELECTOR, "div.chatbot_DrawerContentWrapper"))
        > 0
    )


def get_question(driver):
    """
    Returns the latest actual question from the chatbot.
    Skips greeting/information messages.
    """

    messages = driver.find_elements(By.CSS_SELECTOR, "li.botItem div.botMsg span")

    # Traverse from latest to oldest
    for message in reversed(messages):
        text = message.text.strip()

        if not text:
            continue

        lower = text.lower()

        # Ignore greeting messages
        if any(ignore in lower for ignore in IGNORE_MESSAGES):
            continue

        logger.info(f"Question Extracted: {text}")

        return text

    return None


def get_options(driver):

    # Checkbox options
    labels = driver.find_elements(By.CSS_SELECTOR, "label.mcc__label")

    if labels:
        return [i.text.strip() for i in labels]

    # Radio options
    labels = driver.find_elements(By.CSS_SELECTOR, "label.ssrc__label")

    if labels:
        return [i.text.strip() for i in labels]

    # Dropdown options
    selects = driver.find_elements(By.TAG_NAME, "select")

    if selects:
        from selenium.webdriver.support.ui import Select

        options = Select(selects[0]).options

        return [o.text.strip() for o in options]

    return []


def click_save(driver, wait):
    save_xpaths = [
        "//div[contains(@class,'sendMsg') and normalize-space()='Save']",
        "//div[contains(@class,'sendMsg') and normalize-space()='Submit']",
        "//div[contains(@class,'sendMsg') and normalize-space()='Continue']",
        "//div[contains(@class,'sendMsg') and normalize-space()='Done']",
        "//button[normalize-space()='Save']",
        "//button[normalize-space()='Submit']",
        "//button[normalize-space()='Continue']",
        "//button[normalize-space()='Done']",
        "//button[contains(@class,'sendMsg') or contains(@class,'submit') or contains(@class,'continue') or contains(@class,'done')]",
        "//div[contains(@class,'sendMsg') or contains(@class,'submit') or contains(@class,'continue') or contains(@class,'done')]",
    ]

    for xpath in save_xpaths:
        try:
            button = wait.until(EC.visibility_of_element_located((By.XPATH, xpath)))
            if button.is_displayed():
                safe_click(driver, button)
                time.sleep(2)
                return True
        except TimeoutException:
            continue
        except Exception:
            continue

    # Fallback: try to find any visible save/submit-like button by text
    candidates = driver.find_elements(
        By.XPATH,
        "//button|//div[contains(@class,'sendMsg') or contains(@class,'submit') or contains(@class,'continue') or contains(@class,'done')]",
    )
    for candidate in candidates:
        try:
            if candidate.is_displayed():
                safe_click(driver, candidate)
                time.sleep(2)
                return True
        except Exception:
            continue

    logger.info("No save/submit button found. Continuing without clicking save.")
    return False


def detect_question_type(driver):

    # Multi Checkbox
    if driver.find_elements(By.CSS_SELECTOR, "div.multiselectcheckboxes"):
        return "checkbox"

    # Radio Button
    if driver.find_elements(By.CSS_SELECTOR, "div.singleselect-radiobutton"):
        return "radio"

    # Dropdown
    if driver.find_elements(By.TAG_NAME, "select"):
        return "dropdown"

    # Visible Textbox
    textboxes = driver.find_elements(
        By.CSS_SELECTOR, "div.textArea[contenteditable='true']"
    )

    for tb in textboxes:
        if tb.is_displayed():
            return "text"

    return "unknown"


def answer_sidebar(driver, wait):

    while sidebar_visible(driver):
        question = get_question(driver)

        if question is None:
            logger.info("No question found.")
            break

        print("\nQuestion :", question)

        answer = get_answer(question)

        if answer is None:
            logger.info("No answer found in knowledge base. Trying LLM...")

            options = get_options(driver)

            try:
                # Pass extracted options to the LLM so it chooses from them directly
                answer = ask_llm(question, options=options)

                logger.info(f"LLM Answer : {answer}")

            except Exception as exc:
                logger.exception(exc)

                save_missing_question(question)

                break

        add_to_history(question, answer)

        question_type = detect_question_type(driver)

        logger.info(f"Question Type : {question_type}")

        # ===========================
        # CHECKBOX
        # ===========================
        if question_type == "checkbox":
            if isinstance(answer, str):
                # Allow the LLM to return multiple choices separated by commas
                if "," in answer:
                    answer = [a.strip() for a in answer.split(",") if a.strip()]
                else:
                    answer = [answer]

            for value in answer:
                logger.info(f"Selecting checkbox : {value}")

                checkbox = wait.until(
                    EC.element_to_be_clickable(
                        (By.XPATH, f"//label[normalize-space()='{value}']")
                    )
                )

                driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});", checkbox
                )

                safe_click(driver, checkbox)

        # ===========================
        # RADIO BUTTON
        # ===========================
        elif question_type == "radio":
            logger.info(f"Selecting radio : {answer}")

            radio = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, f"//label[normalize-space()='{answer}']")
                )
            )

            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});", radio
            )

            safe_click(driver, radio)

        # ===========================
        # DROPDOWN
        # ===========================
        elif question_type == "dropdown":
            from selenium.webdriver.support.ui import Select

            dropdown = wait.until(
                EC.presence_of_element_located((By.TAG_NAME, "select"))
            )

            Select(dropdown).select_by_visible_text(answer)

            logger.info(f"Dropdown Selected : {answer}")

        # ===========================
        # TEXTBOX
        # ===========================
        elif question_type == "text":
            textbox = wait.until(
                EC.visibility_of_element_located(
                    (
                        By.CSS_SELECTOR,
                        "div.textArea[contenteditable='true']:not(.d-none)",
                    )
                )
            )

            textbox.click()

            textbox.clear()

            textbox.send_keys(str(answer))

            logger.info(f"Entered text : {answer}")

        # ===========================
        # UNKNOWN
        # ===========================
        else:
            logger.warning("Unknown question type.")

            save_missing_question(question)

            break

        if not click_save(driver, wait):
            logger.info(
                "Save button was not found after answering. Checking sidebar state."
            )
            time.sleep(2)
            if sidebar_visible(driver):
                logger.warning(
                    "Sidebar still visible but no save action available. Ending sidebar flow."
                )
            break

        time.sleep(2)

        if not click_save(driver, wait):
            logger.info("Final save/submit button was not found. Ending sidebar flow.")
            break

        time.sleep(2)

    logger.info("Sidebar Completed.")
