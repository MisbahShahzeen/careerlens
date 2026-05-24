from google import genai
from app.core.config import settings
import json
import re

client = genai.Client(api_key=settings.GEMINI_API_KEY)

def analyze_resume(resume_text: str, job_description: str) -> dict:
    prompt = f"""
You are an expert ATS and resume coach.

RESUME:
{resume_text[:4000]}

JOB DESCRIPTION:
{job_description[:2000]}

Return ONLY valid JSON with no extra text:
{{
    "match_score": <integer 0-100>,
    "matched_keywords": [<skills in BOTH resume and JD>],
    "missing_keywords": [<important skills in JD missing from resume>],
    "strengths": [<2-3 things resume does well>],
    "improvements": [<3-4 specific actionable suggestions>],
    "summary": "<2 sentence assessment>"
}}
"""
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    content = response.text
    match = re.search(r'\{.*\}', content, re.DOTALL)
    if match:
        return json.loads(match.group())
    return json.loads(content)


def generate_cover_letter(resume_text: str, job_description: str, analysis_summary: str) -> str:
    prompt = f"""
Write a professional cover letter for this candidate.

RESUME:
{resume_text[:2000]}

JOB DESCRIPTION:
{job_description[:1500]}

CONTEXT:
{analysis_summary}

Rules:
- 3 paragraphs, professional but warm
- Highlight strongest matching skills specifically
- Do NOT start with "I am writing to apply"
- End with a confident call to action
- Under 300 words
"""
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text