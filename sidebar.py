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


def normalize_text(value):

    return (
        str(value).lower().strip().replace(".", "").replace("-", " ").replace("_", " ")
    )


def resolve_answer(answer, question_type, options):
    """
    Converts a stored/local answer into something usable
    by the CURRENT Naukri input control.

    Returns None if it cannot safely resolve the answer.
    """

    if answer is None:
        return None

    # ==========================================
    # TEXT
    # ==========================================
    if question_type == "text":
        return str(answer).strip()

    # No options means we cannot validate
    if not options:
        return answer

    # ==========================================
    # CHECKBOX
    # ==========================================
    if question_type == "checkbox":
        if isinstance(answer, list):
            answers = answer
        else:
            answers = [x.strip() for x in str(answer).split(",") if x.strip()]

        resolved = []

        for value in answers:
            for option in options:
                if value.lower() == option.lower():
                    resolved.append(option)
                    break

        return resolved if resolved else None

    # ==========================================
    # RADIO / DROPDOWN
    # ==========================================
    if question_type in ("radio", "dropdown"):
        answer_text = str(answer).strip()

        # FIRST: exact case-insensitive match
        for option in options:
            if answer_text.lower() == option.lower():
                return option

        # SECOND: normalized match
        normalized_answer = normalize_text(answer_text)

        for option in options:
            if normalized_answer == normalize_text(option):
                return option

        # Nothing reliable found
        return None

    return None


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

        if question is None:
            logger.info("No question found.")
            break

        print("\nQuestion :", question)

        # 1. Detect CURRENT input type
        question_type = detect_question_type(driver)

        # 2. Get CURRENT options
        options = get_options(driver)

        logger.info(f"Question Type : {question_type}")
        logger.info(f"Available Options : {options}")

        # 3. Try local knowledge
        answer = get_answer(question)

        if answer is not None:
            logger.info(f"Local Answer : {answer}")

        else:
            # 4. Only use LLM when local answer doesn't exist
            logger.info("No local answer found. Trying LLM...")

            try:
                answer = ask_llm(question, options=options)

                logger.info(f"LLM Answer : {answer}")

                add_to_history(question, answer)

            except Exception as exc:
                logger.exception(exc)
                save_missing_question(question)
                break

        # =========================================
        # 5. RESOLVE ANSWER FOR CURRENT INPUT TYPE
        # ADD THE CODE HERE
        # =========================================

        original_answer = answer

        resolved_answer = resolve_answer(answer, question_type, options)

        # Local answer exists but doesn't match
        # the current radio/dropdown/checkbox options
        if resolved_answer is None:
            logger.warning(
                f"Local answer '{original_answer}' "
                f"does not match current options: {options}"
            )

            logger.info("Trying LLM to select from current options...")

            try:
                resolved_answer = ask_llm(question, options=options)

                logger.info(f"LLM option answer : {resolved_answer}")

                # Validate LLM answer also
                resolved_answer = resolve_answer(
                    resolved_answer, question_type, options
                )

            except Exception as exc:
                logger.exception(exc)
                save_missing_question(question)
                break

        # Still invalid?
        if resolved_answer is None:
            logger.error("Could not resolve a valid answer.")

            save_missing_question(question)
            break

        # From here onwards use resolved_answer
        answer = resolved_answer

        # =========================================
        # 6. HANDLE CHECKBOX
        # =========================================

        if question_type == "checkbox":
            if isinstance(answer, str):
                answer = [answer]

            for value in answer:
                logger.info(f"Selecting checkbox : {value}")

                normalized_target = normalize_text(value)
                found = False

                # Try exact label match first (original behavior)
                try:
                    checkbox = wait.until(
                        EC.element_to_be_clickable(
                            (By.XPATH, f"//label[normalize-space()='{value}']")
                        )
                    )
                    safe_click(driver, checkbox)
                    found = True
                except Exception:
                    # Fallback: iterate all labels and find a normalized match
                    try:
                        labels = driver.find_elements(By.CSS_SELECTOR, "label")
                        for lbl in labels:
                            try:
                                text = lbl.text or ""
                                if not text.strip():
                                    continue

                                # Exact normalized match or choice-range match
                                if normalize_text(text) == normalized_target or (
                                    _normalize_choice(text) == _normalize_choice(value)
                                ):
                                    safe_click(driver, lbl)
                                    found = True
                                    break

                                # Partial containment (e.g., '2-4 years' vs '2-4')
                                if normalized_target in normalize_text(text):
                                    safe_click(driver, lbl)
                                    found = True
                                    break
                            except Exception:
                                continue
                    except Exception:
                        pass

                # Try input element fallback if label matching failed
                if not found:
                    try:
                        input_el = driver.find_element(
                            By.XPATH,
                            (
                                "//input[@type='checkbox' and (normalize-space(@value)=\""
                                + value
                                + "\" or contains(translate(@value,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),\""
                                + value.lower()
                                + '"))]'
                            ),
                        )
                        safe_click(driver, input_el)
                        found = True
                    except Exception:
                        pass

                if not found:
                    logger.warning(f"Could not find checkbox for '{value}'")
                    save_missing_question(question)
                    break

        # =========================================
        # 7. HANDLE RADIO
        # =========================================

        elif question_type == "radio":
            logger.info(f"Selecting radio : {answer}")

            radio = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, f"//label[normalize-space()='{answer}']")
                )
            )

            safe_click(driver, radio)

        # =========================================
        # 8. HANDLE DROPDOWN
        # =========================================

        elif question_type == "dropdown":
            from selenium.webdriver.support.ui import Select

            dropdown = wait.until(
                EC.presence_of_element_located((By.TAG_NAME, "select"))
            )

            Select(dropdown).select_by_visible_text(answer)

        # =========================================
        # 9. HANDLE TEXT
        # =========================================

        elif question_type == "text":
            textbox = wait.until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, "div.textArea[contenteditable='true']")
                )
            )

            textbox.click()

            textbox.send_keys(str(answer))

            logger.info(f"Entered text : {answer}")

        else:
            logger.warning(f"Unknown question type: {question_type}")

            save_missing_question(question)
            break

        # =========================================
        # 10. SAVE ANSWER
        # =========================================

        if not click_save(driver, wait):
            logger.warning("Could not click Save.")
            break

        time.sleep(2)

    logger.info("Sidebar Completed.")
