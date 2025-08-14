from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

import httpx

from ..config import settings
from ..utils.logging import setup_logging
from ..utils.pwhelper import run_get_page_data
from .utils import parse_ld_list, first_product, product_fields, normalize_urls

setup_logging()
log = logging.getLogger("bot.parsers.wb")

DESTS = ["-1257786", "-239094", "-5617406", "123585148", "123582156", "-80302"]
SPP = [0, 1, 30]


def _nm_from(url: str, html: str) -> str:
    m = re.search(r"/catalog/(\d+)/", url)
    if m:
        return m.group(1)
    m = re.search(r"(?:Артикул|nmId|nm_id|productId)[^\d]{0,16}(\d{6,12})", html or "", re.I)
    return m.group(1) if m else ""


def _json(url: str) -> Optional[dict]:
    try:
        with httpx.Client(timeout=10, follow_redirects=True) as c:
            r = c.get(url, headers={"Accept": "application/json"})
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


def _best_product(nm: str) -> Optional[Dict[str, Any]]:
    best = None
    best_price = None
    for spp in SPP:
        for dest in DESTS:
            url = f"https://card.wb.ru/cards/v2/detail?appType=1&curr=rub&dest={dest}&spp={spp}&nm={nm}"
            log.info("WB API try: %s", url)
            data = _json(url)
            if not isinstance(data, dict):
                continue
            products = (data.get("data") or {}).get("products") or []
            if not products:
                continue
            prod = products[0]

            # оценим цену
            p = None
            for k in ("salePriceU", "priceU", "salePrice", "price"):
                v = prod.get(k)
                if isinstance(v, (int, float)):
                    p = int(round(float(v) / 100))
                    break
            if p is None:
                continue

            if best_price is None or p < best_price:
                best, best_price = prod, p
    return best


def _head_ok(url: str) -> bool:
    try:
        with httpx.Client(timeout=6, follow_redirects=True) as c:
            r = c.head(url)
        return r.status_code == 200
    except Exception:
        return False


def _pick_image_base(nm: str) -> Optional[tuple[str, str]]:
    """
    Возвращает кортеж (base_url, ext), где base_url = .../images/{folder} (без '/1.ext').
    Проверяем только первый кадр (1.webp/jpg) и запоминаем расширение.
    """
    try:
        n = int(nm)
    except Exception:
        return None

    vol = n // 100000
    part = n // 1000

    folders = ("big", "c516x688", "c246x328")
    exts = ("webp", "jpg")
    templates = (
        f"/vol{vol}/part{part}/{nm}/images/{{folder}}/1.{{ext}}",
        f"/vol{vol}/{nm}/images/{{folder}}/1.{{ext}}",  # редкий путь без part
    )

    # корзины 01..35; начнём "с ближней" чтобы быстрее попасть
    start = (n % 20) + 1
    for i in list(range(start, 36)) + list(range(1, start)):
        host = f"https://basket-{i:02d}.wbbasket.ru"
        for tmpl in templates:
            for folder in folders:
                for ext in exts:
                    probe = host + tmpl.format(folder=folder, ext=ext)
                    if _head_ok(probe):
                        return (probe.rsplit("/", 1)[0], ext)
    return None


def _images_from_html(html: str) -> List[str]:
    """
    Резервный источник: достаём ссылки на фото прямо со страницы.
    Подойдут big, c516x688 и c246x328. Возвращаем уникальный упорядоченный список.
    Если попались миниатюры c246x328 — пробуем заменить сегмент пути на 'big'
    (на сервере эти файлы, как правило, существуют).
    """
    if not html:
        return []

    # 1) соберём все ссылки на кадры 1..N из любых размеров
    found = re.findall(
        r"https://basket-\d{2}\.wbbasket\.ru/vol\d+/(?:part\d+/)?\d+/images/(?:big|c516x688|c246x328)/(\d+)\.(?:webp|jpg)",
        html,
    )
    if not found:
        return []

    # 2) вытащим БАЗУ (без номера и расширения) из первого матча любого размера
    m = re.search(
        r"(https://basket-\d{2}\.wbbasket\.ru/vol\d+/(?:part\d+/)?\d+/images/)(?:big|c516x688|c246x328)/1\.(webp|jpg)",
        html,
    )
    base_prefix, ext = (m.group(1), m.group(2)) if m else (None, "webp")

    # 3) построим последовательность кадров 1..max, предпочитая 'big'
    #    (Telegram отлично ест webp/jpg; оставим исходное расширение)
    idxs = sorted({int(x) for x in found})
    images: List[str] = []
    for i in idxs:
        if base_prefix:
            images.append(f"{base_prefix}big/{i}.{ext}")
        else:
            # если не удалось выделить базу — достанем прямые ссылки (включая миниатюры)
            pass

    # 4) если база не распознана, вытащим прямые URL всех размеров и уберём дубли
    if not images:
        raw_urls = re.findall(
            r"https://basket-\d{2}\.wbbasket\.ru/vol\d+/(?:part\d+/)?\d+/images/(?:big|c516x688|c246x328)/\d+\.(?:webp|jpg)",
            html,
        )
        for u in raw_urls:
            if u not in images:
                images.append(u)

    # ограничимся первыми 10 (боту всё равно надо 4)
    return images[:10]


