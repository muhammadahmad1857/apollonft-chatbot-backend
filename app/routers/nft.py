from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.db import crud
from app.rag import embedder, qdrant
from qdrant_client.models import PointStruct
import uuid
import httpx

router = APIRouter(prefix="/api/nft", tags=["nft"])


class NFTConfirmRequest(BaseModel):
    owner_wallet: str
    token_id: int
    token_uri: str
    royalty_bps: int = 0
    status: str = "owned"           # owned | marketplace | auction
    listing_price_wei: str | None = None
    auction_min_bid_wei: str | None = None
    tx_hash: str | None = None


@router.post("/confirm")
async def confirm_nft(req: NFTConfirmRequest, db: AsyncSession = Depends(get_db)):
    """Called by frontend after a blockchain transaction is confirmed."""
    nft = await crud.save_nft(
        db,
        token_id=req.token_id,
        owner_wallet=req.owner_wallet.lower(),
        token_uri=req.token_uri,
        royalty_bps=req.royalty_bps,
        status=req.status,
        listing_price_wei=req.listing_price_wei,
        auction_min_bid_wei=req.auction_min_bid_wei,
        tx_hash=req.tx_hash,
    )

    # Ingest into vector store (best-effort)
    try:
        metadata_text = await _fetch_metadata_text(req.token_uri, req.token_id)
        vector = await embedder.embed(metadata_text)
        await qdrant.upsert([
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={
                    "text": metadata_text,
                    "source": "nft",
                    "token_id": req.token_id,
                    "owner": req.owner_wallet.lower(),
                    "status": req.status,
                },
            )
        ])
    except Exception as e:
        print(f"Vector store ingest skipped: {e}")

    return {"ok": True, "nft_id": nft.id}


@router.get("/my-nfts")
async def get_my_nfts(wallet: str, db: AsyncSession = Depends(get_db)):
    """Return all NFTs owned by a wallet address."""
    nfts = await crud.get_user_nfts(db, wallet.lower())
    return [
        {
            "token_id": nft.token_id,
            "token_uri": nft.token_uri,
            "royalty_bps": nft.royalty_bps,
            "status": nft.status,
            "listing_price_wei": nft.listing_price_wei,
            "auction_min_bid_wei": nft.auction_min_bid_wei,
            "tx_hash": nft.tx_hash,
        }
        for nft in nfts
    ]


async def _fetch_metadata_text(token_uri: str, token_id: int) -> str:
    """Fetch NFT metadata JSON and convert to embeddable text."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            url = token_uri.replace("ipfs://", "https://ipfs.io/ipfs/")
            resp = await client.get(url)
            data = resp.json()
            name = data.get("name", f"NFT #{token_id}")
            desc = data.get("description", "")
            attrs = " ".join(
                f"{a.get('trait_type', '')}: {a.get('value', '')}"
                for a in data.get("attributes", [])
            )
            return f"{name}. {desc}. {attrs}".strip()
    except Exception:
        return f"NFT token #{token_id} at {token_uri}"
