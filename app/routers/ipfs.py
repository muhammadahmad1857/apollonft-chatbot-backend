import httpx
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional

router = APIRouter(prefix="/api/nft", tags=["ipfs"])

_PIN_FILE_URL = "https://api.pinata.cloud/pinning/pinFileToIPFS"
_PIN_JSON_URL = "https://api.pinata.cloud/pinning/pinJSONToIPFS"


async def _pin_file(data: bytes, filename: str, jwt: str) -> str:
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            _PIN_FILE_URL,
            headers={"Authorization": f"Bearer {jwt}"},
            files={"file": (filename, data)},
        )
        resp.raise_for_status()
        return f"ipfs://{resp.json()['IpfsHash']}"


async def _pin_json(payload: dict, jwt: str) -> str:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            _PIN_JSON_URL,
            headers={"Authorization": f"Bearer {jwt}"},
            json={"pinataContent": payload, "pinataMetadata": {"name": payload.get("name", "metadata")}},
        )
        resp.raise_for_status()
        return f"ipfs://{resp.json()['IpfsHash']}"


@router.post("/upload-ipfs")
async def upload_to_ipfs(
    name: str = Form(...),
    description: str = Form(""),
    royalty_bps: int = Form(0),
    music_track: UploadFile = File(...),          # required: the main NFT file (any type)
    cover_image: Optional[UploadFile] = File(None),  # optional: separate cover image
    preview_track: Optional[UploadFile] = File(None),
):
    from app.config import settings
    if not settings.pinata_jwt or settings.pinata_jwt == "your-pinata-jwt-here":
        raise HTTPException(status_code=503, detail="Pinata JWT not configured on server.")

    music_bytes = await music_track.read()
    music_uri = await _pin_file(music_bytes, music_track.filename or "main", settings.pinata_jwt)

    cover_uri: Optional[str] = None
    if cover_image and cover_image.size:
        cover_bytes = await cover_image.read()
        if cover_bytes:
            cover_uri = await _pin_file(cover_bytes, cover_image.filename or "cover", settings.pinata_jwt)

    # If no separate cover and the main file is an image, use it as the cover too
    if not cover_uri:
        main_type = music_track.content_type or ""
        main_name = (music_track.filename or "").lower()
        if main_type.startswith("image/") or any(main_name.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".avif")):
            cover_uri = music_uri

    preview_uri: Optional[str] = None
    if preview_track and preview_track.size:
        preview_bytes = await preview_track.read()
        if preview_bytes:
            preview_uri = await _pin_file(preview_bytes, preview_track.filename or "preview", settings.pinata_jwt)

    metadata: dict = {
        "name": name,
        "description": description,
        "animation_url": music_uri,
        "attributes": [],
    }
    if cover_uri:
        metadata["image"] = cover_uri
    if preview_uri:
        metadata["preview_url"] = preview_uri

    token_uri = await _pin_json(metadata, settings.pinata_jwt)

    response: dict = {
        "token_uri": token_uri,
        "cover_image_url": cover_uri or music_uri,
        "music_track_url": music_uri,
        "metadata": metadata,
    }
    if preview_uri:
        response["preview_track_url"] = preview_uri

    return response
