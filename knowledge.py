import json
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
KNOWLEDGE_DIR = BASE_DIR / "knowledge"
QA_DATABASE_PATH = KNOWLEDGE_DIR / "qa_database.json"
PROFILE_PATH = KNOWLEDGE_DIR / "profile.json"
HISTORY_PATH = KNOWLEDGE_DIR / "history.json"


def _load_json(path: Path) -> Any:
    if not path.exists():
        return [] if path.suffix == ".json" else {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


QA_DATABASE = _load_json(QA_DATABASE_PATH)
PROFILE = _load_json(PROFILE_PATH)


def _get_nested_value(data: dict, dotted_path: str) -> Any:
    value = data
    for part in dotted_path.split("."):
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            return None
    return value


def find_best_answer(question: str):
    q = question.lower()
    best_match = None
    best_score = 0

    for item in QA_DATABASE:
        score = 0
        for keyword in item.get("keywords", []):
            if keyword.lower() in q:
                score += len(keyword)
        if score > best_score:
            best_score = score
            best_match = item

    return best_match


def get_answer(question: str):
    match = find_best_answer(question)
    if not match:
        return None

    if "answer" in match:
        return match["answer"]

    if "field" in match:
        return _get_nested_value(PROFILE, match["field"])

    return None


def save_missing_question(question: str):
    with HISTORY_PATH.open("a", encoding="utf-8") as handle:
        handle.write(question + "\n")


def add_to_history(question: str, answer: Any):
    history = _load_json(HISTORY_PATH)
    if isinstance(history, list):
        history.append({"question": question, "answer": answer})
    else:
        history = [{"question": question, "answer": answer}]
    with HISTORY_PATH.open("w", encoding="utf-8") as handle:
        json.dump(history, handle, indent=2)
