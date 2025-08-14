
import asyncio
from aiogram import Bot
from .db import get_all_tracks, update_track_price, mark_notified
from .price_providers.steam import get_price_by_appid
from .price_providers.cheapshark import best_price_by_title

async def check_prices(bot: Bot):
    tracks = await get_all_tracks()
    for t in tracks:
        try:
            price_cents = None
            currency = t.currency
            link = t.url
            title = t.title

            if t.mode == "steam" and t.steam_appid:
                price_cents, curr, name = await get_price_by_appid(t.steam_appid, cc="ru", lang="russian")
                if name:
                    title = name
                if curr:
                    currency = curr
                if link is None:
                    link = f"https://store.steampowered.com/app/{t.steam_appid}/"
            else:
                # any-store via CheapShark in USD
                price_cents, curr, gtitle, deal_url = await best_price_by_title(t.title)
                if gtitle:
                    title = gtitle
                if deal_url:
                    link = deal_url
                currency = "USD"

            await update_track_price(t.id, price_cents)

            if price_cents is None:
                await asyncio.sleep(0.1)
                continue

            # notify if reached
            if price_cents <= t.target_price_cents and (t.last_notified_price_cents is None or price_cents < (t.last_notified_price_cents or 1e18)):
                text = (f"🔔 <b>{title}</b> сейчас {price_cents/100:.2f} {currency} "
                        f"(ваша цель {t.target_price_cents/100:.2f} {t.currency}).")
                if link:
                    text += f"\nСсылка: {link}"
                try:
                    await bot.send_message(t.user_id, text, parse_mode='HTML', disable_web_page_preview=False)
                except Exception:
                    pass
                await mark_notified(t.id, price_cents)

            await asyncio.sleep(0.2)  # soft throttle
        except Exception as e:
            # swallow errors per track
            await asyncio.sleep(0.1)
            continue
