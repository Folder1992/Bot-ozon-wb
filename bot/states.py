
from aiogram.fsm.state import StatesGroup, State

class AddTrack(StatesGroup):
    waiting_item = State()
    waiting_price = State()
    waiting_currency = State()
    waiting_mode = State()
