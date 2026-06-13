from __future__ import annotations

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup

from app.database import Database
from app.keyboards.premium import premiumize_html


async def send_log(
    bot: Bot,
    db: Database,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    photo: str | None = None,
) -> None:
    chat_id = (await db.get_setting("logs_chat_id")).strip()
    if not chat_id:
        return
    text = premiumize_html(text)
    try:
        if photo:
            await bot.send_photo(chat_id=chat_id, photo=photo, caption=text, reply_markup=reply_markup)
        else:
            await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
    except Exception:
        return
