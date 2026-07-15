from google import genai
from google.genai import types
from app.core.config import settings
from typing import List

client = genai.Client(api_key=settings.GEMINI_API_KEY)

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIM = 768


def embed_text(text: str) -> List[float]:
    """
    Convert a single piece of text into a 768-dimensional embedding vector.
    """
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(
            output_dimensionality=EMBEDDING_DIM,
        ),
    )
    return response.embeddings[0].values


def embed_batch(texts: List[str]) -> List[List[float]]:
    """
    Embed multiple texts in one API call — far more efficient than
    calling embed_text in a loop.
    """
    if not texts:
        return []

    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=texts,
        config=types.EmbedContentConfig(
            output_dimensionality=EMBEDDING_DIM,
        ),
    )
    return [embedding.values for embedding in response.embeddings]