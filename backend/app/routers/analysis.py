from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
import json
from app.core.database import get_db
from app.core.security import decode_access_token
from app.services.parser import extract_resume_text
from app.services.ai_service import analyze_resume, generate_cover_letter, analyze_resume_rag
from app.services.ai_worker_client import call_ai_worker_rag
from app.services.document_store import store_resume_document, get_resume_document
from app.services.chunker import chunk_resume
from app.models.user import Analysis, ResumeChunk, JDRequirement, RequirementMatch, AnalysisJob
from fastapi.security import OAuth2PasswordBearer

router = APIRouter(prefix="/analysis", tags=["analysis"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user_id(token: str = Depends(oauth2_scheme)) -> int:
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return int(payload["sub"])


@router.post("/analyze")
async def analyze(
    resume: UploadFile = File(...),
    job_description: str = Form(...),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    if not resume.filename.lower().endswith((".pdf", ".docx")):
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files allowed")

    file_bytes = await resume.read()

    try:
        resume_text = extract_resume_text(resume.filename, file_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read file: {str(e)}")

    if not resume_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from file")

    try:
        result = analyze_resume(resume_text, job_description)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {str(e)}")

    record = Analysis(
        user_id=user_id,
        resume_filename=resume.filename,
        resume_text=resume_text,
        job_description=job_description,
        match_score=result.get("match_score", 0),
        matched_keywords=json.dumps(result.get("matched_keywords", [])),
        missing_keywords=json.dumps(result.get("missing_keywords", [])),
        strengths=json.dumps(result.get("strengths", [])),
        improvements=json.dumps(result.get("improvements", [])),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {**result, "analysis_id": record.id}


def _process_rag_job(job_id: int, analysis_id: int, resume_text: str, job_description: str):
    """
    Background task: calls the AI worker and updates the job status.
    Runs after the HTTP response has already been sent to the client.
    """
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
        job.status = "processing"
        db.commit()

        result = call_ai_worker_rag(analysis_id, resume_text, job_description)

        record = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        record.match_score = result["match_score"]
        record.matched_keywords = json.dumps(result.get("matched_keywords", []))
        record.missing_keywords = json.dumps(result.get("missing_keywords", []))

        job.status = "complete"
        db.commit()
    except Exception as e:
        job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
        if job:
            job.status = "failed"
            job.error_message = str(e)
            db.commit()
    finally:
        db.close()


@router.post("/analyze-rag")
async def analyze_rag(
    background_tasks: BackgroundTasks,
    resume: UploadFile = File(...),
    job_description: str = Form(...),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    if not resume.filename.lower().endswith((".pdf", ".docx")):
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files allowed")

    file_bytes = await resume.read()

    try:
        resume_text = extract_resume_text(resume.filename, file_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read file: {str(e)}")

    if not resume_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from file")

    sections = chunk_resume(resume_text)
    parsed_sections = {s["chunk_type"]: s["chunk_text"] for s in sections}
    mongo_doc_id = store_resume_document(
        filename=resume.filename,
        raw_text=resume_text,
        parsed_sections=parsed_sections,
    )

    record = Analysis(
        user_id=user_id,
        resume_filename=resume.filename,
        resume_text=resume_text,
        job_description=job_description,
        rag_enabled=True,
        mongo_document_id=mongo_doc_id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    job = AnalysisJob(user_id=user_id, analysis_id=record.id, status="pending")
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(
        _process_rag_job, job.id, record.id, resume_text, job_description
    )

    return {
        "job_id": job.id,
        "analysis_id": record.id,
        "status": "pending",
        "message": "Analysis started. Poll /analysis/jobs/{job_id} for the result.",
    }


@router.get("/jobs/{job_id}")
def get_job_status(
    job_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    job = db.query(AnalysisJob).filter(
        AnalysisJob.id == job_id,
        AnalysisJob.user_id == user_id
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    response = {
        "job_id": job.id,
        "status": job.status,
        "analysis_id": job.analysis_id,
    }

    if job.status == "failed":
        response["error"] = job.error_message

    if job.status == "complete":
        analysis = db.query(Analysis).filter(Analysis.id == job.analysis_id).first()
        matches = db.query(RequirementMatch).filter(
            RequirementMatch.analysis_id == job.analysis_id
        ).all()

        req_scores = []
        for req in db.query(JDRequirement).filter(
            JDRequirement.analysis_id == job.analysis_id
        ).order_by(JDRequirement.requirement_index).all():
            req_matches = [m for m in matches if m.requirement_id == req.id]
            best = max(req_matches, key=lambda m: m.similarity_score or 0, default=None)
            if best:
                chunk = db.query(ResumeChunk).filter(ResumeChunk.id == best.chunk_id).first()
                req_scores.append({
                    "requirement": req.requirement_text,
                    "score": best.requirement_score,
                    "explanation": best.explanation,
                    "evidence": chunk.chunk_text if chunk else None,
                    "similarity": round(best.similarity_score, 3) if best.similarity_score else 0,
                    "has_strong_evidence": (best.similarity_score or 0) >= 0.65,
                })

        response["result"] = {
            "match_score": analysis.match_score,
            "requirement_scores": req_scores,
            "matched_keywords": json.loads(analysis.matched_keywords or "[]"),
            "missing_keywords": json.loads(analysis.missing_keywords or "[]"),
            "summary": f"Analyzed {len(req_scores)} requirements using semantic retrieval. Overall match: {analysis.match_score}%.",
        }

    return response


@router.post("/compare")
async def compare_approaches(
    resume: UploadFile = File(...),
    job_description: str = Form(...),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    if not resume.filename.lower().endswith((".pdf", ".docx")):
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files allowed")

    file_bytes = await resume.read()

    try:
        resume_text = extract_resume_text(resume.filename, file_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read file: {str(e)}")

    if not resume_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from file")

    try:
        legacy_result = analyze_resume(resume_text, job_description)
    except Exception as e:
        legacy_result = {"error": f"Legacy analysis failed: {str(e)}"}

    comparison = {
        "legacy": {
            "approach": "prompt_stuffing",
            "match_score": legacy_result.get("match_score"),
            "matched_keywords": legacy_result.get("matched_keywords", []),
            "missing_keywords": legacy_result.get("missing_keywords", []),
            "has_evidence": False,
            "explainable": False,
            "result": legacy_result,
        },
        "rag": {
            "approach": "retrieval_augmented",
            "note": "Run /analyze-rag for the full RAG pipeline (async job-based).",
            "has_evidence": True,
            "explainable": True,
        },
        "differences": {
            "rag_provides_evidence": True,
            "rag_scores_per_requirement": True,
            "legacy_truncates_input": len(resume_text) > 4000,
            "resume_length_chars": len(resume_text),
        },
    }

    return comparison


@router.post("/cover-letter/{analysis_id}")
def get_cover_letter(
    analysis_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    record = db.query(Analysis).filter(
        Analysis.id == analysis_id,
        Analysis.user_id == user_id
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="Analysis not found")

    suggestions = json.loads(record.improvements or "[]")
    summary = f"Match score: {record.match_score}%. Key gaps: {', '.join(suggestions[:2])}"

    cover_letter = generate_cover_letter(
        record.resume_text, record.job_description, summary
    )

    record.cover_letter = cover_letter
    db.commit()

    return {"cover_letter": cover_letter}


@router.get("/history")
def get_history(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    analyses = db.query(Analysis).filter(
        Analysis.user_id == user_id
    ).order_by(Analysis.created_at.desc()).all()

    return [
        {
            "id": a.id,
            "resume_filename": a.resume_filename,
            "match_score": a.match_score,
            "created_at": a.created_at,
        }
        for a in analyses
    ]


@router.get("/{analysis_id}/evidence")
def get_evidence(
    analysis_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    record = db.query(Analysis).filter(
        Analysis.id == analysis_id,
        Analysis.user_id == user_id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Analysis not found")

    requirements = db.query(JDRequirement).filter(
        JDRequirement.analysis_id == analysis_id
    ).order_by(JDRequirement.requirement_index).all()

    evidence = []
    for req in requirements:
        matches = db.query(RequirementMatch).filter(
            RequirementMatch.requirement_id == req.id
        ).all()
        chunk_details = []
        for match in matches:
            chunk = db.query(ResumeChunk).filter(
                ResumeChunk.id == match.chunk_id
            ).first()
            if chunk:
                chunk_details.append({
                    "chunk_type": chunk.chunk_type,
                    "chunk_text": chunk.chunk_text,
                    "similarity": match.similarity_score,
                    "requirement_score": match.requirement_score,
                    "explanation": match.explanation,
                })
        evidence.append({
            "requirement": req.requirement_text,
            "matched_chunks": chunk_details,
        })

    return {"analysis_id": analysis_id, "evidence": evidence}


@router.get("/{analysis_id}/document")
def get_analysis_document(
    analysis_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    record = db.query(Analysis).filter(
        Analysis.id == analysis_id,
        Analysis.user_id == user_id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Analysis not found")

    if not record.mongo_document_id:
        raise HTTPException(status_code=404, detail="No document stored for this analysis")

    document = get_resume_document(record.mongo_document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found in store")

    return {
        "analysis_id": analysis_id,
        "mongo_document_id": record.mongo_document_id,
        "document": document,
    }


@router.get("/{analysis_id}")
def get_analysis(
    analysis_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    record = db.query(Analysis).filter(
        Analysis.id == analysis_id,
        Analysis.user_id == user_id
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return {
        "analysis_id": record.id,
        "resume_filename": record.resume_filename,
        "job_description": record.job_description,
        "match_score": record.match_score,
        "matched_keywords": json.loads(record.matched_keywords or "[]"),
        "missing_keywords": json.loads(record.missing_keywords or "[]"),
        "strengths": json.loads(record.strengths or "[]"),
        "improvements": json.loads(record.improvements or "[]"),
        "cover_letter": record.cover_letter,
        "created_at": record.created_at,
    }