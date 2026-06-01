<div align="center">

<br/>

```
 ███████╗██╗      ██████╗ ██╗███████╗
 ██╔════╝██║     ██╔══██╗██║██╔════╝
 █████╗  ██║     ██████╔╝██║███████╗
 ██╔══╝  ██║     ██╔══██╗██║╚════██║
 ███████╗███████╗██████╔╝██║███████║
 ╚══════╝╚══════╝╚═════╝ ╚═╝╚══════╝
```

# Gerçek Zamanlı Olay İzleme Platformu

**GDELT · ACLED · Telegram → Canlı Harita**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-Vite-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?style=flat-square&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docker.com)
[![WebSocket](https://img.shields.io/badge/WebSocket-Canlı_Akış-FF6B35?style=flat-square)](#)

<br/>

**[🎥 Demo Videosu](#-demo)** · **[⚡ Hızlı Başlangıç](#-hızlı-başlangıç)** · **[🏗️ Mimari](#-mimari)** · **[📡 API](#-api-endpointleri)**

<br/>

</div>

---

## 🌍 Ne Yapar?

**ELBIS**, dünya genelindeki olayları —haber akışlarından, çatışma verilerinden ve sosyal medyadan— gerçek zamanlı olarak toplayıp tek bir harita arayüzünde sunar.

```
GDELT   (15 dak.)  ──┐
ACLED   (1 saat)   ──┼──► FastAPI ──► PostgreSQL ──► WebSocket ──► Leaflet Harita
Telegram (anlık)   ──┘
```

Sistem sürekli çalışır: veri kaynakları otomatik olarak sorgulanır, yeni olaylar PostgreSQL'e yazılır ve bağlı tüm istemcilere WebSocket üzerinden anlık iletilir.

---

## 🏗️ Mimari

```
┌─────────────────────────────────────────────────────────────────┐
│                        VERİ KAYNAKLARI                          │
│                                                                 │
│   ┌──────────────┐   ┌──────────────┐   ┌───────────────────┐  │
│   │    GDELT     │   │    ACLED     │   │     Telegram      │  │
│   │  15 dakika   │   │   1 saat    │   │      Anlık        │  │
│   │  (haber agg) │   │  (çatışma)  │   │   (kanal akışı)   │  │
│   └──────┬───────┘   └──────┬───────┘   └────────┬──────────┘  │
└──────────┼─────────────────┼────────────────────┼─────────────┘
           │                 │                    │
           └─────────────────▼────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                     BACKEND (FastAPI)                           │
│                                                                 │
│   gdelt.py ──────────────────────────────────► Scheduler       │
│   acled.py ──────────────────────────────────► (arka plan)     │
│   telegram_watcher.py (Telethon) ────────────► Sürekli izleme  │
│   location_extract.py ───────────────────────► Koordinat çıkar │
│                                                                 │
│   models.py (SQLAlchemy) + database.py (Async engine)          │
│   crud.py ─────────────────────────────────────────────────────┤
│                                                                 │
│   /events  ◄── HTTP REST          /ws ◄── WebSocket push       │
└────────────────────────┬────────────────────────────────────────┘
                         │  PostgreSQL 15
                         │  (kalıcı saklama)
┌────────────────────────▼────────────────────────────────────────┐
│                    FRONTEND (React + Vite)                      │
│                                                                 │
│   MapView.jsx ──► Leaflet harita                                │
│   WebSocket  ──► Canlı olay akışı                              │
│   HTTP yedek ──► Son 200 olay (bağlantı kopması senaryosu)     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎥 Demo

https://github.com/user-attachments/assets/45bee311-e935-4be1-ad7d-f0b611e0517c

---

## ⚡ Hızlı Başlangıç

**Gereksinimler:** Docker · Docker Compose

```bash
# 1. Repoyu klonla
git clone https://github.com/TITANBGG/Elbis.git
cd Elbis

# 2. Ortam değişkenlerini hazırla
cp backend/.env.example backend/.env
# → backend/.env dosyasını düzenle (aşağıdaki tabloya bak)

# 3. Derle ve çalıştır
docker compose up --build
```

| Servis | Adres |
|--------|-------|
| 🗺️ Frontend | http://localhost:5173 |
| ⚙️ Backend API | http://localhost:8000 |
| 📖 Swagger Docs | http://localhost:8000/docs |

---

## ⚙️ Yapılandırma

`backend/.env.example` şablonundan `.env` dosyasını oluştur:

| Değişken | Açıklama | Zorunlu |
|----------|----------|---------|
| `DATABASE_URL` | PostgreSQL bağlantı dizesi | ✅ Evet |
| `ACLED_KEY` | ACLED API anahtarı ([kayıt](https://acleddata.com/register)) | ⬜ Hayır |
| `ACLED_EMAIL` | ACLED hesap e-postası | ⬜ Hayır |
| `TG_API_ID` | Telegram API kimliği | ⬜ Hayır |
| `TG_API_HASH` | Telegram API hash | ⬜ Hayır |

> **Not:** GDELT herhangi bir API anahtarı gerektirmez ve varsayılan olarak aktiftir.

### Telegram Oturumu Oluşturma

`TG_API_ID` ve `TG_API_HASH` ayarlandıktan sonra, tek seferlik kimlik doğrulama için:

```bash
docker exec -it elbis-backend-1 python /app/telegram_auth.py
```

Oturum dosyası `backend/data/` dizinine yazılır; container yeniden başlasa da korunur.

---

## 📡 API Endpointleri

| Method | Yol | Açıklama |
|--------|-----|----------|
| `GET` | `/health` | Servis sağlık kontrolü |
| `GET` | `/events` | Son 200 olayı döndür (HTTP yedek) |
| `POST` | `/debug/fetch` | Manuel GDELT çekimi tetikle |
| `WS` | `/ws` | Canlı olay akışı (WebSocket) |

---

## 🗂️ Proje Yapısı

```
Elbis/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI uygulaması, WebSocket, arka plan görevleri
│   │   ├── models.py            # SQLAlchemy Event modeli
│   │   ├── database.py          # Async engine ve session factory
│   │   ├── crud.py              # Veritabanı işlemleri (upsert, query)
│   │   ├── gdelt.py             # GDELT veri çekici (15 dak. scheduler)
│   │   ├── acled.py             # ACLED veri çekici (1 saat scheduler)
│   │   ├── telegram_watcher.py  # Telethon tabanlı Telegram izleyici
│   │   └── location_extract.py  # Koordinat çıkarma yardımcıları
│   ├── telegram_auth.py         # Telegram oturum oluşturucu (tek seferlik)
│   ├── data/                    # Çalışma zamanı verileri (git'te izlenmez)
│   ├── .env.example
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx
│   │   └── MapView.jsx          # Leaflet harita + WebSocket entegrasyonu
│   ├── index.html
│   └── Dockerfile
└── docker-compose.yml
```

---

## 📊 Veri Kaynakları

| Kaynak | Güncelleme | Kapsam | API Anahtarı |
|--------|-----------|--------|--------------|
| **GDELT** | 15 dakika | Dünya geneli haber agregasyonu | Gerekmez |
| **ACLED** | 1 saat | Araştırma kalitesi çatışma verileri | Gerekir (ücretsiz) |
| **Telegram** | Anlık | Seçili kanal mesaj akışı | Gerekir |

---

## 🛠️ Teknoloji Yığını

```
Backend     │  Python 3.11+  ·  FastAPI  ·  SQLAlchemy (Async)  ·  Telethon
Veritabanı  │  PostgreSQL 15
Frontend    │  React  ·  Vite  ·  Leaflet
İletişim    │  WebSocket (canlı push)  ·  REST HTTP (yedek)
Altyapı     │  Docker  ·  Docker Compose
```

---

## 📄 Lisans

Bu proje [MIT Lisansı](LICENSE) kapsamında lisanslanmıştır.
