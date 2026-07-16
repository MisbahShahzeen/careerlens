from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.database import get_db, SessionLocal
from app.services.rag_service import store_resume_chunks, store_jd_requirements
from app.services.ai_service import analyze_resume_rag
import traceback


app = FastAPI(title="CareerLens AI Worker")


class AnalyzeRequest(BaseModel):
    analysis_id: int
    resume_text: str
    job_description: str


@app.get("/health")
def health():
    return {"status": "ok", "service": "ai-worker"}


@app.post("/internal/analyze-rag")
def internal_analyze_rag(request: AnalyzeRequest):
    """
    Internal endpoint called by the main service.
    Runs the full RAG pipeline: chunk, embed, store, retrieve, score.
    """
    db = SessionLocal()
    try:
        store_resume_chunks(db, request.analysis_id, request.resume_text)
        store_jd_requirements(db, request.analysis_id, request.job_description)
        result = analyze_resume_rag(db, request.analysis_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI worker failed: {str(e)}")
    finally:
        db.close()


@app.post("/internal/analyze-rag")
def internal_analyze_rag(request: AnalyzeRequest):
    """
    Internal endpoint called by the main service.
    Runs the full RAG pipeline: chunk, embed, store, retrieve, score.
    """
    db = SessionLocal()
    try:
        store_resume_chunks(db, request.analysis_id, request.resume_text)
        store_jd_requirements(db, request.analysis_id, request.job_description)
        result = analyze_resume_rag(db, request.analysis_id)
        return result
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"AI worker failed: {str(e)}")
    finally:
        db.close()