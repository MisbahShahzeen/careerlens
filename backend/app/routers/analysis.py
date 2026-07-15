from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
import json
from app.core.database import get_db
from app.core.security import decode_access_token
from app.services.parser import extract_resume_text
from app.services.ai_service import analyze_resume, generate_cover_letter, analyze_resume_rag
from app.services.rag_service import store_resume_chunks, store_jd_requirements
from app.services.document_store import store_resume_document, get_resume_document
from app.services.chunker import chunk_resume
from app.models.user import Analysis, ResumeChunk, JDRequirement, RequirementMatch
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


@router.post("/analyze-rag")
async def analyze_rag(
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

    # Store the raw resume document in MongoDB (document store)
    sections = chunk_resume(resume_text)
    parsed_sections = {s["chunk_type"]: s["chunk_text"] for s in sections}

    mongo_doc_id = store_resume_document(
        filename=resume.filename,
        raw_text=resume_text,
        parsed_sections=parsed_sections,
    )

    # Create the analysis record in PostgreSQL, referencing the MongoDB document
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

    try:
        store_resume_chunks(db, record.id, resume_text)
        store_jd_requirements(db, record.id, job_description)
        result = analyze_resume_rag(db, record.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG analysis failed: {str(e)}")

    record.match_score = result["match_score"]
    record.matched_keywords = json.dumps(result.get("matched_keywords", []))
    record.missing_keywords = json.dumps(result.get("missing_keywords", []))
    db.commit()

    return {**result, "analysis_id": record.id}


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

    # --- Approach 1: Legacy prompt stuffing ---
    try:
        legacy_result = analyze_resume(resume_text, job_description)
    except Exception as e:
        legacy_result = {"error": f"Legacy analysis failed: {str(e)}"}

    # --- Approach 2: RAG ---
    rag_analysis = Analysis(
        user_id=user_id,
        resume_filename=resume.filename,
        resume_text=resume_text,
        job_description=job_description,
        rag_enabled=True,
    )
    db.add(rag_analysis)
    db.commit()
    db.refresh(rag_analysis)

    try:
        store_resume_chunks(db, rag_analysis.id, resume_text)
        store_jd_requirements(db, rag_analysis.id, job_description)
        rag_result = analyze_resume_rag(db, rag_analysis.id)
        rag_result["analysis_id"] = rag_analysis.id
    except Exception as e:
        rag_result = {"error": f"RAG analysis failed: {str(e)}"}

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
            "match_score": rag_result.get("match_score"),
            "requirements_analyzed": len(rag_result.get("requirement_scores", [])),
            "has_evidence": True,
            "explainable": True,
            "result": rag_result,
        },
        "differences": {
            "score_delta": (
                (rag_result.get("match_score", 0) or 0)
                - (legacy_result.get("match_score", 0) or 0)
            ),
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