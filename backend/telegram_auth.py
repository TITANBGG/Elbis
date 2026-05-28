#!/usr/bin/env python3
"""
Tek seferlik Telegram kimlik doğrulaması.

Çalıştırma (container içinde — telefon numarasını girmek için interaktif terminal gerekir):

    docker exec -it elbis-backend-1 python /app/telegram_auth.py

Başarılı olursa /app/data/telegram.session oluşur.
Backend bir sonraki başlatmada bu dosyayı kullanarak kanalları dinlemeye başlar.
"""

import asyncio
import os
import sys

# Container dışında çalıştırılırsa proje dizinini path'e ekle
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    from telethon import TelegramClient
    from telethon.errors import SessionPasswordNeededError
except ImportError:
    print("HATA: telethon kurulu değil.")
    print("  pip install telethon")
    sys.exit(1)

TG_API_ID   = int(os.getenv("TG_API_ID",   "0") or "0")
TG_API_HASH = os.getenv("TG_API_HASH", "")
SESSION_PATH = "/app/data/telegram"


async def main() -> None:
    if not TG_API_ID or not TG_API_HASH:
        print()
        print("HATA: TG_API_ID ve TG_API_HASH .env dosyasında tanımlı değil.")
        print()
        print("  1. https://my.telegram.org adresine git")
        print("  2. API development tools → yeni uygulama oluştur")
        print("  3. api_id ve api_hash değerlerini .env'e ekle:")
        print()
        print("     TG_API_ID=123456")
        print("     TG_API_HASH=abcdef1234567890abcdef1234567890")
        print()
        return

    client = TelegramClient(SESSION_PATH, TG_API_ID, TG_API_HASH)
    await client.connect()

    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"✅ Zaten giriş yapılmış: {me.first_name} (@{me.username})")
        print(f"   Oturum: {SESSION_PATH}.session")
        await client.disconnect()
        return

    print()
    print("═══════════════════════════════════════")
    print("  ELBIS — Telegram Kimlik Doğrulaması")
    print("═══════════════════════════════════════")
    print()

    phone = input("📱 Telefon numarası (+90 ile başlat): ").strip()
    if not phone:
        print("Telefon numarası boş — iptal.")
        return

    await client.send_code_request(phone)
    print()

    code = input("🔑 Telegram'dan gelen doğrulama kodu: ").strip()
    if not code:
        print("Kod boş — iptal.")
        return

    try:
        await client.sign_in(phone, code)
    except SessionPasswordNeededError:
        print()
        pw = input("🔐 İki adımlı doğrulama şifresi: ").strip()
        await client.sign_in(password=pw)

    me = await client.get_me()
    print()
    print(f"✅ Giriş başarılı!  {me.first_name} (@{me.username})")
    print(f"   Oturum kaydedildi: {SESSION_PATH}.session")
    print()
    print("Şimdi backend'i yeniden başlat:")
    print("  docker compose restart backend")
    print()

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
