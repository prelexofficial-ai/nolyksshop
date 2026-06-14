from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.keyboards.premium import button as premium_button, split_button_icon, url_button_kwargs
from app.utils.formatting import money


def _row_value(row: Any, key: str, default: Any = None) -> Any:
    try:
        return row[key]
    except (KeyError, IndexError, TypeError):
        return default


def main_menu(is_admin: bool = False) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    premium_button(kb, "👤", "Профиль", callback_data="u:profile")
    premium_button(kb, "🛒", "Каталог", callback_data="u:catalog")
    premium_button(kb, "ℹ️", "Инфа", callback_data="u:info")
    premium_button(kb, "❓", "FAQ", callback_data="u:faq")
    if is_admin:
        premium_button(kb, "⚙️", "Админ-панель", callback_data="a:main")
    kb.adjust(2, 2, 1)
    return kb.as_markup()


def back_main() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    premium_button(kb, "⬅️", "Назад", callback_data="u:main")
    return kb.as_markup()


def profile_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    premium_button(kb, "💳", "Пополнить баланс", callback_data="u:topup")
    premium_button(kb, "📈", "Отслеживание цен", callback_data="u:watch")
    premium_button(kb, "🎁", "Активировать промокод", callback_data="u:promo")
    premium_button(kb, "🧾", "История покупок", callback_data="u:history")
    premium_button(kb, "⬅️", "Назад", callback_data="u:main")
    kb.adjust(1)
    return kb.as_markup()


def topup_methods(owner_username: str | None) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    premium_button(kb, "💳", "Банковская карта", callback_data="u:topup:card")
    premium_button(kb, "👛", "CryptoBot", callback_data="u:topup:crypto")
    if owner_username:
        username = owner_username.lstrip("@")
        premium_button(kb, "👑", "Пополнить через владельца", url=f"https://t.me/{username}")
    premium_button(kb, "⬅️", "Назад", callback_data="u:profile")
    kb.adjust(1)
    return kb.as_markup()


def categories_menu(categories: Iterable[Any]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for category in categories:
        text, icon = split_button_icon(str(category["title_text"]))
        stored_icon = _row_value(category, "icon_custom_emoji_id")
        kwargs = {"text": text, "callback_data": f"u:cat:{category['id']}"}
        if stored_icon or icon:
            kwargs["icon_custom_emoji_id"] = stored_icon or icon
        kb.button(**kwargs)
    premium_button(kb, "⬅️", "Назад", callback_data="u:main")
    kb.adjust(1)
    return kb.as_markup()


def products_menu(products: Iterable[Any], category_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for product in products:
        title_text, icon = split_button_icon(str(product["title_text"]))
        stored_icon = _row_value(product, "icon_custom_emoji_id")
        kwargs = {
            "text": f"{title_text} - ${money(product['price'])}",
            "callback_data": f"u:prod:{product['id']}",
        }
        if stored_icon or icon:
            kwargs["icon_custom_emoji_id"] = stored_icon or icon
        kb.button(**kwargs)
    premium_button(kb, "⬅️", "Назад", callback_data="u:catalog")
    kb.adjust(1)
    return kb.as_markup()


def info_menu(buttons: Iterable[Any]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for item in buttons:
        kb.button(
            **url_button_kwargs(
                text=str(item["text"]),
                url=str(item["url"]),
                style=str(_row_value(item, "style", "default") or "default"),
                icon_custom_emoji_id=_row_value(item, "icon_custom_emoji_id"),
            )
        )
    premium_button(kb, "⬅️", "Назад", callback_data="u:main")
    kb.adjust(1)
    return kb.as_markup()


def product_menu(product: Any, category_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    premium_button(kb, "🛒", "Купить", callback_data=f"u:buy:{product['id']}")
    if product["view_url"]:
        premium_button(kb, "🔎", "Подробнее", url=str(product["view_url"]))
    premium_button(kb, "⬅️", "Назад", callback_data=f"u:cat:{category_id}")
    kb.adjust(1)
    return kb.as_markup()


def invoice_menu(pay_url: str, topup_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    premium_button(kb, "💸", "Оплатить", url=pay_url)
    premium_button(kb, "✅", "Проверить оплату", callback_data=f"u:topup:check:{topup_id}")
    premium_button(kb, "⬅️", "Назад", callback_data="u:topup")
    kb.adjust(1)
    return kb.as_markup()


def subscription_menu(channels: list[dict[str, str]]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for channel in channels:
        if channel["url"]:
            kb.button(text=f"Подписаться: {channel['title']}", url=channel["url"])
    premium_button(kb, "✅", "Проверить подписку", callback_data="u:sub:check")
    kb.adjust(1)
    return kb.as_markup()


def owner_button(owner_username: str | None) -> InlineKeyboardMarkup | None:
    if not owner_username:
        return None
    kb = InlineKeyboardBuilder()
    kb.button(text="Написать владельцу", url=f"https://t.me/{owner_username.lstrip('@')}")
    return kb.as_markup()
