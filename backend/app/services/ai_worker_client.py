import httpx
from app.core.config import settings

# Generous timeout — RAG makes many Gemini calls and can take a while
WORKER_TIMEOUT = 120.0


def call_ai_worker_rag(analysis_id: int, resume_text: str, job_description: str) -> dict:
    """
    Call the AI worker service to run the RAG pipeline.
    The worker chunks, embeds, stores, retrieves, and scores.
    """
    url = f"{settings.AI_WORKER_URL}/internal/analyze-rag"
    payload = {
        "analysis_id": analysis_id,
        "resume_text": resume_text,
        "job_description": job_description,
    }

    try:
        response = httpx.post(url, json=payload, timeout=WORKER_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except httpx.TimeoutException:
        raise RuntimeError("AI worker timed out")
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"AI worker returned an error: {e.response.status_code}")
    except httpx.RequestError as e:
        raise RuntimeError(f"Could not reach AI worker: {str(e)}")