from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models import ResumeChunk, JDRequirement, RequirementMatch
from app.services.chunker import chunk_resume, chunk_job_description
from app.services.embedder import embed_batch
from typing import List, Dict

# Return the top-K resume chunks per JD requirement
TOP_K = 2

# Below this cosine similarity, we treat a match as weak evidence
SIMILARITY_THRESHOLD = 0.65


def store_resume_chunks(db: Session, analysis_id: int, resume_text: str) -> List[ResumeChunk]:
    """
    Chunk the resume, embed each chunk, and store in pgvector.
    Returns the created ResumeChunk records.
    """
    chunks = chunk_resume(resume_text)
    if not chunks:
        return []

    texts = [c["chunk_text"] for c in chunks]
    embeddings = embed_batch(texts)

    records = []
    for chunk, embedding in zip(chunks, embeddings):
        record = ResumeChunk(
            analysis_id=analysis_id,
            chunk_type=chunk["chunk_type"],
            chunk_text=chunk["chunk_text"],
            chunk_index=chunk["chunk_index"],
            embedding=embedding,
        )
        db.add(record)
        records.append(record)

    db.commit()
    for r in records:
        db.refresh(r)
    return records


def store_jd_requirements(db: Session, analysis_id: int, jd_text: str) -> List[JDRequirement]:
    """
    Chunk the JD into requirements, embed each, and store in pgvector.
    """
    requirements = chunk_job_description(jd_text)
    if not requirements:
        return []

    texts = [r["requirement_text"] for r in requirements]
    embeddings = embed_batch(texts)

    records = []
    for req, embedding in zip(requirements, embeddings):
        record = JDRequirement(
            analysis_id=analysis_id,
            requirement_text=req["requirement_text"],
            requirement_index=req["requirement_index"],
            embedding=embedding,
        )
        db.add(record)
        records.append(record)

    db.commit()
    for r in records:
        db.refresh(r)
    return records


def find_matching_chunks(
    db: Session,
    analysis_id: int,
    requirement: JDRequirement,
) -> List[Dict]:
    """
    For one JD requirement, find the TOP_K most similar resume chunks
    using pgvector cosine similarity search.
    """
    # pgvector: <=> is cosine distance. similarity = 1 - distance.
    # We scope the search to THIS analysis's chunks only.
    query = text("""
        SELECT
            id,
            chunk_type,
            chunk_text,
            1 - (embedding <=> (:req_embedding)::vector) AS similarity
        FROM resume_chunks
        WHERE analysis_id = :analysis_id
        ORDER BY embedding <=> (:req_embedding)::vector
        LIMIT :top_k
    """)

    result = db.execute(query, {
        "req_embedding": str(requirement.embedding),
        "analysis_id": analysis_id,
        "top_k": TOP_K,
    })

    matches = []
    for row in result:
        matches.append({
            "chunk_id": row.id,
            "chunk_type": row.chunk_type,
            "chunk_text": row.chunk_text,
            "similarity": float(row.similarity),
        })
    return matches


def build_evidence_map(db: Session, analysis_id: int) -> List[Dict]:
    """
    For every JD requirement in this analysis, retrieve its best-matching
    resume chunks. This is the retrieval step of RAG — it produces the
    evidence set that the LLM will later score.
    """
    requirements = (
        db.query(JDRequirement)
        .filter(JDRequirement.analysis_id == analysis_id)
        .order_by(JDRequirement.requirement_index)
        .all()
    )

    evidence = []
    for req in requirements:
        matches = find_matching_chunks(db, analysis_id, req)
        best_similarity = matches[0]["similarity"] if matches else 0.0
        evidence.append({
            "requirement_id": req.id,
            "requirement_text": req.requirement_text,
            "matched_chunks": matches,
            "best_similarity": best_similarity,
            "has_strong_evidence": best_similarity >= SIMILARITY_THRESHOLD,
        })
    return evidence