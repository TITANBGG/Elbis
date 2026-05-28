"""
Telegram mesajlarından Ukrayna şehir adlarını çıkar ve koordinat döndür.

Desteklenen diller: İngilizce, Ukraynaca (Latin + Kiril), Rusça (Kiril).
Önce uzun/özgün adlar aranır, sonra kısa varyantlar — yanlış eşleşmeyi önler.
"""

from __future__ import annotations
import re
from typing import Optional

# ── Şehir sözlüğü ─────────────────────────────────────────────────────────────
# Her girdi: arama_anahtarı → (lat, lon, görünen_ad)
# Uzun varyantlar önce gelir → kısa öneklerle yanlış eşleşmeyi engeller.
_CITIES: dict[str, tuple[float, float, str]] = {
    # ── Büyük şehirler ────────────────────────────────────────────────────────
    "kyiv":              (50.4501, 30.5234, "Kyiv"),
    "kiev":              (50.4501, 30.5234, "Kyiv"),
    "київ":              (50.4501, 30.5234, "Kyiv"),
    "киев":              (50.4501, 30.5234, "Kyiv"),

    "kharkiv":           (49.9935, 36.2304, "Kharkiv"),
    "харків":            (49.9935, 36.2304, "Kharkiv"),
    "харьков":           (49.9935, 36.2304, "Kharkiv"),

    "odesa":             (46.4825, 30.7233, "Odesa"),
    "odessa":            (46.4825, 30.7233, "Odesa"),
    "одеса":             (46.4825, 30.7233, "Odesa"),
    "одесса":            (46.4825, 30.7233, "Odesa"),

    "dnipro":            (48.4647, 35.0462, "Dnipro"),
    "дніпро":            (48.4647, 35.0462, "Dnipro"),
    "днепр":             (48.4647, 35.0462, "Dnipro"),

    "zaporizhzhia":      (47.8388, 35.1396, "Zaporizhzhia"),
    "zaporizhia":        (47.8388, 35.1396, "Zaporizhzhia"),
    "запоріжжя":         (47.8388, 35.1396, "Zaporizhzhia"),
    "запорожье":         (47.8388, 35.1396, "Zaporizhzhia"),

    "lviv":              (49.8397, 24.0297, "Lviv"),
    "львів":             (49.8397, 24.0297, "Lviv"),
    "львов":             (49.8397, 24.0297, "Lviv"),

    "mykolaiv":          (46.9750, 31.9946, "Mykolaiv"),
    "mikolaiv":          (46.9750, 31.9946, "Mykolaiv"),
    "николаев":          (46.9750, 31.9946, "Mykolaiv"),
    "миколаїв":          (46.9750, 31.9946, "Mykolaiv"),

    "kherson":           (46.6354, 32.6169, "Kherson"),
    "херсон":            (46.6354, 32.6169, "Kherson"),

    "mariupol":          (47.0971, 37.5433, "Mariupol"),
    "маріуполь":         (47.0971, 37.5433, "Mariupol"),
    "мариуполь":         (47.0971, 37.5433, "Mariupol"),

    "kramatorsk":        (48.7337, 37.5636, "Kramatorsk"),
    "краматорськ":       (48.7337, 37.5636, "Kramatorsk"),
    "краматорск":        (48.7337, 37.5636, "Kramatorsk"),

    # ── Çatışma hattı şehirleri ───────────────────────────────────────────────
    "bakhmut":           (48.5956, 38.0002, "Bakhmut"),
    "бахмут":            (48.5956, 38.0002, "Bakhmut"),
    "артемівськ":        (48.5956, 38.0002, "Bakhmut"),

    "avdiivka":          (48.1390, 37.7589, "Avdiivka"),
    "авдіївка":          (48.1390, 37.7589, "Avdiivka"),
    "авдеевка":          (48.1390, 37.7589, "Avdiivka"),

    "soledar":           (48.6804, 38.0861, "Soledar"),
    "соледар":           (48.6804, 38.0861, "Soledar"),

    "kupiansk":          (49.7082, 37.6118, "Kupiansk"),
    "купянськ":          (49.7082, 37.6118, "Kupiansk"),
    "купянск":           (49.7082, 37.6118, "Kupiansk"),

    "lyman":             (48.9842, 37.8139, "Lyman"),
    "лиман":             (48.9842, 37.8139, "Lyman"),

    "severodonetsk":     (48.9483, 38.4867, "Severodonetsk"),
    "сєвєродонецьк":     (48.9483, 38.4867, "Severodonetsk"),

    "lysychansk":        (48.9085, 38.4374, "Lysychansk"),
    "лисичанськ":        (48.9085, 38.4374, "Lysychansk"),

    "vuhledar":          (47.7737, 37.2535, "Vuhledar"),
    "вугледар":          (47.7737, 37.2535, "Vuhledar"),

    "marinka":           (47.9520, 37.5100, "Marinka"),
    "мар'їнка":          (47.9520, 37.5100, "Marinka"),

    "toretsk":           (48.0158, 37.8478, "Toretsk"),
    "торецьк":           (48.0158, 37.8478, "Toretsk"),

    "pokrovsk":          (48.2796, 37.1760, "Pokrovsk"),
    "покровськ":         (48.2796, 37.1760, "Pokrovsk"),

    "chasiv yar":        (48.5636, 37.8559, "Chasiv Yar"),
    "часів яр":          (48.5636, 37.8559, "Chasiv Yar"),

    "kurakhove":         (47.9885, 37.2744, "Kurakhove"),
    "курахове":          (47.9885, 37.2744, "Kurakhove"),

    # ── Kuzey / Doğu bölgesi ─────────────────────────────────────────────────
    "kharkiv oblast":    (49.9935, 36.2304, "Kharkiv Oblast"),
    "izium":             (49.2088, 37.2772, "Izium"),
    "ізюм":              (49.2088, 37.2772, "Izium"),

    "sumy":              (50.9077, 34.7981, "Sumy"),
    "суми":              (50.9077, 34.7981, "Sumy"),

    "chernihiv":         (51.4982, 31.2893, "Chernihiv"),
    "чернігів":          (51.4982, 31.2893, "Chernihiv"),

    # ── Batı / Merkez ─────────────────────────────────────────────────────────
    "zhytomyr":          (50.2547, 28.6588, "Zhytomyr"),
    "житомир":           (50.2547, 28.6588, "Zhytomyr"),

    "poltava":           (49.5883, 34.5514, "Poltava"),
    "полтава":           (49.5883, 34.5514, "Poltava"),

    "rivne":             (50.6197, 26.2514, "Rivne"),
    "рівне":             (50.6197, 26.2514, "Rivne"),

    "vinnytsia":         (49.2331, 28.4682, "Vinnytsia"),
    "вінниця":           (49.2331, 28.4682, "Vinnytsia"),

    "kremenchuk":        (49.0669, 33.4162, "Kremenchuk"),
    "кременчук":         (49.0669, 33.4162, "Kremenchuk"),

    "kryvyi rih":        (47.9516, 33.3964, "Kryvyi Rih"),
    "кривий ріг":        (47.9516, 33.3964, "Kryvyi Rih"),
    "кривой рог":        (47.9516, 33.3964, "Kryvyi Rih"),

    # ── Güney ─────────────────────────────────────────────────────────────────
    "melitopol":         (46.8462, 35.3631, "Melitopol"),
    "мелітополь":        (46.8462, 35.3631, "Melitopol"),

    "berdyansk":         (46.7635, 36.7955, "Berdyansk"),
    "бердянськ":         (46.7635, 36.7955, "Berdyansk"),

    "energodar":         (47.5005, 34.6600, "Energodar"),
    "енергодар":         (47.5005, 34.6600, "Energodar"),

    # ── Kırım ─────────────────────────────────────────────────────────────────
    "simferopol":        (44.9521, 34.1024, "Simferopol"),
    "сімферополь":       (44.9521, 34.1024, "Simferopol"),

    "sevastopol":        (44.6167, 33.5254, "Sevastopol"),
    "севастополь":       (44.6167, 33.5254, "Sevastopol"),

    "kerch":             (45.3531, 36.4681, "Kerch"),
    "керч":              (45.3531, 36.4681, "Kerch"),

    # ── Luhansk bölgesi ───────────────────────────────────────────────────────
    "luhansk":           (48.5740, 39.3082, "Luhansk"),
    "луганськ":          (48.5740, 39.3082, "Luhansk"),
    "lugansk":           (48.5740, 39.3082, "Luhansk"),

    "donetsk":           (48.0159, 37.8028, "Donetsk"),
    "донецьк":           (48.0159, 37.8028, "Donetsk"),
    "донецк":            (48.0159, 37.8028, "Donetsk"),
}

# Uzun anahtarları önce ara (kısa öneklerin yanlış eşlemesini engelle)
_SORTED_KEYS = sorted(_CITIES.keys(), key=len, reverse=True)

# Kelime sınırı olmadan arama (Kiril için word boundary güvenilmez)
_PATTERNS: list[tuple[re.Pattern, tuple[float, float, str]]] = [
    (re.compile(re.escape(k), re.IGNORECASE), v)
    for k, v in ((k, _CITIES[k]) for k in _SORTED_KEYS)
]


def find_location(text: str) -> Optional[dict]:
    """
    Metinde geçen ilk Ukrayna şehrini bul ve koordinatlarını döndür.
    Bulunmazsa None döner.

    Dönen dict: {"lat": float, "lon": float, "name": str}
    """
    for pattern, (lat, lon, name) in _PATTERNS:
        if pattern.search(text):
            return {"lat": lat, "lon": lon, "name": name}
    return None
