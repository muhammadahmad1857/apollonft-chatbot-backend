from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    wallet_address: Mapped[str] = mapped_column(String(42), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_seen: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    nfts: Mapped[list["NFTRecord"]] = relationship(back_populates="owner", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    wallet_address: Mapped[str] = mapped_column(String(42), ForeignKey("users.wallet_address"), nullable=False)
    session_id: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)   # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="messages")


class NFTRecord(Base):
    __tablename__ = "nft_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token_id: Mapped[int] = mapped_column(Integer, nullable=False)
    owner_wallet: Mapped[str] = mapped_column(String(42), ForeignKey("users.wallet_address"), nullable=False)
    token_uri: Mapped[str] = mapped_column(Text, nullable=False)
    royalty_bps: Mapped[int] = mapped_column(Integer, default=0)
    # "owned" | "marketplace" | "auction"
    status: Mapped[str] = mapped_column(String(20), default="owned")
    listing_price_wei: Mapped[str | None] = mapped_column(Text, nullable=True)
    auction_min_bid_wei: Mapped[str | None] = mapped_column(Text, nullable=True)
    auction_end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    tx_hash: Mapped[str | None] = mapped_column(String(66), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    owner: Mapped["User"] = relationship(back_populates="nfts")
