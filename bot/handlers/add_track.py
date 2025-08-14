
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from ..states import AddTrack
from ..keyboards import currency_kb, mode_kb
from ..utils import try_extract_steam_appid, to_cents, fmt_price
from ..db import add_track
from ..price_providers.steam import get_price_by_appid

router = Router()

@router.message(Command("add"))
async def add_cmd(m: types.Message, state: FSMContext):
    await state.clear()
    await m.answer("Вставьте ссылку на игру в Steam (или введите название игры для поиска по магазинам):")
    await state.set_state(AddTrack.waiting_item)

@router.message(AddTrack.waiting_item, F.text.len() > 0)
async def got_item(m: types.Message, state: FSMContext):
    text = m.text.strip()
    appid = try_extract_steam_appid(text)
    ctx = {"title": None, "url": None, "steam_appid": None}
    if appid:
        # try fetch name to show friendly confirmation
        price, currency, name = await get_price_by_appid(appid, cc="ru", lang="russian")
        ctx["title"] = name or f"Steam app {appid}"
        ctx["url"] = text
        ctx["steam_appid"] = appid
        await state.update_data(**ctx)
    else:
        # treat as title for multi-store
        ctx["title"] = text
        ctx["url"] = None
        ctx["steam_appid"] = None
        await state.update_data(**ctx)
    await m.answer("Укажите желаемую цену (число, например 2499 или 29.99):")
    await state.set_state(AddTrack.waiting_price)

@router.message(AddTrack.waiting_price, F.text.len() > 0)
async def got_price(m: types.Message, state: FSMContext):
    amount = m.text.strip()
    data = await state.get_data()
    # default currency hint: RUB if steam_appid present else USD
    await state.update_data(target_amount=amount)
    await m.answer("Выберите валюту:", reply_markup=currency_kb())
    await state.set_state(AddTrack.waiting_currency)

@router.callback_query(AddTrack.waiting_currency, F.data.startswith("cur:"))
async def chose_currency(cq: types.CallbackQuery, state: FSMContext):
    await cq.answer()
    cur = cq.data.split(":")[1]
    await state.update_data(currency=cur)
    await cq.message.answer("Режим отслеживания:", reply_markup=mode_kb())
    await state.set_state(AddTrack.waiting_mode)

@router.callback_query(AddTrack.waiting_mode, F.data.startswith("mode:"))
async def chose_mode(cq: types.CallbackQuery, state: FSMContext):
    await cq.answer()
    mode = cq.data.split(":")[1]  # steam | any
    data = await state.get_data()
    title = data.get("title")
    url = data.get("url")
    steam_appid = data.get("steam_appid")
    currency = data.get("currency")
    target_amount = data.get("target_amount")
    try:
        target_cents = to_cents(target_amount, currency)
    except Exception:
        await cq.message.answer("Не смог разобрать число. Начните заново: /add")
        await state.clear()
        return

    # guard: if mode=steam but нет appid — откажем и предложим any
    if mode == "steam" and not steam_appid:
        await cq.message.answer("Для режима «Steam‑только» нужна ссылка на Steam. Повторите /add или выберите «Любой магазин».")
        await state.clear()
        return

    # persist
    track_id = await add_track(
        cq.from_user.id,
        title=title,
        url=url,
        mode=mode,
        currency=currency,
        target_price_cents=target_cents,
        steam_appid=steam_appid,
    )
    await state.clear()
    await cq.message.answer(f"Готово! Добавлено отслеживание #{track_id}: {title} — цель {target_amount} {currency} ({'Steam' if mode=='steam' else 'мульти‑магазины'}).")
