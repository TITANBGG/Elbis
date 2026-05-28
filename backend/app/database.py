import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

# .env'deki postgresql:// → asyncpg sürücüsü için postgresql+asyncpg:// yap
_raw = os.getenv("DATABASE_URL", "postgresql://elbis:elbis_pass@postgres:5432/elbis_db")
DATABASE_URL = _raw.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,       # bağlantı düşmüşse otomatik yenile
    pool_size=5,
    max_overflow=10,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_session():
    """FastAPI dependency — her istek için bir oturum açar, bitince kapatır."""
    async with AsyncSessionLocal() as session:
        yield session
