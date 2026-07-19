import json
from pathlib import Path
from typing import Any
from sentence_transformers import SentenceTransformer, util

from logger import logger

BASE_DIR = Path(__file__).resolve().parent
KNOWLEDGE_DIR = BASE_DIR / "knowledge"
QA_DATABASE_PATH = KNOWLEDGE_DIR / "qa_database.json"
PROFILE_PATH = KNOWLEDGE_DIR / "profile.json"
HISTORY_PATH = KNOWLEDGE_DIR / "history.json"
MISSING_QUESTIONS_PATH = BASE_DIR / "missing_questions.txt"
model = SentenceTransformer("all-MiniLM-L6-v2")

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
HISTORY = _load_json(HISTORY_PATH)

history_questions = [item.get("question", "") for item in HISTORY]
history_embeddings = (
    model.encode(history_questions, convert_to_tensor=True)
    if history_questions
    else None
)


def refresh_embeddings():
    global history_questions, history_embeddings
    history_questions = [item.get("question", "") for item in HISTORY]
    history_embeddings = (
        model.encode(history_questions, convert_to_tensor=True)
        if history_questions
        else None
    )


def _get_nested_value(data, field):

    value = data

    for key in field.split("."):
        value = value.get(key)

        if value is None:
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


def semantic_search(question, threshold=0.82):
    if not HISTORY or history_embeddings is None:
        return None

    query_embedding = model.encode(question, convert_to_tensor=True)

    similarities = util.cos_sim(query_embedding, history_embeddings)[0]

    best_index = similarities.argmax().item()

    score = similarities[best_index].item()

    logger.info(f"Semantic Score : {score:.3f}")

    if score >= threshold:
        return HISTORY[best_index]["answer"]

    return None


def get_answer(question):

    # Rule Engine
    answer = find_best_answer(question)

    if answer:
        if "answer" in answer:
            return answer["answer"]

        if "field" in answer:
            return _get_nested_value(PROFILE, answer["field"])

    # Semantic Search
    answer = semantic_search(question)

    if answer:
        return answer

    return None


def save_missing_question(question: str):
    with MISSING_QUESTIONS_PATH.open("a", encoding="utf-8") as handle:
        handle.write(question + "\n")


def add_to_history(question, answer):

    for item in HISTORY:
        if item["question"].strip().lower() == question.strip().lower():
            item["answer"] = answer

            save_history()
            refresh_embeddings()
            return

    HISTORY.append({"question": question, "answer": answer})

    save_history()
    refresh_embeddings()


def get_rule_answer(question):

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

    if best_match is None:
        return None

    if "answer" in best_match:
        return best_match["answer"]

    if "field" in best_match:
        return _get_nested_value(PROFILE, best_match["field"])

    return None


def save_history():
    with HISTORY_PATH.open("w", encoding="utf-8") as f:
        json.dump(HISTORY, f, indent=4, ensure_ascii=False)
