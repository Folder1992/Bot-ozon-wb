from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from ..config import settings
from ..utils.logging import setup_logging
from ..utils.pwhelper import run_get_page_data
from .utils import parse_ld_list, first_product, product_fields, normalize_urls

setup_logging()
log = logging.getLogger("bot.parsers.ozon")


def _digits(n: Any) -> Optional[int]:
    if n is None:
        return None
    s = str(n)
    nums = "".join(ch for ch in s if ch.isdigit())
    return int(nums) if nums else None


def _price_from_composer(comp: Dict[str, Any]) -> tuple[Optional[int], Optional[int]]:
    """
    Ищем блок webPrice-* внутри widgetStates Composer-а.
    Возвращаем (card_price, regular_price) — в рублях.
    """
    if not isinstance(comp, dict):
        return None, None

    ws = comp.get("widgetStates") or {}
    if not isinstance(ws, dict):
        return None, None

    card_price = None
    regular_price = None

    for key, raw in ws.items():
        if not isinstance(key, str) or "webPrice-" not in key:
            continue
        try:
            data = json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            continue

        # Часто прямо на верхнем уровне
        card_price = card_price or _digits(data.get("cardPrice") or data.get("ozonCardPrice"))
        regular_price = regular_price or _digits(data.get("price") or data.get("basePrice"))

        # Иногда цена лежит внутри вложенных структур
        block = data.get("priceBlock") or {}
        if isinstance(block, dict):
            card_price = card_price or _digits(block.get("cardPrice") or block.get("ozonCardPrice"))
            regular_price = regular_price or _digits(block.get("price") or block.get("basePrice"))

        # Нашли оба — хватит
        if card_price or regular_price:
            break

    return card_price, regular_price


def _price_from_html(html: str) -> tuple[Optional[int], Optional[int]]:
    """
    Из статики: <div id="state-webPrice-... " data-state="...json...">
    """
    if not html:
        return None, None

    m = re.search(
        r'id="state-webPrice-[^"]+"\s+data-state="([^"]+)"',
        html,
    )
    if not m:
        return None, None

    try:
        # Внутри чаще всего обычный JSON (без экранирования), но на всякий случай заменим &quot;
        raw = m.group(1)
        raw = raw.replace("&quot;", '"')
        data = json.loads(raw)
    except Exception:
        return None, None

    return _digits(data.get("cardPrice")), _digits(data.get("price"))


def parse_ozon(url: str) -> Dict[str, Any]:
    """
    Возвращает:
      title, description, rating, reviews, price (цена с Ozon Картой, если доступна),
      images, videos
    """
    r = run_get_page_data(url, settings, site="ozon") or {}
    html = r.get("html", "") or ""
    comp = r.get("composer") or {}

    title = description = rating = None
    reviews = None
    price: Optional[int] = None
    images: List[str] = []
    videos: List[str] = []

    # 1) JSON-LD, если есть (часто закрывает title/desc/rating/reviews/images)
    ld = parse_ld_list(html, r.get("ld_scripts") or [])
    product = first_product(ld)
    if product:
        t, d, rat, rev, imgs = product_fields(product)
        title = title or t
        description = description or d
        rating = rating or rat
        reviews = reviews or rev
        images = normalize_urls(images + imgs)

    # 2) Галерея из Composer: webGallery-*
    ws = comp.get("widgetStates") or {}
    if isinstance(ws, dict):
        for k, v in ws.items():
            if not isinstance(k, str) or "webGallery-" not in k:
                continue
            try:
                data = json.loads(v) if isinstance(v, str) else v
            except Exception:
                continue
            arr = []
            # классический массив [{"src": "..."}]
            for it in data.get("images") or []:
                src = (it or {}).get("src")
                if src:
                    arr.append(src)
            # единичный cover
            cover = data.get("coverImage")
            if cover:
                arr.append(cover)
            if arr:
                images = normalize_urls(images + arr)
                break

    # 3) Цена — жёстко из webPrice (Composer → HTML)
    card_price, regular_price = _price_from_composer(comp)
    if card_price is None and regular_price is None:
        card_price, regular_price = _price_from_html(html)

    # Берём именно цену по карте, если она есть; иначе обычную
    price = card_price or regular_price or None

    # 4) Fallback на OG-картинку (редко нужно)
    if not images:
        og = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', html)
        if og:
            images = [og.group(1)]

    # Минимальная нормализация title
    if not title:
        m = re.search(r"<title>([^<]+)</title>", html)
        if m:
            title = m.group(1).strip()

    return {
        "title": title or "Товар",
        "description": description,
        "rating": rating,
        "reviews": reviews,
        "price": price,
        "images": images,
        "videos": videos,
    }
