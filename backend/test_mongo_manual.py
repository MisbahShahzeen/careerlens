from app.core.mongodb import resume_documents
from datetime import datetime, timezone

# Insert a test document
doc = {
    "raw_text": "This is a test resume with Python and FastAPI experience.",
    "filename": "test_resume.pdf",
    "parsed_sections": {
        "skills": "Python, FastAPI, PostgreSQL",
        "experience": "Backend developer",
    },
    "uploaded_at": datetime.now(timezone.utc),
}

result = resume_documents.insert_one(doc)
print(f"Inserted document with ID: {result.inserted_id}")

# Read it back
retrieved = resume_documents.find_one({"_id": result.inserted_id})
print(f"Retrieved filename: {retrieved['filename']}")
print(f"Retrieved skills: {retrieved['parsed_sections']['skills']}")

# Clean up
resume_documents.delete_one({"_id": result.inserted_id})
print("Test document deleted. MongoDB connection works!")