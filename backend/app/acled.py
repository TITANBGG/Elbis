"""
ACLED (Armed Conflict Location & Event Data) entegrasyonu.

Ücretsiz API key almak için:  https://acleddata.com/register
Alınan key ve e-posta adresini .env dosyasına ekle:

    ACLED_KEY=your_key_here
    ACLED_EMAIL=your@email.com

Key girilmezse bu modül sessizce devre dışı kalır — sistem çalışmaya devam eder.
"""

import datetime
import os
import httpx

_UTC = datetime.timezone.utc

ACLED_KEY   = os.getenv("ACLED_KEY",   "")
ACLED_EMAIL = os.getenv("ACLED_EMAIL", "")
ENABLED     = bool(ACLED_KEY and ACLED_EMAIL)

ACLED_URL = "https://api.acleddata.com/acled/read"

# ACLED olay tipi → CAMEO benzeri kısa kod (sadece görünüm için)
EVENT_TYPE_MAP: dict[str, str] = {
    "Battles":                       "19",
    "Violence against civilians":     "18",
    "Explosions/Remote violence":     "19",
    "Protests":                       "14",
    "Riots":                          "14",
    "Strategic developments":         "15",
}


async def fetch_acled_ukraine(days_back: int = 2) -> list[dict]:
    """
    ACLED'den son `days_back` güne ait Ukrayna olaylarını çek.
    API key yoksa boş liste döndürür.
    """
    if not ENABLED:
        return []

    since = (datetime.datetime.now(_UTC) - datetime.timedelta(days=days_back)).strftime("%Y-%m-%d")

    params = {
        "key":              ACLED_KEY,
        "email":            ACLED_EMAIL,
        "country":          "Ukraine",
        "limit":            500,
        "event_date":       since,
        "event_date_where": ">=",
        "fields":           (
            "data_id|event_date|event_type|sub_event_type|"
            "location|latitude|longitude|source|notes|timestamp"
        ),
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(ACLED_URL, params=params)
        resp.raise_for_status()

    rows = resp.json().get("data", [])
    events: list[dict] = []

    for row in rows:
        try:
            lat = float(row.get("latitude", 0))
            lon = float(row.get("longitude", 0))
        except (TypeError, ValueError):
            continue
        if lat == 0.0 and lon == 0.0:
            continue

        # ── Zaman damgası ───────────────────────────────────────────────
        ts_raw = row.get("timestamp") or row.get("event_date", "")
        try:
            if str(ts_raw).isdigit():
                ts = datetime.datetime.fromtimestamp(int(ts_raw), tz=_UTC)
            else:
                ts = datetime.datetime.fromisoformat(str(ts_raw))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=_UTC)
        except Exception:
            ts = datetime.datetime.now(_UTC)

        event_type  = row.get("event_type", "")
        sub_type    = row.get("sub_event_type", "")
        location    = row.get("location", "—")
        source      = row.get("source", "ACLED")
        notes       = (row.get("notes") or "")[:500]
        event_code  = EVENT_TYPE_MAP.get(event_type, "00")

        events.append({
            "source_id":   f"acled_{row['data_id']}",
            "lat":         lat,
            "lon":         lon,
            "event_code":  event_code,
            "title":       f"{location} — {sub_type or event_type}"[:500],
            "description": notes or None,
            "src":         source[:50],
            "url":         None,
            "timestamp":   ts,
            "country":     "UP",
            "source_type": "ACLED",
        })

    return events
