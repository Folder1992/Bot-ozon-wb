
import re
from typing import Optional

STEAM_APP_RE = re.compile(r"(?:store\.steampowered\.com/app/)(\d+)")

def try_extract_steam_appid(text: str) -> Optional[int]:
    m = STEAM_APP_RE.search(text)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return None
    return None

def to_cents(amount_str: str, currency: str) -> int:
    # supports "2499" or "2499.99"
    norm = amount_str.strip().replace(",", ".")
    value = float(norm)
    return int(round(value * 100))

def fmt_price(cents: int | None, currency: str) -> str:
    if cents is None:
        return "—"
    return f"{cents/100:.2f} {currency}"
