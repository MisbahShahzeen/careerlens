from google import genai
from app.core.config import settings
import json
import re
from app.services.rag_service import build_evidence_map
from sqlalchemy.orm import Session


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


def score_requirement(requirement_text: str, matched_chunks: list) -> dict:
    """
    Score a single JD requirement against its matched resume chunks.
    Returns score, explanation, and the evidence used.
    """
    if not matched_chunks:
        return {
            "score": 0,
            "explanation": "No relevant experience found in the resume.",
            "evidence": None,
        }

    # Build the evidence text from matched chunks
    evidence_text = "\n".join(
        f"- [{c['chunk_type']}] {c['chunk_text']}" for c in matched_chunks
    )
    best_similarity = matched_chunks[0]["similarity"]

    prompt = f"""
You are evaluating how well a candidate's resume satisfies ONE specific job requirement.

JOB REQUIREMENT:
{requirement_text}

RELEVANT RESUME SECTIONS (retrieved by semantic search):
{evidence_text}

Semantic similarity of best match: {best_similarity:.2f}

Score how well the resume satisfies THIS requirement from 0 to 100.
Consider: does the resume show direct experience, related experience, or nothing?

Return ONLY valid JSON:
{{
    "score": <integer 0-100>,
    "explanation": "<one sentence explaining the score, referencing the evidence>"
}}
"""
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    content = response.text
    match = re.search(r'\{.*\}', content, re.DOTALL)
    parsed = json.loads(match.group()) if match else {"score": 0, "explanation": "Could not parse."}

    return {
        "score": parsed.get("score", 0),
        "explanation": parsed.get("explanation", ""),
        "evidence": matched_chunks[0]["chunk_text"],
    }


def analyze_resume_rag(db: Session, analysis_id: int) -> dict:
    """
    RAG-based analysis. Assumes chunks and requirements are already
    stored and embedded. Retrieves evidence per requirement, scores
    each one, and aggregates into a final analysis.
    """
    evidence_map = build_evidence_map(db, analysis_id)

    if not evidence_map:
        return {
            "match_score": 0,
            "requirement_scores": [],
            "matched_keywords": [],
            "missing_keywords": [],
            "summary": "No requirements could be extracted from the job description.",
        }

    requirement_scores = []
    total = 0

    for item in evidence_map:
        result = score_requirement(item["requirement_text"], item["matched_chunks"])
        requirement_scores.append({
            "requirement": item["requirement_text"],
            "score": result["score"],
            "explanation": result["explanation"],
            "evidence": result["evidence"],
            "similarity": round(item["best_similarity"], 3),
            "has_strong_evidence": item["has_strong_evidence"],
        })
        total += result["score"]

    # Overall match score = average of all requirement scores
    match_score = round(total / len(requirement_scores))

    # Derive matched/missing keywords from scores
    matched = [r["requirement"] for r in requirement_scores if r["score"] >= 60]
    missing = [r["requirement"] for r in requirement_scores if r["score"] < 40]

    return {
        "match_score": match_score,
        "requirement_scores": requirement_scores,
        "matched_keywords": matched,
        "missing_keywords": missing,
        "summary": f"Analyzed {len(requirement_scores)} requirements using semantic retrieval. "
                   f"Overall match: {match_score}%.",
    }