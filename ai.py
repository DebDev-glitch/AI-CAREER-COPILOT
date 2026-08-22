import json
import os

from dotenv import load_dotenv
from google import genai


# Environment
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY is not set in .env")

client = genai.Client(api_key=api_key)


REQUIRED_FIELDS = [
    "career_summary",
    "job_readiness_score",
    "job_readiness_reason",
    "skills",
    "missing_skills",
    "roadmap",
    "recommended_projects",
    "interview_questions",
    "resume_improvements"
]


def analyze_resume(resume_text, user_goal):

    prompt = f"""
You are an expert technical recruiter, senior software engineer,
career coach, and resume evaluator.

Analyze the candidate's resume specifically for the target career role.

TARGET ROLE:
{user_goal}

RESUME:
{resume_text}

ANALYSIS RULES:

1. Base every conclusion strictly on evidence from the resume.
2. Never invent skills, experience, internships, certifications,
   projects, education, achievements, technologies, or proficiency levels.
3. If something is not demonstrated, treat it as missing or unknown.
4. Only recommend skills relevant to the target role.
5. Prioritize important skill gaps.
6. Consider projects, education, internships, certifications,
   work experience, and technical skills.
7. Do not confuse a mentioned technology with demonstrated proficiency.
8. Use "Unknown" when proficiency cannot be determined.
9. Keep recommendations realistic for the candidate's level.
10. Avoid generic advice.

SKILLS:

Identify only skills relevant to the target role.

For every skill provide:
- name
- level
- evidence

Allowed levels:
- Beginner
- Intermediate
- Advanced
- Unknown

Do not assign Advanced without strong evidence.

MISSING SKILLS:

Identify important skills required for the target role that are not
sufficiently demonstrated.

For every missing skill provide:
- name
- priority
- reason

Allowed priorities:
- High
- Medium
- Low

Do not include unrelated technologies.

ROADMAP:

Create a practical roadmap based on the identified skill gaps.

Order the roadmap logically from prerequisite knowledge to practical
application.

For every step provide:
- step
- topic
- reason
- practice

Do not recommend skills the candidate already clearly demonstrates
unless deeper knowledge is needed.

PROJECTS:

Recommend practical projects that help close the most important gaps.

For every project provide:
- name
- purpose
- skills
- description

Keep projects realistic for the candidate's current level.

INTERVIEW:

Generate questions specifically for the target role.

Include:
- Fundamental technical questions
- Intermediate technical questions
- Practical problem-solving questions
- Project-based questions
- Scenario-based questions

For every question provide:
- question
- category
- difficulty

Allowed categories:
- Technical
- Practical
- Project
- Scenario

Allowed difficulty:
- Beginner
- Intermediate
- Advanced

RESUME IMPROVEMENTS:

Identify specific improvements for the target role.

Focus on:
- Missing information
- Weak project descriptions
- Lack of measurable achievements
- Unclear technical contributions
- Missing relevant keywords
- Poor demonstration of skills
- Missing evidence of impact

Do not suggest adding experience or skills the candidate does not have.

JOB READINESS:

Provide a score from 0 to 100 based on the evidence in the resume
compared with the requirements of the target role.

The score is an estimate, not an objective measurement.

Also provide a short explanation.

OUTPUT:

Return ONLY valid JSON.

Do not use Markdown.
Do not use ```json.
Do not include explanations outside the JSON.

Return exactly:

{{
    "career_summary": "",
    "job_readiness_score": 0,
    "job_readiness_reason": "",
    "skills": [],
    "missing_skills": [],
    "roadmap": [],
    "recommended_projects": [],
    "interview_questions": [],
    "resume_improvements": []
}}

Rules:
- career_summary must be a concise personalized assessment.
- job_readiness_score must be an integer from 0 to 100.
- job_readiness_reason must briefly explain the score.
- skills must be an array of objects.
- missing_skills must be an array of objects.
- roadmap must be an array of objects.
- recommended_projects must be an array of objects.
- interview_questions must be an array of objects.
- resume_improvements must be an array of strings.
- Never invent information not present in the resume.
"""

    try:

        # Generate response
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt
        )

        if not response or not response.text:
            raise ValueError("Gemini returned an empty response.")

        content = response.text.strip()

        # Clean response
        if content.startswith("```"):
            content = content.replace("```json", "", 1)
            content = content.replace("```", "", 1).strip()

        start = content.find("{")
        end = content.rfind("}")

        if start == -1 or end == -1:
            raise ValueError(
                "AI response did not contain valid JSON."
            )

        result = json.loads(content[start:end + 1])

        if not isinstance(result, dict):
            raise ValueError(
                "AI response must be a JSON object."
            )

        # Check fields
        missing_fields = [
            field
            for field in REQUIRED_FIELDS
            if field not in result
        ]

        if missing_fields:
            raise ValueError(
                "AI response is missing required fields: "
                + ", ".join(missing_fields)
            )

        # Validate summary
        if not isinstance(result["career_summary"], str):
            raise ValueError(
                "career_summary must be a string."
            )

        # Validate score
        if not isinstance(result["job_readiness_score"], int):
            raise ValueError(
                "job_readiness_score must be an integer."
            )

        if not 0 <= result["job_readiness_score"] <= 100:
            raise ValueError(
                "job_readiness_score must be between 0 and 100."
            )

        if not isinstance(
            result["job_readiness_reason"],
            str
        ):
            raise ValueError(
                "job_readiness_reason must be a string."
            )

        list_fields = [
            "skills",
            "missing_skills",
            "roadmap",
            "recommended_projects",
            "interview_questions",
            "resume_improvements"
        ]

        # Validate arrays
        for field in list_fields:
            if not isinstance(result[field], list):
                raise ValueError(
                    f"AI field '{field}' must be an array."
                )

        # Validate skills
        for skill in result["skills"]:

            if not isinstance(skill, dict):
                raise ValueError(
                    "Each skill must be an object."
                )

            required_fields = [
                "name",
                "level",
                "evidence"
            ]

            for field in required_fields:
                if field not in skill:
                    raise ValueError(
                        f"Skill is missing '{field}'."
                    )

        # Validate missing skills
        for skill in result["missing_skills"]:

            if not isinstance(skill, dict):
                raise ValueError(
                    "Each missing skill must be an object."
                )

            required_fields = [
                "name",
                "priority",
                "reason"
            ]

            for field in required_fields:
                if field not in skill:
                    raise ValueError(
                        f"Missing skill is missing '{field}'."
                    )

        # Validate roadmap
        for step in result["roadmap"]:

            if not isinstance(step, dict):
                raise ValueError(
                    "Each roadmap step must be an object."
                )

            required_fields = [
                "step",
                "topic",
                "reason",
                "practice"
            ]

            for field in required_fields:
                if field not in step:
                    raise ValueError(
                        f"Roadmap step is missing '{field}'."
                    )

        # Validate projects
        for project in result["recommended_projects"]:

            if not isinstance(project, dict):
                raise ValueError(
                    "Each recommended project must be an object."
                )

            required_fields = [
                "name",
                "purpose",
                "skills",
                "description"
            ]

            for field in required_fields:
                if field not in project:
                    raise ValueError(
                        f"Project is missing '{field}'."
                    )

        # Validate interview questions
        for question in result["interview_questions"]:

            if not isinstance(question, dict):
                raise ValueError(
                    "Each interview question must be an object."
                )

            required_fields = [
                "question",
                "category",
                "difficulty"
            ]

            for field in required_fields:
                if field not in question:
                    raise ValueError(
                        f"Interview question is missing '{field}'."
                    )

        # Validate improvements
        for improvement in result["resume_improvements"]:

            if not isinstance(improvement, str):
                raise ValueError(
                    "Resume improvements must contain strings."
                )

        return result

    except json.JSONDecodeError:

        return {
            "career_summary": "",
            "job_readiness_score": 0,
            "job_readiness_reason": "",
            "skills": [],
            "missing_skills": [],
            "roadmap": [],
            "recommended_projects": [],
            "interview_questions": [],
            "resume_improvements": [],
            "error": (
                "The AI returned an invalid JSON response. "
                "Please try analyzing the resume again."
            )
        }

    except Exception as e:

        return {
            "career_summary": "",
            "job_readiness_score": 0,
            "job_readiness_reason": "",
            "skills": [],
            "missing_skills": [],
            "roadmap": [],
            "recommended_projects": [],
            "interview_questions": [],
            "resume_improvements": [],
            "error": str(e)
        }