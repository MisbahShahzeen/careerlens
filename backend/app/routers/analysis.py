from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import Analysis
from app.services.parser import extract_resume_text
from app.services.ai_service import analyze_resume, generate_cover_letter
from fastapi.security import OAuth2PasswordBearer
import json

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

    summary = f"Match score: {record.match_score}%. Improvements: {record.improvements[:200]}"

    cover_letter = generate_cover_letter(
        record.resume_text,
        record.job_description,
        summary
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