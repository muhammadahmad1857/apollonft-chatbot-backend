import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from google import genai
from google.genai import types
from app.config import settings
from app.agent.agent import SYSTEM_PROMPT

router = APIRouter()

_genai_client = genai.Client(api_key=settings.google_api_key, http_options={"api_version": "v1alpha"})

LIVE_MODEL = "gemini-2.5-flash-native-audio-latest"

# NFT tool declarations available in voice mode
_NFT_TOOLS = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="request_nft_upload",
            description=(
                "Initiate the NFT minting flow. Call this when the user wants to mint a new music NFT. "
                "Gather the name and description from conversation first, then call this tool."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "name": types.Schema(type=types.Type.STRING, description="NFT name"),
                    "description": types.Schema(type=types.Type.STRING, description="NFT description"),
                    "royalty_bps": types.Schema(type=types.Type.INTEGER, description="Royalty in BPS (0-1000, default 0)"),
                },
                required=["name"],
            ),
        ),
        types.FunctionDeclaration(
            name="list_nft_marketplace",
            description="List an owned NFT on the marketplace for a fixed price.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "token_id": types.Schema(type=types.Type.INTEGER, description="Token ID to list"),
                    "price_eth": types.Schema(type=types.Type.STRING, description="Listing price in ETH"),
                },
                required=["token_id", "price_eth"],
            ),
        ),
        types.FunctionDeclaration(
            name="list_nft_auction",
            description="Start an auction for an owned NFT.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "token_id": types.Schema(type=types.Type.INTEGER, description="Token ID to auction"),
                    "min_bid_eth": types.Schema(type=types.Type.STRING, description="Minimum bid in ETH"),
                    "duration_hours": types.Schema(type=types.Type.INTEGER, description="Auction duration in hours"),
                },
                required=["token_id", "min_bid_eth"],
            ),
        ),
    ]
)

LIVE_CONFIG = types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    system_instruction=SYSTEM_PROMPT,
    speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Aoede")
        )
    ),
    tools=[_NFT_TOOLS],
)


def _build_action_payload(name: str, args: dict) -> str:
    """Build [ACTION:...] marker from a tool call."""
    if name == "request_nft_upload":
        data = {
            "name": args.get("name", ""),
            "description": args.get("description", ""),
            "royalty_bps": int(args.get("royalty_bps", 0)),
        }
        return f"[ACTION:upload_mint:{json.dumps(data)}]"
    elif name == "list_nft_marketplace":
        data = {"token_id": str(args.get("token_id", "")), "price_eth": str(args.get("price_eth", ""))}
        return f"[ACTION:list_marketplace:{json.dumps(data)}]"
    elif name == "list_nft_auction":
        data = {
            "token_id": str(args.get("token_id", "")),
            "min_bid_eth": str(args.get("min_bid_eth", "")),
            "duration_hours": str(args.get("duration_hours", 24)),
        }
        return f"[ACTION:list_auction:{json.dumps(data)}]"
    return ""


@router.websocket("/api/voice/live")
async def voice_live(ws: WebSocket):
    await ws.accept()
    try:
        async with _genai_client.aio.live.connect(
            model=LIVE_MODEL,
            config=LIVE_CONFIG,
        ) as session:

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
                        # Audio / text parts
                        if response.server_content and response.server_content.model_turn:
                            for part in response.server_content.model_turn.parts:
                                if part.inline_data and part.inline_data.data:
                                    await ws.send_bytes(part.inline_data.data)
                                elif part.text:
                                    await ws.send_text(json.dumps({"type": "text", "content": part.text}))

                        # Tool calls from the model
                        if response.tool_call:
                            tool_responses = []
                            for fc in response.tool_call.function_calls:
                                args = dict(fc.args) if fc.args else {}
                                action_marker = _build_action_payload(fc.name, args)
                                if action_marker:
                                    await ws.send_text(json.dumps({"type": "action", "content": action_marker}))

                                tool_responses.append(
                                    types.FunctionResponse(
                                        id=fc.id,
                                        name=fc.name,
                                        response={"result": "Action triggered in the app. Confirm to the user."},
                                    )
                                )

                            await session.send(
                                input=types.LiveClientToolResponse(function_responses=tool_responses)
                            )
                except WebSocketDisconnect:
                    pass

            await asyncio.gather(browser_to_gemini(), gemini_to_browser())

    except WebSocketDisconnect:
        pass
    except Exception as e:
        import traceback
        traceback.print_exc()
        try:
            await ws.send_text(json.dumps({"type": "error", "content": str(e)}))
            await ws.close()
        except Exception:
            pass
