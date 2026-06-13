from __future__ import annotations

from aiogram.filters import Filter
from aiogram.types import CallbackQuery, Message

from app.config import Config


class IsAdmin(Filter):
    async def __call__(self, event: Message | CallbackQuery, config: Config) -> bool:
        return bool(event.from_user and event.from_user.id in config.owner_ids)
