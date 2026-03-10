from fastapi import APIRouter, File, UploadFile, HTTPException
from groq import AsyncGroq
from app.config import settings

router = APIRouter()

_groq_client = AsyncGroq(api_key=settings.groq_api_key)


@router.post("/api/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    """Transcribe audio using Groq Whisper."""
    allowed_prefixes = (
        "audio/wav", "audio/wave", "audio/mpeg", "audio/mp4",
        "audio/ogg", "audio/webm", "audio/flac", "audio/x-m4a",
    )
    content_type = audio.content_type or ""
    if not any(content_type.startswith(p) for p in allowed_prefixes):
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported audio type: {content_type}",
        )

    audio_bytes = await audio.read()
    filename = audio.filename or "audio.wav"

    transcript = await _groq_client.audio.transcriptions.create(
        model="whisper-large-v3-turbo",
        file=(filename, audio_bytes, audio.content_type),
    )

    return {"text": transcript.text}
