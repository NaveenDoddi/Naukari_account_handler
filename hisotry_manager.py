import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

HISTORY_FILE = BASE_DIR / "knowledge" / "history.json"


def save_history(question, answer):

    history = json.load(open(HISTORY_FILE, encoding="utf-8"))

    for item in history:
        if item["question"].lower() == question.lower():
            item["answer"] = answer

            break

    else:
        history.append({"question": question, "answer": answer})

    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=4, ensure_ascii=False)
