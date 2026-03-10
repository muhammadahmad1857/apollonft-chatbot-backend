import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
from google.adk.sessions import Session
from google.genai import types as genai_types
from app.agent.runner import runner, session_service
from app.agent.tools.image_tools import get_stored_image
from app.config import settings

router = APIRouter()


class ChatRequest(BaseModel):
    session_id: str
    message: str


async def _get_or_create_session(session_id: str) -> Session:
    print("Getting or creating session for session_id:", session_id)
    session = await session_service.get_session(
        app_name="apollonft",
        user_id=session_id,
        session_id=session_id,
    )
    print("Session in create session",session)
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
    print("Got the session")
    async def event_stream():
        try:
            user_message = genai_types.Content(
                role="user",
                parts=[genai_types.Part(text=req.message)],
            )
            print("User message received:", req.message)
            async for event in runner.run_async(
                user_id=req.session_id,
                session_id=req.session_id,
                new_message=user_message,
            ):
                if event.is_final_response() and event.content and event.content.parts:
                    text = event.content.parts[0].text or ""
                    payload = json.dumps({"text": text, "done": True})
                    yield f"data: {payload}\n\n"
                elif event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            payload = json.dumps({"text": part.text, "done": False})
                            yield f"data: {payload}\n\n"
        except Exception as e:
            import traceback
            traceback.print_exc()
            payload = json.dumps({"error": str(e), "done": True})
            yield f"data: {payload}\n\n"

        yield "data: [DONE]\n\n"

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
