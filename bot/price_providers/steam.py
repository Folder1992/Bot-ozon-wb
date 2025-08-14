
import httpx
from typing import Optional

STEAM_APPDETAILS_URL = "https://store.steampowered.com/api/appdetails"

async def get_appdetails(appid: int, cc: str = "ru", lang: str = "russian") -> dict | None:
    params = {
        "appids": str(appid),
        "filters": "price_overview,name",
        "cc": cc,
        "l": lang,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(STEAM_APPDETAILS_URL, params=params)
        r.raise_for_status()
        data = r.json()
        item = data.get(str(appid))
        if not item or not item.get("success"):
            return None
        return item.get("data") or {}

async def get_price_by_appid(appid: int, cc: str = "ru", lang: str = "russian") -> tuple[Optional[int], Optional[str], Optional[str]]:
    """Return (price_cents, currency, name) for given appid."""
    data = await get_appdetails(appid, cc=cc, lang=lang)
    if not data:
        return None, None, None
    name = data.get("name")
    pov = data.get("price_overview") or {}
    final = pov.get("final")
    currency = pov.get("currency")
    if final is None or currency is None:
        return None, None, name
    return int(final), currency, name
