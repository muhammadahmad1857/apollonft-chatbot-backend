import asyncio
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
from google.adk.sessions import Session
from google.genai import types as genai_types
from app.agent.runner import get_runner, rebuild_runner, session_service
from app.agent.tools.image_tools import get_stored_image
from app.config import key_rotator
from app.agent.key_rotator import is_quota_error

router = APIRouter()


class ChatRequest(BaseModel):
    session_id: str
    message: str


async def _get_or_create_session(session_id: str) -> Session:
    session = await session_service.get_session(
        app_name="apollonft",
        user_id=session_id,
        session_id=session_id,
    )
    if session is None:
        session = await session_service.create_session(
            app_name="apollonft",
            user_id=session_id,
            session_id=session_id,
        )
    return session


@router.post("/api/chat")
async def chat(req: ChatRequest):
    await _get_or_create_session(req.session_id)

    async def event_stream():
        user_message = genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=req.message)],
        )

        attempts = 0
        max_attempts = key_rotator.num_keys

        while attempts < max_attempts:
            final_sent = False
            current_runner = get_runner()  # fetch current runner (may be rebuilt)
            try:
                async for event in current_runner.run_async(
                    user_id=req.session_id,
                    session_id=req.session_id,
                    new_message=user_message,
                ):
                    if event.is_final_response():
                        text = ""
                        if event.content and event.content.parts:
                            text = "".join(
                                part.text for part in event.content.parts if part.text
                            )
                        yield f"data: {json.dumps({'text': text, 'done': True})}\n\n"
                        final_sent = True
                        break
                    elif event.content and event.content.parts:
                        for part in event.content.parts:
                            if hasattr(part, "function_call") and part.function_call:
                                tool_name = getattr(part.function_call, "name", "tool")
                                payload = json.dumps({"type": "thinking", "step": f"Calling {tool_name}...", "status": "start"})
                                yield f"data: {payload}\n\n"
                            elif hasattr(part, "function_response") and part.function_response:
                                tool_name = getattr(part.function_response, "name", "tool")
                                payload = json.dumps({"type": "thinking", "step": f"{tool_name} done", "status": "done"})
                                yield f"data: {payload}\n\n"
                            elif part.text:
                                payload = json.dumps({"text": part.text, "done": False})
                                yield f"data: {payload}\n\n"

                if not final_sent:
                    yield f"data: {json.dumps({'text': '', 'done': True})}\n\n"
                return  # success

            except Exception as exc:
                if is_quota_error(exc) and attempts < max_attempts - 1:
                    attempts += 1
                    try:
                        new_key = key_rotator.rotate()
                        # Rebuild runner so the new genai Client uses the new key
                        rebuild_runner()
                        print(f"[KeyRotator] Quota hit — rebuilt runner with key ending ***{new_key[-4:]}")
                        await asyncio.sleep(0.5)
                        continue  # retry with new runner + key
                    except RuntimeError:
                        pass  # only one key configured; fall through to error

                import traceback
                traceback.print_exc()
                payload = json.dumps({"error": str(exc), "done": True})
                yield f"data: {payload}\n\n"
                return

        # All keys exhausted
        payload = json.dumps({
            "error": "All API keys quota-exhausted. Please try again later or add more keys to GOOGLE_API_KEYS in .env.",
            "done": True,
        })
        yield f"data: {payload}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/api/image/{img_id}")
async def get_image(img_id: str):
    result = get_stored_image(img_id)
    if not result:
        raise HTTPException(status_code=404, detail="Image not found")
    mime, data = result
    return Response(content=data, media_type=mime)
