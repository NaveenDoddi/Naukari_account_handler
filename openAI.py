from openai import OpenAI
import json

client = OpenAI(api_key="YOUR_API_KEY")

with open("profile.json") as f:
    profile = json.load(f)


def ask_llm(question):

    prompt = f"""
You are helping complete a job application.

Candidate Profile:
{json.dumps(profile, indent=2)}

Question:
{question}

Return ONLY the answer.
"""

    response = client.responses.create(model="gpt-5", input=prompt)

    return response.output_text.strip()
