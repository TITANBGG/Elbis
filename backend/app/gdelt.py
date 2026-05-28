"""
GDELT v2 — 15 dakikada bir güncellenen olay akışını çeker ve
veritabanına uygun formatta döndürür.
"""

import asyncio
import csv
import datetime
import io
import requests
import zipfile
from typing import Optional

_UTC = datetime.timezone.utc

LASTUPDATE_URL = "http://data.gdeltproject.org/gdeltv2/lastupdate.txt"

# ── CAMEO olay kodu → Türkçe etiket ──────────────────────────────────────────
# GDELT, CAMEO (Conflict and Mediation Event Observations) kodlarını kullanır.
# Üst iki rakam ana kategoriyi belirler.
CAMEO_TR: dict[str, str] = {
    "01": "Sözlü İşbirliği",
    "02": "Çağrı / Talep",
    "03": "İşbirliği Niyeti",
    "04": "Danışma / Görüşme",
    "05": "Diplomatik İşbirliği",
    "06": "Maddi Destek",
    "07": "Yardım / Tedarik",
    "08": "Taviz / Geri Adım",
    "09": "Soruşturma",
    "10": "Baskı / İstek",
    "11": "Kınama / Eleştiri",
    "12": "Ret / İnkâr",
    "13": "Tehdit",
    "14": "Protesto",
    "15": "Güç Gösterisi",
    "16": "İlişkileri Kesme",
    "17": "Zorlama",
    "18": "Saldırı / Şiddet",
    "19": "Çatışma / Muharebe",
    "20": "Toplu Şiddet",
}


def cameo_label(code: str) -> str:
    """CAMEO kodu → okunabilir etiket (ör. '190' → 'Çatışma / Muharebe')."""
    prefix = code[:2] if len(code) >= 2 else code
    return CAMEO_TR.get(prefix, f"Olay [{code}]")


def _parse_gdelt_timestamp(sql_date: str, month_year: str) -> datetime.datetime:
    """GDELT'in SQLDATE (YYYYMMDD) ve MonthYear (YYYYMM) alanlarından datetime üret."""
    try:
        year  = int(sql_date[:4])
        month = int(sql_date[4:6])
        day   = int(sql_date[6:8])
        # MonthYear'ın ilk 2 karakteri saat olarak yorumlanır (mevcut kod mantığı)
        hour  = int(month_year[:2]) if month_year and month_year[:2].isdigit() else 0
        return datetime.datetime(year, month, day, hour, 0, 0, tzinfo=_UTC)
    except Exception:
        return datetime.datetime.now(_UTC)


def _best_location(row: list[str]) -> str:
    """
    Satırın konum sütunlarından okunabilir bir yer adı bul.

    GDELT v2 Event Export sütun haritası (0-tabanlı, doğrulanmış):
      52 → ActionGeo_FullName   ← öncelikli kaynak
      36 → Actor1Geo_FullName
      44 → Actor2Geo_FullName
    """
    for col in (52, 36, 44):
        try:
            val = row[col].strip()
            # Sadece boş veya saf-sayısal değerleri atla
            if val and not val.replace(".", "").replace("-", "").lstrip("-").isdigit():
                return val.split(",")[0].strip()  # ilk parça genellikle şehir adı
        except IndexError:
            pass
    return ""


def parse_export_csv(
    content: bytes,
    limit: int = 200,
    only_country: Optional[str] = None,
) -> list[dict]:
    """
    GDELT export CSV'sini ayrıştır ve DB'ye uygun dict listesi döndür.

    Sütun eşlemeleri (0-tabanlı, GDELT v2 Event Export — container içinde doğrulandı):
      0   GLOBALEVENTID
      1   SQLDATE
      2   MonthYear
      26  EventCode
      52  ActionGeo_FullName     ← konum adı
      53  ActionGeo_CountryCode  ← ülke filtresi ('UP' = Ukrayna)
      56  ActionGeo_Lat
      57  ActionGeo_Long
      60  SOURCEURL
    """
    text = content.decode("utf-8", errors="replace")
    reader = csv.reader(io.StringIO(text), delimiter="\t")
    events: list[dict] = []

    for index, row in enumerate(reader):
        if len(events) >= limit:
            break
        if len(row) < 61:
            continue

        # ── Ülke filtresi ───────────────────────────────────────────────
        country = row[53].strip()
        if only_country and country != only_country:
            continue

        # ── Konum ──────────────────────────────────────────────────────
        try:
            lat = float(row[56].strip())
            lon = float(row[57].strip())
        except (ValueError, IndexError):
            continue
        if lat == 0.0 and lon == 0.0:
            continue

        # ── Olay kimliği ────────────────────────────────────────────────
        try:
            raw_id = int(row[0].strip())
        except (ValueError, IndexError):
            raw_id = index

        source_id = f"gdelt_{raw_id}"

        # ── Olay kodu & başlık ──────────────────────────────────────────
        event_code = row[26].strip() if len(row) > 26 else ""
        location   = _best_location(row)
        label      = cameo_label(event_code)
        title      = f"{location} — {label}" if location else label

        # ── Kaynak URL ──────────────────────────────────────────────────
        source_url = row[60].strip() if len(row) > 60 else ""

        # ── Zaman damgası ───────────────────────────────────────────────
        timestamp = _parse_gdelt_timestamp(row[1].strip(), row[2].strip())

        events.append({
            "source_id":   source_id,
            "lat":         lat,
            "lon":         lon,
            "event_code":  event_code,
            "title":       title[:500],
            "description": f"CAMEO {event_code}: {label}",
            "src":         "GDELT",
            "url":         source_url or None,
            "timestamp":   timestamp,
            "country":     country or "UP",
            "source_type": "GDELT",
        })

    return events


def fetch_latest_export_events(
    limit: int = 200,
    only_country: Optional[str] = None,
) -> list[dict]:
    """GDELT'in son export dosyasını indir, ayrıştır ve döndür (senkron)."""
    # 1. Son güncelleme listesini al
    r = requests.get(LASTUPDATE_URL, timeout=30)
    r.raise_for_status()

    export_url: Optional[str] = None
    for line in r.text.splitlines():
        if line.strip().endswith(".export.CSV.zip"):
            parts = line.split()
            export_url = parts[-1]
            break

    if not export_url:
        return []

    # 2. ZIP dosyasını indir ve aç
    zresp = requests.get(export_url, timeout=60)
    zresp.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(zresp.content)) as zf:
        csv_name = next(
            (n for n in zf.namelist() if n.endswith(".export.CSV")), None
        )
        if not csv_name:
            return []
        with zf.open(csv_name) as fh:
            content = fh.read()

    return parse_export_csv(content, limit=limit, only_country=only_country)


# ── Periyodik görev (main.py tarafından başlatılır) ───────────────────────────
async def periodic_fetch_and_store(interval_seconds: int = 900):
    """
    Eski uyumluluk fonksiyonu — main.py'nin gdelt_loop() ile değiştirildi.
    Yalnızca direkt çağrı için burada bırakıldı.
    """
    while True:
        await asyncio.sleep(interval_seconds)
