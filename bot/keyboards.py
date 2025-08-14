
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def currency_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="RUB", callback_data="cur:RUB")
    kb.button(text="USD", callback_data="cur:USD")
    kb.adjust(2)
    return kb.as_markup()

def mode_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Steam‑только", callback_data="mode:steam")
    kb.button(text="Любой магазин", callback_data="mode:any")
    kb.adjust(2)
    return kb.as_markup()

def remove_kb(track_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Удалить", callback_data=f"rm:{track_id}")
    return kb.as_markup()
