import re
from typing import List, Dict

# Common section headers found in resumes, mapped to a normalized type
SECTION_PATTERNS = {
    "summary": r"(summary|objective|profile|about)",
    "experience": r"(experience|employment|work history|professional experience)",
    "skills": r"(skills|technical skills|technologies|competencies)",
    "education": r"(education|academic|qualifications)",
    "projects": r"(projects|portfolio|personal projects)",
    "certifications": r"(certifications|certificates|licenses)",
}


def chunk_resume(resume_text: str) -> List[Dict[str, str]]:
    """
    Split a resume into semantic sections.
    Returns a list of {chunk_type, chunk_text, chunk_index}.
    Falls back to paragraph chunking if no sections are detected.
    """
    lines = resume_text.split("\n")
    chunks = []
    current_type = "general"
    current_lines = []

    def flush():
        if current_lines:
            text = "\n".join(current_lines).strip()
            if len(text) > 20:  # skip trivially short chunks
                chunks.append({
                    "chunk_type": current_type,
                    "chunk_text": text,
                })

    for line in lines:
        stripped = line.strip().lower()
        matched_section = None

        # Is this line a section header?
        for section_type, pattern in SECTION_PATTERNS.items():
            if re.match(rf"^\s*{pattern}\s*:?\s*$", stripped) or \
               (len(stripped) < 40 and re.search(pattern, stripped)):
                matched_section = section_type
                break

        if matched_section:
            flush()                     # save the previous section
            current_type = matched_section
            current_lines = []
        else:
            current_lines.append(line)

    flush()  # save the last section

    # Fallback: if we only found one big chunk, split by paragraphs
    if len(chunks) <= 1:
        chunks = _chunk_by_paragraphs(resume_text)

    # Add index
    for i, chunk in enumerate(chunks):
        chunk["chunk_index"] = i

    return chunks


def _chunk_by_paragraphs(text: str) -> List[Dict[str, str]]:
    """Fallback chunking: split on blank lines into paragraphs."""
    paragraphs = re.split(r"\n\s*\n", text)
    chunks = []
    for para in paragraphs:
        para = para.strip()
        if len(para) > 20:
            chunks.append({
                "chunk_type": "general",
                "chunk_text": para,
            })
    return chunks


def chunk_job_description(jd_text: str) -> List[Dict[str, str]]:
    """
    Split a job description into individual requirements.
    Each bullet point or sentence becomes one requirement.
    Returns a list of {requirement_text, requirement_index}.
    """
    # Normalize bullet characters to newlines
    normalized = re.sub(r"[•·▪●○\-\*]\s*", "\n", jd_text)
    lines = normalized.split("\n")

    requirements = []
    for line in lines:
        line = line.strip()
        # Keep lines that look like real requirements
        if len(line) > 15 and not _is_header(line):
            requirements.append(line)

    # If bullet splitting produced too few, fall back to sentence splitting
    if len(requirements) < 3:
        requirements = _split_sentences(jd_text)

    return [
        {"requirement_text": req, "requirement_index": i}
        for i, req in enumerate(requirements)
    ]


def _is_header(line: str) -> bool:
    """Detect section headers that aren't real requirements."""
    headers = ["responsibilities", "requirements", "qualifications",
               "about us", "what you", "we offer", "benefits"]
    lower = line.lower()
    return len(line) < 30 and any(h in lower for h in headers)


def _split_sentences(text: str) -> List[str]:
    """Fallback: split text into sentences."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if len(s.strip()) > 15]