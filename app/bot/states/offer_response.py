from aiogram.fsm.state import State
from aiogram.fsm.state import StatesGroup


class OfferResponseStates(StatesGroup):
    price = State()
    included_services = State()
    possible_surcharges = State()
    service_window = State()
    estimate_status = State()
