
from dataclasses import dataclass
from typing import Optional, Literal

Mode = Literal["steam", "any"]
Currency = Literal["RUB", "USD"]

@dataclass
class Track:
    id: int
    user_id: int
    title: str
    url: str | None
    mode: Mode
    currency: Currency
    target_price_cents: int
    steam_appid: int | None = None
    last_price_cents: int | None = None
    last_notified_price_cents: int | None = None
