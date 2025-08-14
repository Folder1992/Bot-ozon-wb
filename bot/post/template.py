# bot/post/template.py
from __future__ import annotations
from urllib.parse import urlsplit, urlunsplit

def _short_url(url: str) -> str:
    if not url:
        return ""
    parts = list(urlsplit(url))
    parts[3] = ""  # query
    parts[4] = ""  # fragment
    return urlunsplit(parts)

def _fmt_price(price) -> str | None:
    if price is None:
        return None
    try:
        s = str(price).replace("\u00A0", "").replace(" ", "")
        n = int(float(s))
        return f"{n:,}".replace(",", " ") + " ₽"
    except Exception:
        return str(price)

def _smart_trim(text: str, limit: int = 520) -> str:
    """Обрезаем по границе слов, без «оборванных» окончаний."""
    t = " ".join((text or "").split())
    if len(t) <= limit:
        return t
    cut = t[:limit].rstrip()
    for sep in (" ", " — ", ". ", ", ", "; "):
        p = cut.rfind(sep)
        if p >= int(limit * 0.6):
            return cut[:p].rstrip() + "…"
    return cut + "…"

def make_post(
    title: str,
    url: str,
    description: str | None = None,
    rating: str | None = None,
    reviews: int | None = None,
    price: str | int | float | None = None,
    source: str | None = None,
) -> str:
    site = (source or "").lower()
    site_name = "Ozon" if site.startswith("oz") else "Wildberries" if site.startswith("wb") else "сайте"
    short_url = _short_url(url)

    parts = [f"<b>Название:</b> {title or 'Товар'}"]

    # Цена — отдельной строкой СВЕРХУ
    if price is not None:
        label = "💳 <b>Стоимость (по карте Ozon):</b>" if site.startswith("oz") else "💰 <b>Стоимость:</b>"
        parts.append(f"{label} {_fmt_price(price)}")

    # Ниже — оценка и отзывы
    rr = []
    if rating:
        rr.append(f"⭐ <b>Оценка:</b> {rating}")
    if reviews is not None:
        rr.append(f"🗣️ <b>Отзывов:</b> {reviews}")
    if rr:
        parts.append(" | ".join(rr))

    if description:
        parts.append(f"📝 <b>Описание:</b> {_smart_trim(description)}")

    # Ссылка спрятана под кликаемый текст
    parts.append(f"🔗 <b>Ссылка:</b> <a href=\"{short_url}\">Открыть на {site_name}</a>")

    tag = "#ozon" if site.startswith("oz") else "#wildberries" if site.startswith("wb") else "#marketplace"
    parts.append(f"{tag} #находки")
    return "\n".join(parts)
