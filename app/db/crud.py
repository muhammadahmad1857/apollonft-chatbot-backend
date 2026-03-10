from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import User, ChatMessage, NFTRecord


async def get_or_create_user(db: AsyncSession, wallet_address: str) -> User:
    result = await db.execute(select(User).where(User.wallet_address == wallet_address))
    user = result.scalar_one_or_none()
    if not user:
        user = User(wallet_address=wallet_address)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


async def save_messages(
    db: AsyncSession,
    wallet_address: str,
    session_id: str,
    user_content: str,
    assistant_content: str,
) -> None:
    await get_or_create_user(db, wallet_address)
    db.add(ChatMessage(wallet_address=wallet_address, session_id=session_id, role="user", content=user_content))
    db.add(ChatMessage(wallet_address=wallet_address, session_id=session_id, role="assistant", content=assistant_content))
    await db.commit()


async def get_history(db: AsyncSession, wallet_address: str, limit: int = 50) -> list[ChatMessage]:
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.wallet_address == wallet_address)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    )
    return list(reversed(result.scalars().all()))


async def save_nft(db: AsyncSession, **kwargs) -> NFTRecord:
    wallet = kwargs.get("owner_wallet")
    await get_or_create_user(db, wallet)

    # Check if NFT already exists for this token_id + owner
    result = await db.execute(
        select(NFTRecord).where(
            NFTRecord.token_id == kwargs["token_id"],
            NFTRecord.owner_wallet == wallet,
        )
    )
    nft = result.scalar_one_or_none()
    if nft:
        for k, v in kwargs.items():
            setattr(nft, k, v)
    else:
        nft = NFTRecord(**kwargs)
        db.add(nft)
    await db.commit()
    await db.refresh(nft)
    return nft


async def get_user_nfts(db: AsyncSession, wallet_address: str) -> list[NFTRecord]:
    result = await db.execute(
        select(NFTRecord)
        .where(NFTRecord.owner_wallet == wallet_address)
        .order_by(NFTRecord.created_at.desc())
    )
    return list(result.scalars().all())
