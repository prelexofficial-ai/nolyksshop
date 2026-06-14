from __future__ import annotations

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InputMediaPhoto, Message

from app.database import Database
from app.keyboards.premium import premiumize_html


Target = Message | CallbackQuery


async def answer_screen(
    target: Target,
    db: Database,
    text: str,
    reply_markup=None,
    photo: str | None = None,
) -> Message | None:
    message = target.message if isinstance(target, CallbackQuery) else target
    if message is None:
        return None

    text = premiumize_html(text)
    banner = photo or (await db.get_setting("banner_url")).strip()

    async def send_text_replacement() -> Message | None:
        try:
            sent = await message.answer(text, reply_markup=reply_markup)
        except TelegramBadRequest:
            return None
        try:
            await message.delete()
        except TelegramBadRequest:
            pass
        return sent

    if isinstance(target, CallbackQuery):
        if banner:
            if len(text) > 1024:
                return await send_text_replacement()
            try:
                updated = await message.edit_media(
                    media=InputMediaPhoto(media=banner, caption=text),
                    reply_markup=reply_markup,
                )
                return updated if isinstance(updated, Message) else message
            except TelegramBadRequest:
                if getattr(message, "photo", None):
                    try:
                        updated = await message.edit_caption(caption=text, reply_markup=reply_markup)
                        return updated if isinstance(updated, Message) else message
                    except TelegramBadRequest:
                        pass
                try:
                    sent = await message.answer_photo(photo=banner, caption=text, reply_markup=reply_markup)
                    try:
                        await message.delete()
                    except TelegramBadRequest:
                        pass
                    return sent
                except TelegramBadRequest:
                    pass
        try:
            updated = await message.edit_text(text, reply_markup=reply_markup)
            return updated if isinstance(updated, Message) else message
        except TelegramBadRequest:
            try:
                updated = await message.edit_caption(caption=text, reply_markup=reply_markup)
                return updated if isinstance(updated, Message) else message
            except TelegramBadRequest:
                return await send_text_replacement()

    if banner:
        if len(text) > 1024:
            return await message.answer(text, reply_markup=reply_markup)
        try:
            return await message.answer_photo(photo=banner, caption=text, reply_markup=reply_markup)
        except TelegramBadRequest:
            pass
    return await message.answer(text, reply_markup=reply_markup)