def _build_images(nm: str, prod: Dict[str, Any]) -> List[str]:
    """
    1) Берём базу из basket-XX (одной проверкой), после этого просто строим 1..N
       без HEAD на каждый кадр — так быстрее и WB не режет по HEAD.
    2) Фоллбек: вытянуть прямые ссылки из HTML (теперь видим и c246x328).
    3) Последний шанс — legacy CDN images.wbstatic.net.
    """
    # сколько кадров?
    count = 0
    if isinstance(prod, dict):
        cnt = prod.get("pics") or prod.get("imagesCount")
        try:
            count = int(cnt)
        except Exception:
            count = 0
    if count <= 0:
        # попробуем оценить по HTML (поиск последних индексов)
        html = getattr(settings, "_last_html", "") or ""
        m = re.findall(r"/images/(?:big|c516x688|c246x328)/(\d+)\.(?:webp|jpg)", html)
        if m:
            try:
                count = max(int(x) for x in m)
            except Exception:
                count = 0
    if count <= 0:
        count = 8  # разумная «крыша»

    base = _pick_image_base(nm)
    if base:
        base_url, ext = base
        return [f"{base_url}/{i}.{ext}" for i in range(1, count + 1)]

    # 2) со страницы (теперь умеем видеть и миниатюры)
    html_imgs = _images_from_html(getattr(settings, "_last_html", "") or "")
    if html_imgs:
        return html_imgs

    # 3) старый путь на images.wbstatic.net
    try:
        vol = int(nm) // 100000 * 100000
    except Exception:
        vol = 0
    return [f"https://images.wbstatic.net/big/new/{vol}/{nm}-{i}.jpg" for i in range(1, min(count, 10) + 1)]


def _price_from(prod: Dict[str, Any]) -> Optional[int]:
    for k in ("salePriceU", "priceU", "salePrice", "price"):
        v = prod.get(k)
        if isinstance(v, (int, float)):
            return int(round(float(v) / 100))
    sizes = prod.get("sizes")
    if isinstance(sizes, list) and sizes:
        pr = sizes[0].get("price") or {}
        for k in ("total", "final", "basic", "discount"):
            v = pr.get(k)
            if isinstance(v, (int, float)):
                return int(round(float(v) / 100))
    return None


def _meta_description(html: str) -> Optional[str]:
    m = re.search(r'<meta\s+name=["\']description["\']\s+content=["\'](.+?)["\']', html or "", re.I)
    return m.group(1).strip() if m else None

def _looks_like_site_meta(text: Optional[str]) -> bool:
    if not text:
        return False
    s = text.strip().lower()
    # типичный текст из мета-тегов WB (см. твою страницу)
    return "коллекции женской, мужской и детской одежды" in s and "информация о доставке" in s

def parse_wb(url: str) -> Dict[str, Any]:
    r = run_get_page_data(url, settings, site="wb") or {}
    html = r.get("html", "") or ""
    # запишем html в settings для резервного чтения картинок (без проброса больших структур)
    try:
        settings._last_html = html  # type: ignore[attr-defined]
    except Exception:
        pass

    title = description = rating = None
    reviews = None
    price: Optional[int] = None
    images: List[str] = []
    videos: List[str] = []

    # 1) JSON-LD
    ld = parse_ld_list(html, r.get("ld_scripts") or [])
    product = first_product(ld)
    if product:
        t, d, rat, rev, imgs = product_fields(product)
        title = title or t
        description = description or d
        rating = rating or rat
        reviews = reviews or rev
        images = normalize_urls(images + imgs)

    nm = _nm_from(url, html)
    log.info("WB nm detection: %s (src=url/html)", nm or "-")

    # 2) WB API (для цены, названия, количества фоток)
    prod = _best_product(nm) if nm else None
    if prod:
        title = title or prod.get("name")
        description = description or prod.get("description")
        if not rating:
            rtt = prod.get("rating") or prod.get("reviewRating") or prod.get("stars")
            if rtt is not None:
                try:
                    rating = f"{float(rtt):.1f}".rstrip("0").rstrip(".")
                except Exception:
                    rating = str(rtt)
        reviews = reviews or prod.get("feedbacks") or prod.get("feedbacksCount")
        price = price or _price_from(prod)
        if not images:
            images = _build_images(nm, prod)

    # 3) мета-описание как запасной вариант
    if not description:
        description = _meta_description(html)
    # НЕ подставляем общий meta WB вместо описания товара
    if _looks_like_site_meta(description):
        description = None

    # 4) если картинок всё ещё нет — попробуем вытащить хотя бы из текущего HTML напрямую
    if not images:
        images = _images_from_html(html)

    return {
        "title": title or "Товар",
        "description": description,
        "rating": rating,
        "reviews": reviews,
        "price": price,
        "images": images,
        "videos": videos,
    }
