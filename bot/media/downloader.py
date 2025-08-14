# bot/media/downloader.py
from __future__ import annotations

import asyncio
import hashlib
import logging
import mimetypes
import os
import pathlib
from typing import Iterable, List, Optional

import httpx

log = logging.getLogger(__name__)

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

def _ext_from_response(url: str, content_type: Optional[str]) -> str:
    if content_type:
        ct = content_type.split(";", 1)[0].strip().lower()
        ext = mimetypes.guess_extension(ct)
        if ext:
            return ext
    for e in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        if url.lower().endswith(e):
            return e
    return ".jpg"

async def download_many_async(
    urls: Iterable[str],
    out_dir: str = "downloads",
    prefix: str = "media",
    limit: int = 10,
    concurrency: int = 4,
    referer: Optional[str] = None,
) -> List[str]:
    """Асинхронная загрузка изображений с сохранением исходного порядка."""
    urls = [u for u in (urls or []) if isinstance(u, str) and u.strip()]
    if not urls:
        return []
    # дедуп + ограничение, но порядок сохраняем
    seen = set(); ordered = []
    for u in urls:
        if u not in seen:
            seen.add(u); ordered.append(u)
        if len(ordered) >= limit:
            break

    pathlib.Path(out_dir).mkdir(parents=True, exist_ok=True)
    headers = {
        "User-Agent": UA,
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "Accept-Language": "ru,en;q=0.9",
    }
    if referer:
        headers["Referer"] = referer

    results: List[Optional[str]] = [None] * len(ordered)
    sem = asyncio.Semaphore(concurrency)

    async with httpx.AsyncClient(timeout=25, follow_redirects=True, headers=headers) as c:
        async def fetch(idx: int, url: str):
            async with sem:
                try:
                    r = await c.get(url)
                    if r.status_code != 200:
                        return
                    ct = r.headers.get("content-type", "").lower()
                    if "image" not in ct and not any(url.lower().endswith(e) for e in (".jpg",".jpeg",".png",".webp",".gif")):
                        return
                    ext = _ext_from_response(url, ct)
                    h = hashlib.md5(url.encode("utf-8")).hexdigest()[:8]
                    path = os.path.join(out_dir, f"{prefix}_{idx+1:02d}_{h}{ext}")
                    with open(path, "wb") as f:
                        f.write(r.content)
                    results[idx] = path
                except Exception as e:
                    log.debug("download fail %s: %s", url, e)

        await asyncio.gather(*(fetch(i, u) for i, u in enumerate(ordered)))

    return [p for p in results if p]

def download_many(urls: Iterable[str], out_dir="downloads", prefix="media") -> List[str]:
    return asyncio.get_event_loop().run_until_complete(
        download_many_async(urls, out_dir=out_dir, prefix=prefix)
    )
