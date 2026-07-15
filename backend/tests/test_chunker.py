from app.services.chunker import chunk_resume, chunk_job_description


def test_chunk_resume_detects_sections():
    resume = """
SUMMARY
Backend developer with 3 years of experience.

EXPERIENCE
Software Engineer at TechCorp. Built REST APIs.

SKILLS
Python, FastAPI, PostgreSQL

EDUCATION
BS Computer Science, 2021
"""
    chunks = chunk_resume(resume)
    # Should detect multiple sections
    assert len(chunks) >= 4
    chunk_types = [c["chunk_type"] for c in chunks]
    assert "experience" in chunk_types
    assert "skills" in chunk_types
    assert "education" in chunk_types


def test_chunk_resume_assigns_index():
    resume = "SUMMARY\nDeveloper.\n\nSKILLS\nPython, Docker"
    chunks = chunk_resume(resume)
    indices = [c["chunk_index"] for c in chunks]
    # Indices should be sequential starting from 0
    assert indices == list(range(len(chunks)))


def test_chunk_resume_fallback_on_unstructured():
    # No clear section headers — should fall back to paragraph chunking
    resume = "Just some text about a developer.\n\nAnother paragraph about skills."
    chunks = chunk_resume(resume)
    assert len(chunks) >= 1


def test_chunk_job_description_splits_bullets():
    jd = """
Requirements:
- 3+ years of Python experience
- Strong knowledge of FastAPI
- Experience with PostgreSQL
- Familiarity with Docker
"""
    requirements = chunk_job_description(jd)
    # Should extract the individual requirements
    assert len(requirements) >= 4
    texts = [r["requirement_text"] for r in requirements]
    assert any("Python" in t for t in texts)
    assert any("Docker" in t for t in texts)


def test_chunk_job_description_assigns_index():
    jd = "- Python\n- FastAPI\n- Docker experience required here"
    requirements = chunk_job_description(jd)
    indices = [r["requirement_index"] for r in requirements]
    assert indices == list(range(len(requirements)))


def test_empty_inputs_dont_crash():
    assert chunk_resume("") == [] or len(chunk_resume("")) >= 0
    assert chunk_job_description("") == [] or len(chunk_job_description("")) >= 0