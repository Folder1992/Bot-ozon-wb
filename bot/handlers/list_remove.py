
from aiogram import Router, types, F
from aiogram.filters import Command
from ..db import list_tracks, remove_track
from ..keyboards import remove_kb
from ..utils import fmt_price

router = Router()

@router.message(Command("list"))
async def list_cmd(m: types.Message):
    tracks = await list_tracks(m.from_user.id)
    if not tracks:
        await m.answer("У вас пока нет отслеживаний. Нажмите /add, чтобы добавить.")
        return
    lines = ["Ваши отслеживания:"]
    for t in tracks:
        lines.append(f"#{t.id} • {t.title} — цель {fmt_price(t.target_price_cents, t.currency)} — последняя цена: {fmt_price(t.last_price_cents, t.currency if t.mode=='steam' else 'USD')}")
    await m.answer("\n".join(lines))

    # bonus: кнопки удаления (по одному сообщению на позицию, чтобы не перегружать)
    for t in tracks:
        await m.answer(f"#{t.id} • {t.title}", reply_markup=remove_kb(t.id))

@router.callback_query(F.data.startswith("rm:"))
async def rm_track(cq: types.CallbackQuery):
    tid = int(cq.data.split(":")[1])
    ok = await remove_track(cq.from_user.id, tid)
    await cq.answer("Удалено" if ok else "Не найдено")
    await cq.message.edit_text(f"#{tid} — удалено" if ok else f"#{tid} — не найдено/чужое")
