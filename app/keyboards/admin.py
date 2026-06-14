from __future__ import annotations

from collections.abc import Iterable
from math import ceil
from typing import Any

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.keyboards.premium import button as premium_button, emoji_id, split_button_icon
from app.utils.formatting import money


def _row_value(row: Any, key: str, default: Any = None) -> Any:
    try:
        return row[key]
    except (KeyError, IndexError, TypeError):
        return default


SETTINGS_LABELS = {
    "owner_username": "Username владельца",
    "logs_chat_id": "Чат логов",
}

TEXT_LABELS = {
    "main_text": "Главное меню",
    "profile_text": "Профиль",
    "info_text": "Текст инфы",
    "faq_text": "FAQ",
    "topup_text": "Пополнение: выбор способа",
    "crypto_amount_text": "CryptoBot: ввод суммы",
    "crypto_invoice_text": "CryptoBot: счет",
    "card_amount_text": "Карта: ввод суммы",
    "card_pending_text": "Карта: заявка проверяется",
}

PAYMENT_LABELS = {
    "bank_card": "Карта",
    "bank_holder": "ФИО карты",
    "bank_name": "Банк",
    "rub_rate": "Курс RUB за $1",
}

ALL_SETTING_LABELS = {
    "banner_url": "Баннер",
    **SETTINGS_LABELS,
    **TEXT_LABELS,
    **PAYMENT_LABELS,
}


def admin_main() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    premium_button(kb, "🎨", "Оформление", callback_data="a:appearance")
    premium_button(kb, "💳", "Платежи", callback_data="a:payments")
    premium_button(kb, "⚙️", "Настройки", callback_data="a:settings")
    premium_button(kb, "🛒", "Каталог", callback_data="a:catalog")
    premium_button(kb, "👥", "Пользователи", callback_data="a:users:0")
    premium_button(kb, "📊", "Статистика", callback_data="a:stats")
    premium_button(kb, "📣", "Рассылка", callback_data="a:bc")
    premium_button(kb, "🔐", "Обязательные подписки", callback_data="a:subs")
    premium_button(kb, "🎁", "Промокоды", callback_data="a:promo")
    premium_button(kb, "🏠", "В магазин", callback_data="u:main")
    kb.adjust(3, 2, 2, 1, 1, 1)
    return kb.as_markup()


def settings_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for key, label in SETTINGS_LABELS.items():
        kb.button(text=label, callback_data=f"a:set:{key}")
    premium_button(kb, "⬅️", "Назад", callback_data="a:main")
    kb.adjust(1)
    return kb.as_markup()


def appearance_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    premium_button(kb, "🖼", "Баннер", callback_data="a:set:banner_url")
    premium_button(kb, "ℹ️", "Информация", callback_data="a:info:buttons")
    for key, label in TEXT_LABELS.items():
        kb.button(text=label, callback_data=f"a:set:{key}")
    premium_button(kb, "⬅️", "Назад", callback_data="a:main")
    kb.adjust(1)
    return kb.as_markup()


