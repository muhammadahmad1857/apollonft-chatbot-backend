from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
import os

DB_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./apollonft.db")

engine = create_async_engine(DB_URL, echo=False)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with SessionLocal() as session:
        yield session


async def create_tables():
    async with engine.begin() as conn:
        from app.db import models  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)
