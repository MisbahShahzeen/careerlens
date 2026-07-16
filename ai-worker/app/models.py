from sqlalchemy import Column, Integer, String, DateTime, Text, Float
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from app.database import Base


class ResumeChunk(Base):
    __tablename__ = "resume_chunks"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, nullable=False)
    resume_id = Column(Integer, nullable=True)
    chunk_type = Column(String(50))
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer)
    embedding = Column(Vector(768))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class JDRequirement(Base):
    __tablename__ = "jd_requirements"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, nullable=False)
    requirement_text = Column(Text, nullable=False)
    requirement_index = Column(Integer)
    embedding = Column(Vector(768))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RequirementMatch(Base):
    __tablename__ = "requirement_matches"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, nullable=False)
    requirement_id = Column(Integer, nullable=False)
    chunk_id = Column(Integer, nullable=False)
    similarity_score = Column(Float)
    requirement_score = Column(Integer)
    explanation = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())