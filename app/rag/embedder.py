from google import genai
from app.config import settings

_client = genai.Client(api_key=settings.google_api_key)


async def embed(text: str) -> list[float]:
    """Embed text using Gemini text-embedding-004, returns 768-dim vector."""
    response = _client.models.embed_content(
        model=settings.embed_model,
        contents=text,
    )
    return response.embeddings[0].values
