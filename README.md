# ELBIS

Gerçek zamanlı olay izleme platformu. GDELT, ACLED ve Telegram kanallarından veri çekip PostgreSQL'de depolar; WebSocket üzerinden harita arayüzüne canlı olarak iletir.

## Mimari

```
┌─────────────────────────────────────────────────────┐
│  Veri Kaynakları          Backend (FastAPI)          │
│  ─────────────────        ───────────────────────    │
│  GDELT   (15 dak.)  ───►  /events  HTTP endpoint     │
│  ACLED   (1 saat)   ───►  /ws      WebSocket push    │
│  Telegram (anlık)   ───►  PostgreSQL (kalıcı saklama)│
└─────────────────────────────────────────────────────┘
                               │
                        WebSocket / HTTP
                               │
                    ┌──────────▼──────────┐
                    │  Frontend (React)    │
                    │  Leaflet harita      │
                    │  Canlı olay akışı    │
                    └─────────────────────┘
```

## Servisler

| Servis     | Teknoloji               | Port  |
|------------|-------------------------|-------|
| backend    | FastAPI + SQLAlchemy    | 8000  |
| frontend   | React + Vite + Leaflet  | 5173  |
| postgres   | PostgreSQL 15           | 5432  |

## Hızlı Başlangıç

Docker ve Docker Compose gereklidir.

```powershell
# 1. Repoyu klonla
git clone https://github.com/TITANBGG/Elbis.git
cd Elbis

# 2. Ortam değişkenlerini hazırla
Copy-Item backend\.env.example backend\.env

# 3. Çalıştır
docker compose up --build
```

Arayüzler:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- Swagger dokümantasyonu: http://localhost:8000/docs

## Yapılandırma

`backend/.env` dosyasını `.env.example` şablonundan oluşturun:

| Değişken       | Açıklama                              | Zorunlu |
|----------------|---------------------------------------|---------|
| `DATABASE_URL` | PostgreSQL bağlantı dizesi            | Evet    |
| `ACLED_KEY`    | ACLED API anahtarı                    | Hayır   |
| `ACLED_EMAIL`  | ACLED hesap e-postası                 | Hayır   |
| `TG_API_ID`    | Telegram API kimliği                  | Hayır   |
| `TG_API_HASH`  | Telegram API hash                     | Hayır   |

### Telegram Oturumu Oluşturma

`TG_API_ID` ve `TG_API_HASH` ayarlandıktan sonra:

```powershell
docker exec -it elbis-backend-1 python /app/telegram_auth.py
```

Oturum dosyası `backend/data/` dizinine yazılır ve container yeniden başlasa da korunur.

## API Endpoint'leri

| Method | Yol              | Açıklama                              |
|--------|------------------|---------------------------------------|
| GET    | `/health`        | Servis sağlık kontrolü                |
| GET    | `/events`        | Son 200 olayı döndür (HTTP yedek)     |
| POST   | `/debug/fetch`   | Manuel GDELT çekimi tetikle           |
| WS     | `/ws`            | Canlı olay akışı (WebSocket)          |

## Proje Yapısı

```
Elbis/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI uygulaması, WebSocket, arka plan görevleri
│   │   ├── models.py            # SQLAlchemy Event modeli
│   │   ├── database.py          # Async engine ve session factory
│   │   ├── crud.py              # Veritabanı işlemleri (upsert, query)
│   │   ├── gdelt.py             # GDELT veri çekici
│   │   ├── acled.py             # ACLED veri çekici
│   │   ├── telegram_watcher.py  # Telethon tabanlı Telegram izleyici
│   │   └── location_extract.py  # Koordinat çıkarma yardımcıları
│   ├── telegram_auth.py         # Telegram oturum oluşturucu (tek seferlik)
│   ├── data/                    # Çalışma zamanı verileri (git'te izlenmez)
│   ├── .env.example             # Ortam değişkeni şablonu
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx
│   │   └── MapView.jsx
│   ├── index.html
│   └── Dockerfile
└── docker-compose.yml
```

## Veri Kaynakları

- **GDELT** — Dünya geneli haber agregasyonu, 15 dakikada bir güncellenir. API anahtarı gerektirmez.
- **ACLED** — Araştırma kalitesi çatışma verileri. [Ücretsiz kayıt](https://acleddata.com/register) gerektirir.
- **Telegram** — Seçili kanallardan anlık mesaj akışı. Telegram API kimlik bilgileri gerektirir.
