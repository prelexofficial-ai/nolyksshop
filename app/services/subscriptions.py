from __future__ import annotations

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import ChatMember

from app.database import Database


ALLOWED_STATUSES = {"creator", "administrator", "member"}


async def missing_subscriptions(bot: Bot, db: Database, user_id: int) -> list[dict[str, str]]:
    missing: list[dict[str, str]] = []
    channels = await db.list_subscriptions(active_only=True)
    for channel in channels:
        try:
            member: ChatMember = await bot.get_chat_member(channel["channel_id"], user_id)
            if member.status in ALLOWED_STATUSES:
                continue
        except (TelegramBadRequest, TelegramForbiddenError):
            pass
        missing.append(
            {
                "id": str(channel["id"]),
                "title": str(channel["title"]),
                "url": str(channel["invite_url"] or ""),
            }
        )
    return missing
