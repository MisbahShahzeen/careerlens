from app.core.mongodb import resume_documents
from datetime import datetime, timezone
from bson import ObjectId
from typing import Optional, Dict


def store_resume_document(
    filename: str,
    raw_text: str,
    parsed_sections: Dict[str, str],
) -> str:
    """
    Store a raw resume document in MongoDB.
    Returns the MongoDB document ID as a string.
    """
    document = {
        "filename": filename,
        "raw_text": raw_text,
        "parsed_sections": parsed_sections,
        "char_count": len(raw_text),
        "uploaded_at": datetime.now(timezone.utc),
    }
    result = resume_documents.insert_one(document)
    return str(result.inserted_id)


def get_resume_document(document_id: str) -> Optional[Dict]:
    """
    Retrieve a resume document from MongoDB by its ID.
    Returns None if not found or if the ID is malformed.
    """
    try:
        obj_id = ObjectId(document_id)
    except Exception:
        return None

    doc = resume_documents.find_one({"_id": obj_id})
    if not doc:
        return None

    # Convert MongoDB's ObjectId to a string so it's JSON-serializable
    doc["_id"] = str(doc["_id"])
    return doc