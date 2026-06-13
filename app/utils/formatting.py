from __future__ import annotations

import html
import random
import re
import string
from datetime import datetime
from typing import Any

from aiogram.types import Message

from app.keyboards.premium import tg


def html_from_message(message: Message) -> str:
    formatted = getattr(message, "html_text", None) or getattr(message, "caption_html", None)
    if formatted:
        return formatted
    value = message.text or message.caption or ""
    return html.escape(value)


def plain_from_message(message: Message) -> str:
    return message.text or message.caption or ""


def strip_html(value: str) -> str:
    return re.sub(r"<[^>]+>", "", value).strip()


def money(value: float | int | str) -> str:
    amount = float(value)
    if amount.is_integer():
        return f"{int(amount)}"
    return f"{amount:.2f}".rstrip("0").rstrip(".")


def parse_amount(value: str) -> float | None:
    normalized = value.strip().replace(",", ".").replace(" ", "")
    try:
        amount = float(normalized)
    except ValueError:
        return None
    if amount <= 0:
        return None
    return round(amount, 2)


def parse_rub_rate(value: str) -> float:
    cleaned = value.strip().replace(" ", "").replace(",", ".")
    if "." in cleaned and cleaned.count(".") > 1:
        cleaned = cleaned.replace(".", "")
    amount = float(cleaned)
    if amount <= 0:
        raise ValueError("Rate must be positive.")
    return amount


def user_link(telegram_id: int, name: str | None = None) -> str:
    label = html.escape(name or str(telegram_id))
    return f'<a href="tg://user?id={telegram_id}">{label}</a>'


def order_code() -> str:
    alphabet = string.ascii_letters + string.digits
    return "#" + "".join(random.choice(alphabet) for _ in range(8))


def product_card(category: Any, product: Any) -> str:
    created = str(product["created_at"]).split("T", maxsplit=1)[0]
    return (
        f"{tg('📝')} <b>Информация о проекте</b> ⌵\n\n"
        f"┠Категория: {category['title_html']}\n"
        f"┠Товар: {product['title_html']}\n"
        f"┠Цена: ${money(product['price'])}\n"
        f"┖Дата публикации: {html.escape(created)}\n\n"
        f"{tg('❓')} <b>Описание:</b>\n"
        f"<blockquote>{product['description_html']}</blockquote>"
    )


def profile_text(base_text: str, user: Any) -> str:
    username = f"@{html.escape(user['username'])}" if user["username"] else "нет"
    return (
        f"{base_text}\n\n"
        f"<b>ID:</b> <code>{user['telegram_id']}</code>\n"
        f"<b>Username:</b> {username}\n"
        f"<b>Баланс:</b> ${money(user['balance'])}"
    )


def purchase_user_text(product_title: str, amount: float, code: str, owner_username: str) -> str:
    owner = f"@{owner_username.lstrip('@')}" if owner_username else "администратору"
    return (
        "<b>Вы купили данный товар</b>\n\n"
        f"<b>Название товара:</b> {html.escape(product_title)}\n"
        f"<b>Время покупки:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
        f"<b>Сумма:</b> ${money(amount)}\n\n"
        f"<code>{html.escape(code)}</code>\n\n"
        f"Перешлите данное сообщение {html.escape(owner)}, чтобы вам выдали товар."
    )
