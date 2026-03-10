from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.db import crud

router = APIRouter(prefix="/api/user", tags=["users"])


class SaveHistoryRequest(BaseModel):
    session_id: str
    user_message: str
    assistant_message: str


@router.get("/{wallet}")
async def get_user(wallet: str, db: AsyncSession = Depends(get_db)):
    user = await crud.get_or_create_user(db, wallet.lower())
    history = await crud.get_history(db, wallet.lower())
    nfts = await crud.get_user_nfts(db, wallet.lower())
    return {
        "wallet": user.wallet_address,
        "created_at": user.created_at,
        "last_seen": user.last_seen,
        "message_count": len(history),
        "nft_count": len(nfts),
    }


@router.post("/{wallet}/history")
async def save_history(wallet: str, req: SaveHistoryRequest, db: AsyncSession = Depends(get_db)):
    await crud.save_messages(
        db,
        wallet_address=wallet.lower(),
        session_id=req.session_id,
        user_content=req.user_message,
        assistant_content=req.assistant_message,
    )
    return {"ok": True}


@router.get("/{wallet}/history")
async def get_history(wallet: str, db: AsyncSession = Depends(get_db)):
    messages = await crud.get_history(db, wallet.lower())
    return [
        {
            "role": m.role,
            "content": m.content,
            "session_id": m.session_id,
            "created_at": m.created_at,
        }
        for m in messages
    ]


@router.get("/{wallet}/nfts")
async def get_nfts(wallet: str, db: AsyncSession = Depends(get_db)):
    nfts = await crud.get_user_nfts(db, wallet.lower())
    return [
        {
            "id": n.id,
            "token_id": n.token_id,
            "token_uri": n.token_uri,
            "status": n.status,
            "listing_price_wei": n.listing_price_wei,
            "tx_hash": n.tx_hash,
            "created_at": n.created_at,
        }
        for n in nfts
    ]
