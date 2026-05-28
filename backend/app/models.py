import datetime
from sqlalchemy import String, Float, DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

_UTC = datetime.timezone.utc


class Event(Base):
    __tablename__ = "events"

    # ── Birincil anahtar (otomatik artan) ──────────────────────────────
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ── Harici kaynak kimliği — tekrarlı kayıtları önler (unique) ──────
    # Örnekler: "gdelt_1234567890", "acled_987654"
    source_id: Mapped[str] = mapped_column(String(120), unique=True, index=True)

    # ── Konum ──────────────────────────────────────────────────────────
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)

    # ── Olay bilgisi ───────────────────────────────────────────────────
    event_code:  Mapped[str]       = mapped_column(String(20),   default="")
    title:       Mapped[str]       = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text,         nullable=True)
    src:         Mapped[str]       = mapped_column(String(50))   # GDELT / ACLED / TELEGRAM
    url:         Mapped[str | None] = mapped_column(String(1000), nullable=True)
    country:     Mapped[str]       = mapped_column(String(5),    default="UP")
    source_type: Mapped[str]       = mapped_column(String(20))   # GDELT / ACLED / TELEGRAM

    # ── Zaman damgaları ────────────────────────────────────────────────
    timestamp:  Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(_UTC),
    )

    # ── Frontend için serileştirme ─────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "id":          self.id,
            "source_id":   self.source_id,
            "lat":         self.lat,
            "lon":         self.lon,
            "event_code":  self.event_code,
            "title":       self.title,
            "description": self.description,
            "src":         self.src,
            "url":         self.url,
            "timestamp":   self.timestamp.isoformat() if self.timestamp else None,
            "country":     self.country,
            "source_type": self.source_type,
        }
