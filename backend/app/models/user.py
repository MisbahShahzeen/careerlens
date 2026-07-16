from sqlalchemy import Column, Integer, String, DateTime, Text, Float, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    analyses = relationship("Analysis", back_populates="owner")
    resumes = relationship("Resume", back_populates="owner")


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    raw_text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    owner = relationship("User", back_populates="resumes")
    chunks = relationship("ResumeChunk", back_populates="resume")
    analyses = relationship("Analysis", back_populates="resume")


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=True)
    resume_filename = Column(String)
    resume_text = Column(Text)
    job_description = Column(Text)
    match_score = Column(Float)
    missing_keywords = Column(Text)
    matched_keywords = Column(Text)
    strengths = Column(Text)
    improvements = Column(Text)
    cover_letter = Column(Text)
    rag_enabled = Column(Boolean, default=False)
    mongo_document_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    owner = relationship("User", back_populates="analyses")
    resume = relationship("Resume", back_populates="analyses")
    chunks = relationship("ResumeChunk", back_populates="analysis")
    jd_requirements = relationship("JDRequirement", back_populates="analysis")
    requirement_matches = relationship("RequirementMatch", back_populates="analysis")


class ResumeChunk(Base):
    __tablename__ = "resume_chunks"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False)
    resume_id = Column(Integer, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=True)
    chunk_type = Column(String(50))
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer)
    embedding = Column(Vector(768))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    analysis = relationship("Analysis", back_populates="chunks")
    resume = relationship("Resume", back_populates="chunks")
    matches = relationship("RequirementMatch", back_populates="chunk")


class JDRequirement(Base):
    __tablename__ = "jd_requirements"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False)
    requirement_text = Column(Text, nullable=False)
    requirement_index = Column(Integer)
    embedding = Column(Vector(768))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    analysis = relationship("Analysis", back_populates="jd_requirements")
    matches = relationship("RequirementMatch", back_populates="requirement")


class RequirementMatch(Base):
    __tablename__ = "requirement_matches"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False)
    requirement_id = Column(Integer, ForeignKey("jd_requirements.id"), nullable=False)
    chunk_id = Column(Integer, ForeignKey("resume_chunks.id"), nullable=False)
    similarity_score = Column(Float)
    requirement_score = Column(Integer)
    explanation = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    analysis = relationship("Analysis", back_populates="requirement_matches")
    requirement = relationship("JDRequirement", back_populates="matches")
    chunk = relationship("ResumeChunk", back_populates="matches")

class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    analysis_id = Column(Integer, ForeignKey("analyses.id"), nullable=True)
    status = Column(String, default="pending")  # pending, processing, complete, failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())