def info_buttons_menu(buttons: Iterable[Any]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    premium_button(kb, "➕", "Добавить кнопку", callback_data="a:info:btn:add")
    for item in buttons:
        kwargs = {
            "text": str(item["text"]),
            "callback_data": f"a:info:btn:{item['id']}",
        }
        icon_id = _row_value(item, "icon_custom_emoji_id")
        if icon_id:
            kwargs["icon_custom_emoji_id"] = icon_id
        kb.button(**kwargs)
    premium_button(kb, "⬅️", "Назад", callback_data="a:appearance")
    kb.adjust(1)
    return kb.as_markup()


def info_button_edit_menu(button: Any) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    button_id = int(button["id"])
    premium_button(kb, "✏️", "Текст", callback_data=f"a:info:edit:{button_id}:text")
    premium_button(kb, "🔗", "Ссылка", callback_data=f"a:info:edit:{button_id}:url")
    premium_button(kb, "🎨", "Стиль", callback_data=f"a:info:style:{button_id}")
    premium_button(kb, "⬅️", "Влево", callback_data=f"a:info:move:{button_id}:left")
    premium_button(kb, "➡️", "Вправо", callback_data=f"a:info:move:{button_id}:right")
    premium_button(kb, "🗑", "Удалить", callback_data=f"a:info:del:{button_id}")
    premium_button(kb, "⬅️", "К кнопкам", callback_data="a:info:buttons")
    kb.adjust(2, 1, 2, 1, 1)
    return kb.as_markup()


def info_button_style_menu(button_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Default", callback_data=f"a:info:style:{button_id}:default")
    kb.button(text="Primary", callback_data=f"a:info:style:{button_id}:primary")
    kb.button(text="Success", callback_data=f"a:info:style:{button_id}:success")
    kb.button(text="Danger", callback_data=f"a:info:style:{button_id}:danger")
    premium_button(kb, "⬅️", "Назад", callback_data=f"a:info:btn:{button_id}")
    kb.adjust(2, 2, 1)
    return kb.as_markup()


def payments_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for key, label in PAYMENT_LABELS.items():
        kb.button(text=label, callback_data=f"a:set:{key}")
    premium_button(kb, "⬅️", "Назад", callback_data="a:main")
    kb.adjust(1)
    return kb.as_markup()


def catalog_menu(categories: Iterable[Any]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    premium_button(kb, "➕", "Добавить категорию", callback_data="a:cat:add")
    for category in categories:
        text, icon = split_button_icon(str(category["title_text"]))
        stored_icon = _row_value(category, "icon_custom_emoji_id")
        kwargs = {"callback_data": f"a:cat:{category['id']}", "text": text}
        if stored_icon or icon:
            kwargs["icon_custom_emoji_id"] = stored_icon or icon
        kb.button(**kwargs)
    premium_button(kb, "⬅️", "Назад", callback_data="a:main")
    kb.adjust(1)
    return kb.as_markup()


def category_menu(category: Any, products: Iterable[Any]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    premium_button(kb, "➕", "Добавить товар", callback_data=f"a:prod:add:{category['id']}")
    premium_button(kb, "✏️", "Переименовать категорию", callback_data=f"a:cat:edit:{category['id']}")
    premium_button(kb, "🗑", "Удалить категорию", callback_data=f"a:cat:del:{category['id']}")
    for product in products:
        status = "" if int(product["is_active"]) else " [выкл]"
        title_text, icon = split_button_icon(str(product['title_text']))
        stored_icon = _row_value(product, "icon_custom_emoji_id")
        text = f"{title_text} - ${money(product['price'])}{status}"
        kwargs = {"text": text, "callback_data": f"a:prod:{product['id']}"}
        if stored_icon or icon:
            kwargs["icon_custom_emoji_id"] = stored_icon or icon
        kb.button(**kwargs)
    premium_button(kb, "⬅️", "Назад", callback_data="a:catalog")
    kb.adjust(1)
    return kb.as_markup()


def product_admin_menu(product: Any) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    premium_button(kb, "✏️", "Название", callback_data=f"a:pe:{product['id']}:title")
    premium_button(kb, "💵", "Цена", callback_data=f"a:pe:{product['id']}:price")
    premium_button(kb, "📝", "Описание", callback_data=f"a:pe:{product['id']}:desc")
    premium_button(kb, "🖼", "Фото", callback_data=f"a:pe:{product['id']}:photo")
    premium_button(kb, "🔗", "Ссылка подробнее", callback_data=f"a:pe:{product['id']}:view")
    toggle = "Выключить" if int(product["is_active"]) else "Включить"
    premium_button(kb, "🔁", toggle, callback_data=f"a:prod:toggle:{product['id']}")
    premium_button(kb, "🗑", "Удалить", callback_data=f"a:prod:del:{product['id']}")
    premium_button(kb, "⬅️", "Назад", callback_data=f"a:cat:{product['category_id']}")
    kb.adjust(1)
    return kb.as_markup()


def users_menu(users: Iterable[Any], page: int, total: int, per_page: int = 6) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for user in users:
        username = f"@{user['username']}" if user["username"] else str(user["telegram_id"])
        kwargs = {"icon_custom_emoji_id": emoji_id("🚫")} if int(user["is_blocked"]) else {}
        kb.button(text=f"{username} | ${money(user['balance'])}", callback_data=f"a:u:{user['id']}", **kwargs)
    pages = max(1, ceil(total / per_page))
    if page > 0:
        premium_button(kb, "⬅️", "Назад", callback_data=f"a:users:{page - 1}")
    if page + 1 < pages:
        premium_button(kb, "➡️", "Вперед", callback_data=f"a:users:{page + 1}")
    premium_button(kb, "⬅️", "Назад", callback_data="a:main")
    kb.adjust(1)
    return kb.as_markup()


def user_admin_menu(user: Any) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    premium_button(kb, "➕", "Выдать баланс", callback_data=f"a:ub:add:{user['id']}")
    premium_button(kb, "➖", "Отнять баланс", callback_data=f"a:ub:sub:{user['id']}")
    premium_button(kb, "✏️", "Установить баланс", callback_data=f"a:ub:set:{user['id']}")
    action = "Разблокировать" if int(user["is_blocked"]) else "Заблокировать"
    premium_button(kb, "🚫", action, callback_data=f"a:u:block:{user['id']}")
    premium_button(kb, "⬅️", "К пользователям", callback_data="a:users:0")
    kb.adjust(1)
    return kb.as_markup()


def topup_decision(topup_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    premium_button(kb, "✅", "Пополнить", callback_data=f"a:top:ok:{topup_id}")
    premium_button(kb, "❌", "Отклонить", callback_data=f"a:top:no:{topup_id}")
    kb.adjust(2)
    return kb.as_markup()


def broadcast_start() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    premium_button(kb, "🖼", "Фото", callback_data="a:bc:photo")
    premium_button(kb, "📝", "Текст", callback_data="a:bc:text")
    premium_button(kb, "🔗", "Inline кнопки", callback_data="a:bc:buttons")
    premium_button(kb, "👁", "Предпросмотр", callback_data="a:bc:preview")
    premium_button(kb, "✅", "Отправить", callback_data="a:bc:send")
    premium_button(kb, "⬅️", "Назад", callback_data="a:main")
    kb.adjust(3, 2, 1)
    return kb.as_markup()


def broadcast_photo_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    premium_button(kb, "🖼", "Загрузить фото", callback_data="a:bc:photo:set")
    premium_button(kb, "🚫", "Без фото", callback_data="a:bc:photo:clear")
    premium_button(kb, "⬅️", "Назад", callback_data="a:bc")
    kb.adjust(1)
    return kb.as_markup()


def broadcast_buttons_menu(buttons: Iterable[dict[str, str]]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    premium_button(kb, "➕", "Добавить кнопку", callback_data="a:bc:btn:add")
    if buttons:
        premium_button(kb, "🧹", "Очистить кнопки", callback_data="a:bc:btn:clear")
    premium_button(kb, "⬅️", "Назад", callback_data="a:bc")
    kb.adjust(1)
    return kb.as_markup()


def broadcast_button_style_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Default", callback_data="a:bc:style:default")
    kb.button(text="Primary", callback_data="a:bc:style:primary")
    kb.button(text="Success", callback_data="a:bc:style:success")
    kb.button(text="Danger", callback_data="a:bc:style:danger")
    kb.adjust(2)
    return kb.as_markup()


def broadcast_confirm() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    premium_button(kb, "✅", "Отправить", callback_data="a:bc:send")
    premium_button(kb, "❌", "Отмена", callback_data="a:bc:cancel")
    kb.adjust(2)
    return kb.as_markup()


def subscriptions_menu(channels: Iterable[Any]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    premium_button(kb, "➕", "Добавить канал", callback_data="a:sub:add")
    for channel in channels:
        premium_button(kb, "🗑", str(channel["title"]), callback_data=f"a:sub:del:{channel['id']}")
    premium_button(kb, "⬅️", "Назад", callback_data="a:main")
    kb.adjust(1)
    return kb.as_markup()


def promo_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    premium_button(kb, "➕", "Добавить промокод", callback_data="a:promo:add")
    premium_button(kb, "⬅️", "Назад", callback_data="a:main")
    kb.adjust(1)
    return kb.as_markup()
