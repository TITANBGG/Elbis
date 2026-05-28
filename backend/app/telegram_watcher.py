"""
Telegram kanal izleyici — telethon tabanlı.

İzlenen kanallardan yeni mesaj geldiğinde:
  1. Metinden şehir adı çıkar (location_extract)
  2. Olayı PostgreSQL'e kaydet (dedup)
  3. Bağlı tüm tarayıcılara WebSocket ile push et

Etkin olmak için .env dosyasında şunlar gerekir:
  TG_API_ID   = my.telegram.org'dan alınan sayısal ID
  TG_API_HASH = my.telegram.org'dan alınan hash

Oturum dosyası: /app/data/telegram.session  (Docker volume üzerinde kalıcı)
Oturum yoksa watcher sessizce devre dışı kalır.
"""

from __future__ import annotations
import asyncio
import datetime
import logging
import os
from typing import Callable, Awaitable

from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError

from app.location_extract import find_location

log = logging.getLogger("elbis.telegram")

_UTC = datetime.timezone.utc

TG_API_ID   = int(os.getenv("TG_API_ID",   "0") or "0")
TG_API_HASH = os.getenv("TG_API_HASH",  "")

SESSION_PATH = "/app/data/telegram"          # telethon .session ekler
SESSION_FILE = SESSION_PATH + ".session"

ENABLED = bool(TG_API_ID and TG_API_HASH)

# ── İzlenecek kanallar ─────────────────────────────────────────────────────────
# Herkese açık kanallar — kullanıcı hesabı bu kanallara üye olmak zorunda değil.
CHANNELS: list[str] = [
    "deepstatemap",         # DeepState MAP (UA / askeri harita güncellemeleri)
    "ukraine_now",          # Ukraine NOW (hızlı haber)
    "ukraineworld",         # Ukraine World (İngilizce özet)
    "United24news",         # United24 (resmi UA)
    "GeneralStaffZSU",      # Ukrayna Genelkurmay (resmi)
    "nexta_tv",             # NEXTA TV (bağımsız)
]

# Mesaj çok kısaysa konum çıkarımı anlamsız olur
_MIN_TEXT_LEN = 20

# Olay kodu — CAMEO haritamızın "14" → Protesto / Gönderi dışı olaylar için "TG"
_EVENT_CODE = "TG"


# ── Ana watcher ───────────────────────────────────────────────────────────────

async def run_watcher(
    on_new_event: Callable[[dict], Awaitable[None]],
) -> None:
    """
    Telegram kanallarını dinler; şehir içeren her yeni mesaj için
    `on_new_event(event_dict)` geri çağrısını yapar.

    Koşullar:
      • TG_API_ID / TG_API_HASH .env'de tanımlı olmalı
      • /app/data/telegram.session mevcut olmalı (telegram_auth.py ile oluştur)
    """
    if not ENABLED:
        log.info("[TG] TG_API_ID/TG_API_HASH tanımlı değil — Telegram devre dışı.")
        return

    if not os.path.exists(SESSION_FILE):
        log.info("[TG] Oturum dosyası bulunamadı (%s) — önce auth betiğini çalıştır.", SESSION_FILE)
        return

    client = TelegramClient(SESSION_PATH, TG_API_ID, TG_API_HASH)

    @client.on(events.NewMessage(chats=CHANNELS))
    async def _handler(event: events.NewMessage.Event) -> None:
        msg  = event.message
        text = msg.message or ""

        if len(text) < _MIN_TEXT_LEN:
            return

        loc = find_location(text)
        if not loc:
            return  # konum bulunamadı — atla

        # Kanal kullanıcı adını güvenli al
        try:
            chat     = await event.get_chat()
            username = getattr(chat, "username", None) or str(event.chat_id)
        except Exception:
            username = str(event.chat_id)

        title = f"{loc['name']} — {text[:100].replace(chr(10), ' ')}"

        ev = {
            "source_id":   f"tg_{event.chat_id}_{msg.id}",
            "lat":         loc["lat"],
            "lon":         loc["lon"],
            "event_code":  _EVENT_CODE,
            "title":       title[:500],
            "description": text[:500],
            "src":         f"TG:{username}"[:50],
            "url":         f"https://t.me/{username}/{msg.id}",
            "timestamp":   msg.date.astimezone(_UTC) if msg.date.tzinfo else msg.date.replace(tzinfo=_UTC),
            "country":     "UP",
            "source_type": "TELEGRAM",
        }

        log.info("[TG] Yeni olay: %s @ %s,%s", loc["name"], loc["lat"], loc["lon"])
        await on_new_event(ev)

    log.info("[TG] Bağlanıyor… Kanallar: %s", CHANNELS)
    await client.start()
    log.info("[TG] Bağlandı. Mesajlar dinleniyor.")
    await client.run_until_disconnected()
