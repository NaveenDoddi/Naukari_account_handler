import json
from pathlib import Path
from typing import Any

from logger import logger

BASE_DIR = Path(__file__).resolve().parent
KNOWLEDGE_DIR = BASE_DIR / "knowledge"
QA_DATABASE_PATH = KNOWLEDGE_DIR / "qa_database.json"
PROFILE_PATH = KNOWLEDGE_DIR / "profile.json"
HISTORY_PATH = KNOWLEDGE_DIR / "history.json"
MISSING_QUESTIONS_PATH = BASE_DIR / "missing_questions.txt"


def _load_json(path: Path) -> Any:
    if not path.exists():
        return [] if path.suffix == ".json" else {}

    text = path.read_text(encoding="utf-8")
    if not text or not text.strip():
        return [] if path.suffix == ".json" else {}

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        if path.suffix == ".json":
            decoder = json.JSONDecoder()
            try:
                obj, idx = decoder.raw_decode(text)
            except json.JSONDecodeError:
                backup_path = path.with_suffix(path.suffix + ".bak")
                path.replace(backup_path)
                return []

            remainder = text[idx:].strip()
            if remainder:
                backup_path = path.with_suffix(path.suffix + ".bak")
                path.replace(backup_path)
                with path.open("w", encoding="utf-8") as handle:
                    json.dump(obj, handle, indent=2)

            return obj if isinstance(obj, (list, dict)) else []

        backup_path = path.with_suffix(path.suffix + ".bak")
        path.replace(backup_path)
        return [] if path.suffix == ".json" else {}


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
    with MISSING_QUESTIONS_PATH.open("a", encoding="utf-8") as handle:
        handle.write(question + "\n")


def add_to_history(question: str, answer: Any):
    history = _load_json(HISTORY_PATH)
    if isinstance(history, list):
        history.append({"question": question, "answer": answer})
    else:
        history = [{"question": question, "answer": answer}]
    with HISTORY_PATH.open("w", encoding="utf-8") as handle:
        json.dump(history, handle, indent=2)
