import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from google import genai
from google.genai import types
from app.config import settings
from app.agent.agent import SYSTEM_PROMPT

router = APIRouter()

_genai_client = genai.Client(api_key=settings.google_api_key, http_options={"api_version": "v1alpha"})

LIVE_MODEL = "gemini-2.5-flash-native-audio-latest"

LIVE_CONFIG = types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    system_instruction=SYSTEM_PROMPT,
    speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Aoede")
        )
    ),
)


@router.websocket("/api/voice/live")
async def voice_live(ws: WebSocket):
    await ws.accept()
    try:
        async with _genai_client.aio.live.connect(
            model=LIVE_MODEL,
            config=LIVE_CONFIG,
        ) as session:
            print("GenAI live session initialized")

            async def browser_to_gemini():
                try:
                    async for msg in ws.iter_bytes():
                        await session.send(
                            input=types.LiveClientRealtimeInput(
                                media_chunks=[types.Blob(data=msg, mime_type="audio/pcm;rate=16000")]
                            )
                        )
                except WebSocketDisconnect:
                    pass

            async def gemini_to_browser():
                try:
                    async for response in session.receive():
                        if response.server_content and response.server_content.model_turn:
                            for part in response.server_content.model_turn.parts:
                                if part.inline_data and part.inline_data.data:
                                    await ws.send_bytes(part.inline_data.data)
                                elif part.text:
                                    await ws.send_text(part.text)
                except WebSocketDisconnect:
                    pass

            await asyncio.gather(browser_to_gemini(), gemini_to_browser())

    except WebSocketDisconnect:
        pass
    except Exception as e:
        import traceback
        traceback.print_exc()
        try:
            await ws.send_text(f"Error: {e}")
            await ws.close()
        except Exception:
            pass
