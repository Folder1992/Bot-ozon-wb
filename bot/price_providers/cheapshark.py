
import httpx
from typing import Optional

API_BASE = "https://www.cheapshark.com/api/1.0"

async def search_games(title: str) -> list[dict]:
    params = {"title": title, "limit": 5, "exact": 0}
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(f"{API_BASE}/games", params=params)
        r.raise_for_status()
        return r.json() or []

async def game_lookup(game_id: str) -> dict | None:
    params = {"id": game_id}
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(f"{API_BASE}/games", params=params)
        r.raise_for_status()
        data = r.json()
        return data or None

async def best_price_by_title(title: str) -> tuple[Optional[int], Optional[str], Optional[str], Optional[str]]:
    """Return (price_cents, currency, title, deal_url) in USD."""
    results = await search_games(title)
    if not results:
        return None, None, None, None
    # pick the first match
    game = results[0]
    gid = game.get("gameID")
    gtitle = game.get("external")
    if not gid:
        return None, None, gtitle, None
    info = await game_lookup(gid)
    if not info:
        return None, None, gtitle, None
    deals = (info.get("deals") or [])
    if not deals:
        return None, None, gtitle, None
    # choose minimal salePrice
    best = min(deals, key=lambda d: float(d.get("salePrice", "1e9")))
    price = int(round(float(best.get("salePrice")) * 100))
    # construct deal link to respect CheapShark policy
    deal_id = best.get("dealID")
    deal_url = f"https://www.cheapshark.com/redirect?dealID={deal_id}" if deal_id else None
    return price, "USD", gtitle, deal_url
