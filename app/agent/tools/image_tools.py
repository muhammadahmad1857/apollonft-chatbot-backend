import uuid
from google import genai
from google.genai import types
from app.config import settings

_client = genai.Client(api_key=settings.google_api_key)

# In-memory image store: id -> (mime_type, bytes)
_image_store: dict[str, tuple[str, bytes]] = {}


async def generate_image(prompt: str) -> str:
    """Generate an image from a text description and return a renderable marker.

    Args:
        prompt: A detailed description of the image to generate.

    Returns:
        An [IMG_ID:...] marker the UI renders as an image, or an error message.
    """
    try:
        response = await _client.aio.models.generate_content(
            model="gemini-2.0-flash-exp-image-generation",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )
        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.data:
                img_id = str(uuid.uuid4())
                mime = part.inline_data.mime_type or "image/png"
                _image_store[img_id] = (mime, part.inline_data.data)
                return f"[IMG_ID:{img_id}]"
        return "Image generation produced no output. Try a more descriptive prompt."
    except Exception as e:
        err = str(e)
        if "429" in err or "RESOURCE_EXHAUSTED" in err or "quota" in err.lower():
            return (
                "Image generation is unavailable on the current API plan. "
                "To enable it, go to https://aistudio.google.com and upgrade to a paid plan, "
                "then the 'gemini-2.0-flash-exp-image-generation' model will be available."
            )
        return f"Image generation failed: {err}"


def get_stored_image(img_id: str) -> tuple[str, bytes] | None:
    return _image_store.get(img_id)
