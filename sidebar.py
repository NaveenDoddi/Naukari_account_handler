import time
import re

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


def _normalize_choice(text):
    """Normalize option text to a canonical numeric range when possible.

    Examples:
    - '2-4 years' -> '2-4'
    - '2 to 4' -> '2-4'
    - '3' -> '3'
    If no digits are present, returns lowercase stripped text.
    """
    if not text:
        return ""

    nums = re.findall(r"\d+", text)
    if len(nums) >= 2:
        return f"{nums[0]}-{nums[1]}"
    if len(nums) == 1:
        return nums[0]

    return text.strip().lower()


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


def is_dob_question(question):
    if not question:
        return False

    normalized = question.lower().replace("?", "").strip()
    return any(
        keyword in normalized
        for keyword in ["date of birth", "dob", "birth date", "birthday"]
    )


def detect_question_type(driver, question=None):

    # Multi Checkbox
    if driver.find_elements(By.CSS_SELECTOR, "div.multiselectcheckboxes"):
        return "checkbox"

    # Radio Button
    if driver.find_elements(By.CSS_SELECTOR, "div.singleselect-radiobutton"):
        return "radio"

    # Dropdown
    if driver.find_elements(By.TAG_NAME, "select"):
        return "dropdown"

    # Custom DOB widget
    if is_dob_question(question) or driver.find_elements(
        By.CSS_SELECTOR, "input[name='day'], input[name='month'], input[name='year']"
    ):
        return "dob"

    # Visible Textbox / input fields
    text_selectors = [
        "div.textArea[contenteditable='true']",
        "textarea",
        "input[type='text']",
        "input[type='date']",
        "input[type='email']",
        "input:not([type])",
    ]

    for selector in text_selectors:
        for element in driver.find_elements(By.CSS_SELECTOR, selector):
            if element.is_displayed() and element.is_enabled():
                return "text"

    return "unknown"


def fill_text_answer(driver, element, answer):
    element.click()

    try:
        element.clear()
    except Exception:
        try:
            driver.execute_script("arguments[0].innerText = '';", element)
        except Exception:
            pass

    element.send_keys(str(answer))


def fill_dob_answer(driver, wait, answer):
    try:
        parts = []
        for token in str(answer).replace("-", "/").split("/"):
            token = token.strip()
            if token:
                parts.append(token)

        if len(parts) != 3:
            raise ValueError("Answer was not in DD/MM/YYYY format")

        day, month, year = parts[0], parts[1], parts[2]

        field_map = {
            "day": wait.until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "input[name='day']"))
            ),
            "month": wait.until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, "input[name='month']")
                )
            ),
            "year": wait.until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, "input[name='year']")
                )
            ),
        }

        for key, value in [("day", day), ("month", month), ("year", year)]:
            element = field_map[key]
            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});", element
            )
            element.clear()
            element.send_keys(str(value))

        return True
    except Exception as exc:
        logger.warning(f"Could not fill DOB fields: {exc}")
        return False


def answer_sidebar(driver, wait):

    while sidebar_visible(driver):
        question = get_question(driver)
        options = get_options(driver)
        # Try local knowledge (Rule Engine + Semantic Search)
        answer = get_answer(question)

        if answer:
            logger.info(f"Local Answer : {answer}")

        else:
            logger.info("No local answer found. Trying LLM...")

            try:
                answer = ask_llm(question, options=options)

                logger.info(f"LLM Answer : {answer}")

                # Save new question only if LLM was used
                add_to_history(question, answer)

            except Exception as exc:
                logger.exception(exc)

                save_missing_question(question)

                break

        add_to_history(question, answer)

        question_type = detect_question_type(driver, question)

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

                checkbox = None

                # Try exact-match XPath first (fastest)
                try:
                    checkbox = wait.until(
                        EC.element_to_be_clickable(
                            (By.XPATH, f"//label[normalize-space()='{value}']")
                        )
                    )
                except Exception:
                    # Fallback: scan all labels and match text more leniently
                    labels = driver.find_elements(By.TAG_NAME, "label")
                    for lab in labels:
                        try:
                            text = lab.text.strip()
                        except Exception:
                            continue

                        if not text:
                            continue

                        # Normalize numeric ranges (e.g. '2-4 years' -> '2-4')
                        lab_norm = _normalize_choice(text)
                        val_norm = _normalize_choice(value)

                        if (
                            text == value
                            or text.lower() == value.lower()
                            or value.lower() in text.lower()
                            or lab_norm == val_norm
                            or lab_norm in val_norm
                            or val_norm in lab_norm
                        ):
                            checkbox = lab
                            break

                if checkbox is None:
                    logger.warning(f"Could not find checkbox for value: {value}")
                    continue

                # If label contains an <input>, prefer clicking the input element
                try:
                    input_el = checkbox.find_element(By.TAG_NAME, "input")
                except Exception:
                    input_el = None

                target = input_el if input_el is not None else checkbox

                driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});", target
                )

                safe_click(driver, target)

        # ===========================
        # RADIO BUTTON
        # ===========================
        elif question_type == "radio":
            logger.info(f"Selecting radio : {answer}")

            radio = None

            try:
                radio = wait.until(
                    EC.element_to_be_clickable(
                        (By.XPATH, f"//label[normalize-space()='{answer}']")
                    )
                )
            except Exception:
                labels = driver.find_elements(By.TAG_NAME, "label")
                for lab in labels:
                    try:
                        text = lab.text.strip()
                    except Exception:
                        continue

                    if not text:
                        continue

                    lab_norm = _normalize_choice(text)
                    ans_norm = _normalize_choice(answer)

                    if (
                        text == answer
                        or text.lower() == answer.lower()
                        or answer.lower() in text.lower()
                        or lab_norm == ans_norm
                        or lab_norm in ans_norm
                        or ans_norm in lab_norm
                    ):
                        radio = lab
                        break

            if radio is None:
                logger.warning(f"Could not find radio option for value: {answer}")
            else:
                try:
                    input_el = radio.find_element(By.TAG_NAME, "input")
                except Exception:
                    input_el = None

                target = input_el if input_el is not None else radio

                driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});", target
                )

                safe_click(driver, target)

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
        # DATE OF BIRTH
        # ===========================
        elif question_type == "dob":
            if not fill_dob_answer(driver, wait, answer):
                logger.warning("DOB fields could not be filled.")
                save_missing_question(question)
                break

            logger.info(f"Entered DOB : {answer}")

        # ===========================
        # TEXTBOX
        # ===========================
        elif question_type == "text":
            textbox = None
            for selector in [
                "div.textArea[contenteditable='true']:not(.d-none)",
                "textarea",
                "input[type='text']",
                "input[type='date']",
                "input[type='email']",
                "input:not([type])",
            ]:
                try:
                    textbox = wait.until(
                        EC.visibility_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    if textbox.is_displayed() and textbox.is_enabled():
                        break
                except TimeoutException:
                    continue
                except Exception:
                    continue

            if textbox is None:
                logger.warning("No visible text input found for the question.")
                save_missing_question(question)
                break

            fill_text_answer(driver, textbox, answer)

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
