import json
import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY is not set in .env")

client = genai.Client(api_key=api_key)


def analyze_resume(resume_text, user_goal):

    prompt = f"""
You are a senior software engineer and hiring manager.

Analyze the following resume based on the user's career goal.

User goal:
{user_goal}

STRICT RULES:

1. Extract only skills relevant to the user's goal.
2. Ignore irrelevant tools or technologies.
3. Identify genuine missing skills needed for the user's goal.
4. Create a practical roadmap only for the missing skills.
5. Generate interview questions relevant to the user's goal.
6. Make the result specific to the user's resume and goal.
7. Do not invent skills that are not present in the resume.
8. Return ONLY valid JSON.
9. Do not use markdown or ```json.

Return exactly this structure:

{{
    "skills": [],
    "missing_skills": [],
    "roadmap": [],
    "interview_questions": []
}}

Resume:
{resume_text}
"""

    try:

        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt
        )

        content = response.text.strip()

        # Remove markdown code fences if Gemini happens to return them
        if content.startswith("```"):
            content = content.replace("```json", "", 1)
            content = content.replace("```", "", 1).strip()

        start = content.find("{")
        end = content.rfind("}")

        if start == -1 or end == -1:
            raise ValueError("AI response did not contain valid JSON.")

        result = json.loads(content[start:end + 1])

        return result

    except Exception as e:

        return {
            "skills": [],
            "missing_skills": [],
            "roadmap": [],
            "interview_questions": [],
            "error": str(e)
        }