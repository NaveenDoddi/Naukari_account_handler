import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from knowledge import add_to_history, get_answer, save_missing_question
from logger import logger
from llm import ask_llm


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
    labels = driver.find_elements(By.CSS_SELECTOR, "label.mcc__label")

    return [i.text.strip() for i in labels]


def click_save(driver, wait):
    save = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//div[@class='sendMsg' and normalize-space()='Save']")
        )
    )

    save.click()

    time.sleep(2)


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
                answer = ask_llm(question)

                logger.info(f"LLM Answer : {answer}")

            except Exception as exc:
                logger.exception(exc)

                save_missing_question(question)

                break

        add_to_history(question, answer)

        options = get_options(driver)

        # Checkbox Question
        if options:
            if isinstance(answer, str):
                answer = [answer]

            for value in answer:
                wait.until(
                    EC.element_to_be_clickable(
                        (By.XPATH, f"//label[normalize-space()='{value}']")
                    )
                ).click()

        # Text Question
        else:
            textbox = wait.until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, "div.textArea[contenteditable='true']")
                )
            )

            textbox.clear()

            textbox.send_keys(answer)

        click_save(driver, wait)

        time.sleep(2)

    logger.info("Sidebar Completed.")
