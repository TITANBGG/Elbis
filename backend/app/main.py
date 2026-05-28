"""
ELBIS — FastAPI uygulaması

Veri kaynakları:
  • GDELT    — 15 dakikada bir (haber agregasyonu)
  • ACLED    — saatte bir (ACLED_KEY varsa, araştırma kalitesi veri)
  • Telegram — anlık push (TG_API_ID/TG_API_HASH + oturum dosyası varsa)

Tüm olaylar PostgreSQL'de saklanır; yeniler WebSocket ile tarayıcılara push edilir.
"""

import asyncio
import json
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import engine, AsyncSessionLocal, Base, get_session
from app.models import Event          # noqa: F401 — tablo oluşturma için import yeterli
from app.crud import upsert_events, get_recent_events
from app.gdelt import fetch_latest_export_events
from app.acled import fetch_acled_ukraine
from app.telegram_watcher import run_watcher as telegram_run_watcher

log = logging.getLogger("elbis")

# ── Uygulama ──────────────────────────────────────────────────────────────────
app = FastAPI(title="ELBIS API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # prodüksiyonda kısıtla
    allow_methods=["*"],
    allow_headers=["*"],
)


# ════════════════════════════════════════════════════════════════════════════════
# WebSocket bağlantı yöneticisi
# ════════════════════════════════════════════════════════════════════════════════

class ConnectionManager:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._clients.add(ws)
        log.info("WS bağlandı  — toplam: %d", len(self._clients))

    def disconnect(self, ws: WebSocket) -> None:
        self._clients.discard(ws)
        log.info("WS ayrıldı   — toplam: %d", len(self._clients))

    async def broadcast(self, payload: dict) -> None:
        """Tüm bağlı istemcilere JSON mesajı gönder; kopuk soketleri temizle."""
        if not self._clients:
            return
        text = json.dumps(payload, default=str)
        dead: set[WebSocket] = set()
        for ws in self._clients:
            try:
                await ws.send_text(text)
            except Exception:
                dead.add(ws)
        self._clients -= dead


manager = ConnectionManager()


# ════════════════════════════════════════════════════════════════════════════════
# HTTP endpoint'leri
# ════════════════════════════════════════════════════════════════════════════════

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/events")
async def get_events(session: AsyncSession = Depends(get_session)):
    """Son 200 olayı döndür — WebSocket bağlanamayan istemciler için yedek."""
    events = await get_recent_events(session, limit=200)
    return [e.to_dict() for e in events]


@app.post("/debug/fetch")
async def trigger_fetch(session: AsyncSession = Depends(get_session)):
    """Manuel tek seferlik GDELT çekimi (test/debug için)."""
    raw = await asyncio.to_thread(fetch_latest_export_events, 200, "UP")
    new = await upsert_events(session, raw)
    if new:
        await manager.broadcast({"type": "events_update", "data": new})
    return {"fetched": len(raw), "new": len(new)}


# ════════════════════════════════════════════════════════════════════════════════
# WebSocket endpoint
# ════════════════════════════════════════════════════════════════════════════════

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)

    # Bağlanır bağlanmaz mevcut olayları gönder
    async with AsyncSessionLocal() as session:
        events = await get_recent_events(session, limit=200)
        await ws.send_text(json.dumps({
            "type": "init",
            "data": [e.to_dict() for e in events],
        }, default=str))

    try:
        while True:
            # Ping/pong — bağlantıyı canlı tut
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)


# ════════════════════════════════════════════════════════════════════════════════
# Arka plan görevleri
# ════════════════════════════════════════════════════════════════════════════════

async def _do_gdelt_fetch() -> None:
    """GDELT'ten veri çek, yeni olayları kaydet ve push et."""
    try:
        raw = await asyncio.to_thread(fetch_latest_export_events, 200, "UP")
        async with AsyncSessionLocal() as session:
            new = await upsert_events(session, raw)
        log.info("[GDELT] %d olay çekildi, %d yeni", len(raw), len(new))
        if new:
            await manager.broadcast({"type": "events_update", "data": new})
    except Exception as exc:
        log.warning("[GDELT] Hata: %s", exc)


async def _do_acled_fetch() -> None:
    """ACLED'den veri çek (key yoksa sessizce atla)."""
    try:
        raw = await fetch_acled_ukraine(days_back=2)
        if not raw:
            return
        async with AsyncSessionLocal() as session:
            new = await upsert_events(session, raw)
        log.info("[ACLED] %d olay çekildi, %d yeni", len(raw), len(new))
        if new:
            await manager.broadcast({"type": "events_update", "data": new})
    except Exception as exc:
        log.warning("[ACLED] Hata: %s", exc)


async def _gdelt_loop() -> None:
    """İlk fetch hemen yapılır, sonra 15 dakikada bir tekrar eder."""
    await _do_gdelt_fetch()
    while True:
        await asyncio.sleep(15 * 60)   # GDELT 15 dak'ta bir güncellenir
        await _do_gdelt_fetch()


async def _acled_loop() -> None:
    """ACLED saatte bir kontrol edilir."""
    await asyncio.sleep(60)            # başlangıçta kısa bekleme
    await _do_acled_fetch()
    while True:
        await asyncio.sleep(60 * 60)
        await _do_acled_fetch()


# ════════════════════════════════════════════════════════════════════════════════
# Uygulama başlangıcı
# ════════════════════════════════════════════════════════════════════════════════

async def _telegram_loop() -> None:
    """
    Telegram watcher — oturum dosyası ve API key varsa çalışır.
    Bağlantı koptuğunda 30 saniye bekleyip yeniden bağlanır.
    """
    while True:
        try:
            await telegram_run_watcher(_on_telegram_event)
        except Exception as exc:
            log.warning("[TG] Watcher durdu: %s — 30s sonra yeniden denenecek.", exc)
        await asyncio.sleep(30)


async def _on_telegram_event(ev: dict) -> None:
    """Telegram'dan gelen tek olayı DB'ye kaydet ve push et."""
    async with AsyncSessionLocal() as session:
        new = await upsert_events(session, [ev])
    if new:
        await manager.broadcast({"type": "events_update", "data": new})


@app.on_event("startup")
async def startup() -> None:
    # 1. Veritabanı tablolarını oluştur (yoksa)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info("Veritabanı tabloları hazır.")

    # 2. Arka plan döngülerini başlat
    asyncio.create_task(_gdelt_loop())
    asyncio.create_task(_acled_loop())
    asyncio.create_task(_telegram_loop())
    log.info("Arka plan görevleri başlatıldı (GDELT + ACLED + Telegram).")
