import json
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

BASE_DIR = Path(__file__).resolve().parent
PROFILE_PATH = BASE_DIR / "knowledge" / "profile.json"

client = OpenAI(api_key="YOUR_API_KEY") if OpenAI is not None else None

with PROFILE_PATH.open("r", encoding="utf-8") as handle:
    profile = json.load(handle)


def ask_llm(question: str) -> str:
    prompt = f"""
You are helping complete a job application.

Candidate Profile:
{json.dumps(profile, indent=2)}

Question:
{question}

Return ONLY the answer.
"""

    if client is None:
        raise RuntimeError("openai package is not installed or not configured")

    response = client.responses.create(model="gpt-5", input=prompt)
    return response.output_text.strip()
