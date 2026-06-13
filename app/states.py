from aiogram.fsm.state import State, StatesGroup


class TopupStates(StatesGroup):
    crypto_amount = State()
    card_amount = State()
    card_screenshot = State()


class PromoStates(StatesGroup):
    code = State()


class SettingStates(StatesGroup):
    value = State()


class CategoryStates(StatesGroup):
    title = State()
    edit_title = State()


class ProductStates(StatesGroup):
    title = State()
    price = State()
    description = State()
    photo = State()
    view_url = State()


class ProductEditStates(StatesGroup):
    value = State()


class UserBalanceStates(StatesGroup):
    amount = State()


class BroadcastStates(StatesGroup):
    photo = State()
    text = State()
    button_text = State()
    button_url = State()


class InfoButtonStates(StatesGroup):
    text = State()
    url = State()
    edit_text = State()
    edit_url = State()


class SubscriptionStates(StatesGroup):
    channel_id = State()


class PromoAdminStates(StatesGroup):
    code = State()
    amount = State()
    max_uses = State()
