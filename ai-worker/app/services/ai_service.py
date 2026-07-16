from google import genai
from app.config import settings
import json
import re
import time
from sqlalchemy.orm import Session
from app.services.rag_service import build_evidence_map

client = genai.Client(api_key=settings.GEMINI_API_KEY)


def score_requirement(requirement_text: str, matched_chunks: list) -> dict:
    if not matched_chunks:
        return {
            "score": 0,
            "explanation": "No relevant experience found in the resume.",
            "evidence": None,
        }

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
    response = None
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            break
        except Exception:
            if attempt < 2:
                time.sleep(2 ** attempt)
                continue
            return {
                "score": 0,
                "explanation": "Scoring temporarily unavailable — please retry.",
                "evidence": matched_chunks[0]["chunk_text"] if matched_chunks else None,
            }

    content = response.text
    match = re.search(r'\{.*\}', content, re.DOTALL)
    parsed = json.loads(match.group()) if match else {"score": 0, "explanation": "Could not parse."}

    return {
        "score": parsed.get("score", 0),
        "explanation": parsed.get("explanation", ""),
        "evidence": matched_chunks[0]["chunk_text"],
    }


def analyze_resume_rag(db: Session, analysis_id: int) -> dict:
    from app.models import JDRequirement, RequirementMatch

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

        for chunk in item["matched_chunks"]:
            match_record = RequirementMatch(
                analysis_id=analysis_id,
                requirement_id=item["requirement_id"],
                chunk_id=chunk["chunk_id"],
                similarity_score=chunk["similarity"],
                requirement_score=result["score"],
                explanation=result["explanation"],
            )
            db.add(match_record)

        requirement_scores.append({
            "requirement": item["requirement_text"],
            "score": result["score"],
            "explanation": result["explanation"],
            "evidence": result["evidence"],
            "similarity": round(item["best_similarity"], 3),
            "has_strong_evidence": item["has_strong_evidence"],
        })
        total += result["score"]

    db.commit()

    match_score = round(total / len(requirement_scores))
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