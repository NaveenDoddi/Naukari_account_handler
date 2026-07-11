import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from knowledge import add_to_history, get_answer, save_missing_question
from logger import logger
from llm import ask_llm


def sidebar_visible(driver):
    return (
        len(driver.find_elements(By.CSS_SELECTOR, "div.chatbot_DrawerContentWrapper"))
        > 0
    )


def get_question(driver):
    return driver.find_element(
        By.CSS_SELECTOR, "li.botItem div.botMsg span"
    ).text.strip()


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
        print("\nQuestion :", question)

        answer = get_answer(question)

        if answer is None:
            print("No answer found in knowledge base. Trying LLM fallback...")
            try:
                answer = ask_llm(question)
                print("LLM answer:", answer)
            except Exception as exc:
                logger.exception("LLM fallback failed: %s", exc)
                save_missing_question(question)
                break

        add_to_history(question, answer)

        options = get_options(driver)

        if len(options) > 0:
            if isinstance(answer, str):
                answer = [answer]
            for value in answer:
                wait.until(
                    EC.element_to_be_clickable(
                        (By.XPATH, f"//label[normalize-space()='{value}']")
                    )
                ).click()
        else:
            textbox = wait.until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, "div.textArea[contenteditable='true']")
                )
            )
            textbox.click()
            textbox.send_keys(answer)

        click_save(driver, wait)
        time.sleep(2)

    print("Sidebar Completed.")
