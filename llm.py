import json
import time
from pathlib import Path
from google import genai
import config

BASE_DIR = Path(__file__).resolve().parent
PROFILE_PATH = BASE_DIR / "knowledge" / "profile.json"

client = genai.Client(api_key=config.GEMINI_API_KEY)

with open(PROFILE_PATH, "r", encoding="utf-8") as f:
    profile = json.load(f)


# to get all the models available in the Gemini API. You can uncomment the above lines to see the list of models.
# for model in client.models.list():
#     print(model.name)


def ask_llm(question: str, options=None):

    if options is None:
        options = []

    prompt = f"""
You are helping complete a Naukri job application.

Candidate Profile:

{json.dumps(profile, indent=4)}

Recruiter's Question:

{question}
"""

    if options:
        prompt += "\nAvailable Options:\n"

        for option in options:
            prompt += f"- {option}\n"

        prompt += """

Choose ONLY from the available options.
Return your answer using the exact text from one of the options.
If multiple options apply, return them separated by commas.
If none of the options are a good match, return the closest matching option or the exact option text.
Return ONLY the answer and nothing else.
"""
    else:
        prompt += """

Return ONLY the answer.
Do not explain anything.
Do not include extra words.
"""

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=config.GEMINI_MODEL, contents=prompt
            )
            return response.text.strip()
        except Exception as exc:
            message = str(exc)
            if "RESOURCE_EXHAUSTED" in message or "quota" in message.lower():
                raise
            if attempt < 2:
                time.sleep(2**attempt)
                continue
            raise


# if __name__ == "__main__":
#     result = ask_llm("How many years of experience do you have in Testing Tools?")

#     print(result)
