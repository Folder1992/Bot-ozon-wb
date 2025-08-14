
from aiogram import Router, types
from aiogram.filters import CommandStart, Command
from ..db import add_user

router = Router()

WELCOME = (
    "Привет! Я слежу за ценами на игры и напомню, когда цена опустится до вашей цели.\n\n"
    "Команды:\n"
    "/add — добавить отслеживание\n"
    "/list — список ваших отслеживаний\n"
    "/help — подсказка\n\n"
    "Поддерживается Steam (RUB) и мульти‑магазины через CheapShark (USD)."
)

@router.message(CommandStart())
async def start(m: types.Message):
    await add_user(m.from_user.id)
    await m.answer(WELCOME)

@router.message(Command("help"))
async def help_cmd(m: types.Message):
    await m.answer(WELCOME)
