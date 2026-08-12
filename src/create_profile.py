import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader

load_dotenv()

RESUME_PATH = Path("data/resume/Siddanth_Resume_August_2026.pdf")
OUTPUT_PATH = Path("data/career_profile.json")


def extract_resume_text(path: Path) -> str:
    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def create_career_profile(resume_text: str) -> dict:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    prompt = f"""
You are a career profile extraction assistant.

Analyze the resume below and create a structured career profile.

IMPORTANT:
- Only use information explicitly present in the resume.
- Never invent skills, experience, achievements, education, or job titles.
- If something is unknown, use an empty list or null.
- Do not exaggerate the candidate's experience.
- Keep the information factual.

Return valid JSON with exactly these fields:

{{
  "summary": "",
  "years_of_experience": null,
  "current_or_recent_roles": [],
  "skills": [],
  "programming_languages": [],
  "data_and_ai_tools": [],
  "cloud_and_infrastructure": [],
  "databases": [],
  "analytics_and_bi_tools": [],
  "industries": [],
  "education": [],
  "certifications": [],
  "projects": [],
  "target_roles": []
}}

Resume:
---
{resume_text}
---
"""

    response = client.responses.create(
        model="gpt-5.6",
        input=prompt
    )

    text = response.output_text.strip()

    # Remove markdown code fences if the model adds them.
    if text.startswith("```"):
        text = text.replace("```json", "").replace("```", "").strip()

    return json.loads(text)


def main():
    print("Reading resume...")

    resume_text = extract_resume_text(RESUME_PATH)

    print("Creating career profile...")

    profile = create_career_profile(resume_text)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(profile, file, indent=2, ensure_ascii=False)

    print(f"\nCareer profile created: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()