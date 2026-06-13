from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(slots=True)
class Config:
    bot_token: str
    owner_ids: set[int]
    database_path: str
    crypto_pay_token: str | None
    crypto_pay_api_url: str


def _parse_owner_ids(value: str) -> set[int]:
    owner_ids: set[int] = set()
    for item in value.replace(";", ",").split(","):
        item = item.strip()
        if not item:
            continue
        owner_ids.add(int(item))
    return owner_ids


def load_config() -> Config:
    env_path = Path(".env")
    if env_path.exists():
        load_dotenv(env_path)

    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token:
        raise RuntimeError("BOT_TOKEN is empty. Fill .env before running the bot.")

    owner_ids = _parse_owner_ids(os.getenv("OWNER_IDS", ""))
    if not owner_ids:
        raise RuntimeError("OWNER_IDS is empty. Add at least one Telegram user id.")

    return Config(
        bot_token=bot_token,
        owner_ids=owner_ids,
        database_path=os.getenv("DATABASE_PATH", "shop.sqlite3").strip() or "shop.sqlite3",
        crypto_pay_token=os.getenv("CRYPTO_PAY_TOKEN", "").strip() or None,
        crypto_pay_api_url=os.getenv("CRYPTO_PAY_API_URL", "https://pay.crypt.bot/api").strip(),
    )
