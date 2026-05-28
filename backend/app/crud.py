"""
CRUD — Veritabanı okuma/yazma işlemleri.

Temel kural: source_id zaten varsa atla (deduplication).
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.models import Event


async def upsert_events(session: AsyncSession, events: list[dict]) -> list[dict]:
    """
    Yeni olayları veritabanına ekle; source_id'si zaten kayıtlıysa atla.
    Yeni eklenen olayların dict listesini döndürür — WebSocket broadcast için.
    """
    new_events: list[dict] = []

    for ev in events:
        source_id = ev.get("source_id")
        if not source_id:
            continue  # source_id olmayan satır atlansın

        result = await session.execute(
            select(Event).where(Event.source_id == source_id)
        )
        if result.scalar_one_or_none() is not None:
            continue  # zaten var, atla

        obj = Event(**ev)
        session.add(obj)
        new_events.append(ev)

    if new_events:
        await session.commit()

    return new_events


async def get_recent_events(session: AsyncSession, limit: int = 200) -> list[Event]:
    """Son `limit` olayı zaman damgasına göre azalan sırayla getir."""
    result = await session.execute(
        select(Event)
        .order_by(desc(Event.timestamp))
        .limit(limit)
    )
    return list(result.scalars().all())
