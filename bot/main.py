# bot/main.py
from __future__ import annotations
import logging, re
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import (
    Message, FSInputFile, InputMediaPhoto,
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
)
from .config import settings
from .utils.logging import setup_logging
from .parsers.ozon import parse_ozon
from .parsers.wb import parse_wb
from .media.downloader import download_many_async
from .post.template import make_post
from .state.cache import STORE

setup_logging()
log = logging.getLogger("bot.main")

URL_RE = re.compile(r"https?://\S+", re.I)
def is_ozon(u): return "ozon.ru" in u
def is_wb(u): return "wildberries.ru" in u or "wb.ru" in u

async def handle_url(url: str, m: Message):
    data = parse_ozon(url) if is_ozon(url) else parse_wb(url) if is_wb(url) else None
    if not data:
        await m.answer("Кинь ссылку на Ozon или Wildberries 😉"); return

    title = data.get("title") or "Товар"
    imgs = (data.get("images") or [])[:4]  # <= 4 фото
    vids = data.get("videos") or []
    rating = data.get("rating")
    reviews = data.get("reviews")
    descr = data.get("description")
    price = data.get("price")
    source = data.get("source")
    log.info("Parsed: title=%r, images=%d, videos=%d, rating=%r, reviews=%r, price=%r",
             title, len(imgs), len(vids), rating, reviews, price)

    caption = make_post(
        title, url,
        description=descr, rating=rating, reviews=reviews, price=price,
        source=source or ("ozon" if is_ozon(url) else "wb" if is_wb(url) else "")
    )

    files = await download_many_async(imgs, out_dir="downloads", prefix="media", limit=4, concurrency=4, referer=url)

    sent_msgs = []
    if files:
        media = [InputMediaPhoto(media=FSInputFile(files[0]), caption=caption, parse_mode=ParseMode.HTML)]
        for p in files[1:4]:
            media.append(InputMediaPhoto(media=FSInputFile(p)))
        sent_msgs = await m.answer_media_group(media=media)
    else:
        sent_msgs = [await m.answer(caption, parse_mode=ParseMode.HTML)]

    # Кнопка «Опубликовать в группу»
    media_refs = []
    for msg in sent_msgs:
        if msg.photo:
            media_refs.append({"type": "photo", "file_id": msg.photo[-1].file_id})
    payload = {"caption": caption, "media": media_refs}
    token = STORE.put(payload)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🚀 Опубликовать в группу", callback_data=f"pub:{token}")
    ]])
    await m.answer("Готово к публикации. Нажми кнопку ниже:", reply_markup=kb)

async def on_message(m: Message):
    urls = URL_RE.findall(m.text or "")
    for url in urls:
        log.info("Handle URL: %s", url)
        await handle_url(url, m)

async def on_publish(call: CallbackQuery):
    try:
        token = (call.data or "").split("pub:", 1)[1]
    except Exception:
        await call.answer("Некорректная кнопка", show_alert=True); return
    data = STORE.get(token)
    if not data:
        await call.answer("Данные не найдены или устарели", show_alert=True); return

    channel = (settings.channel_username or "").strip()
    if not channel:
        await call.answer("Укажи CHANNEL_USERNAME в .env", show_alert=True); return

    caption = data.get("caption") or ""
    media = data.get("media") or []

    try:
        if media:
            ims = []
            for i, item in enumerate(media):
                if item["type"] == "photo":
                    if i == 0:
                        ims.append(InputMediaPhoto(media=item["file_id"], caption=caption, parse_mode=ParseMode.HTML))
                    else:
                        ims.append(InputMediaPhoto(media=item["file_id"]))
            await call.bot.send_media_group(chat_id=channel, media=ims)
        else:
            await call.bot.send_message(chat_id=channel, text=caption, parse_mode=ParseMode.HTML)
    except Exception as e:
        await call.answer(f"Не получилось опубликовать: {e}", show_alert=True); return

    await call.answer("Опубликовано ✅", show_alert=False)

def main():
    log.info("Bot is running… SHOW_BROWSER=%s", settings.show_browser)
    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.message.register(on_message, F.text.regexp(URL_RE.pattern))
    dp.callback_query.register(on_publish, F.data.startswith("pub:"))
    dp.run_polling(bot)

if __name__ == "__main__":
    main()
