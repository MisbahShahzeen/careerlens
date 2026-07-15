from pymongo import MongoClient
from app.core.config import settings

# Create a single MongoDB client, reused across the app
_client = MongoClient(settings.MONGODB_URL)

# The careerlens database
_db = _client["careerlens"]

# The collection that stores raw resume documents
resume_documents = _db["resume_documents"]


def get_mongo_db():
    """Return the MongoDB database handle."""
    return _db