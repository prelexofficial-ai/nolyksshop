from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any

import aiosqlite

from app.keyboards.premium import tg


DEFAULT_SETTINGS = {
    "banner_url": "",
    "main_text": f"{tg('🏠')} <b>Главное меню</b>\n\nВыберите нужный раздел ниже.",
    "profile_text": f"{tg('👤')} <b>Профиль</b>\n\nВаши данные и баланс.",
    "info_text": f"{tg('ℹ️')} <b>Информация</b>\n\n<blockquote>Добавьте описание проекта через админ-панель.</blockquote>",
    "faq_text": f"{tg('❓')} <b>FAQ</b>\n\n<blockquote>Ответы на вопросы появятся здесь.</blockquote>",
    "topup_text": f"{tg('💳')} <b>Пополнение баланса</b>\n\nВыберите удобный способ пополнения.",
    "crypto_amount_text": f"{tg('👛')} <b>CryptoBot</b>\n\nВведите сумму пополнения в долларах.\nМинимум: <b>$1</b>.",
    "crypto_invoice_text": f"{tg('💸')} <b>Счет создан</b>\n\nОплатите счет, затем нажмите кнопку проверки оплаты.",
    "card_amount_text": f"{tg('💳')} <b>Банковская карта</b>\n\nВведите сумму пополнения в долларах.\nМинимум: <b>$1</b>.",
    "card_pending_text": f"{tg('✅')} <b>Заявка отправлена</b>\n\nПроверим перевод в течение часа.",
    "bank_card": "",
    "bank_holder": "-",
    "bank_name": "-",
    "rub_rate": "100",
    "owner_username": "",
    "logs_chat_id": "",
}

LEGACY_DEFAULT_SETTINGS = {
    "main_text": "Добро пожаловать в магазин.",
    "profile_text": "Ваш профиль и баланс.",
    "info_text": "Информация о проекте скоро появится.",
    "faq_text": "FAQ скоро появится.",
    "topup_text": f"{tg('💳')} <b>Пополнение баланса</b>\n\nВыберите способ пополнения.",
    "crypto_amount_text": "Введите сумму пополнения в долларах. Минимум $1.",
    "crypto_invoice_text": "Оплатите счет, затем нажмите кнопку проверки оплаты.",
    "card_amount_text": "Введите сумму пополнения в долларах. Минимум $1.",
    "card_pending_text": f"{tg('✅')} Ваша заявка будет проверена в течение часа.",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class Database:
    def __init__(self, path: str) -> None:
        self.path = path
        self.conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.execute("PRAGMA foreign_keys = ON")
        await self.conn.commit()

    async def close(self) -> None:
        if self.conn is not None:
            await self.conn.close()

    def _db(self) -> aiosqlite.Connection:
        if self.conn is None:
            raise RuntimeError("Database is not connected.")
        return self.conn

    async def migrate(self) -> None:
        db = self._db()
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL UNIQUE,
                username TEXT,
                full_name TEXT,
                balance REAL NOT NULL DEFAULT 0,
                is_blocked INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title_text TEXT NOT NULL,
                title_html TEXT NOT NULL,
                icon_custom_emoji_id TEXT,
                position INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
                title_text TEXT NOT NULL,
                title_html TEXT NOT NULL,
                icon_custom_emoji_id TEXT,
                price REAL NOT NULL,
                description_html TEXT NOT NULL,
                photo_id TEXT,
                view_url TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS topups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                method TEXT NOT NULL,
                amount_usd REAL NOT NULL,
                amount_rub REAL,
                status TEXT NOT NULL DEFAULT 'pending',
                screenshot_file_id TEXT,
                provider_invoice_id TEXT,
                pay_url TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
                product_title TEXT NOT NULL,
                amount REAL NOT NULL,
                code TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS promo_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                amount REAL NOT NULL,
                max_uses INTEGER NOT NULL DEFAULT 1,
                used_count INTEGER NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS promo_uses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                promo_id INTEGER NOT NULL REFERENCES promo_codes(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL,
                UNIQUE(promo_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                invite_url TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS info_buttons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                url TEXT NOT NULL,
                icon_custom_emoji_id TEXT,
                style TEXT NOT NULL DEFAULT 'default',
                position INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            """
        )
        for key, value in DEFAULT_SETTINGS.items():
            await db.execute(
                "INSERT OR IGNORE INTO settings(key, value) VALUES(?, ?)",
                (key, value),
            )
        for key, legacy_value in LEGACY_DEFAULT_SETTINGS.items():
            row = await db.execute("SELECT value FROM settings WHERE key = ?", (key,))
            setting = await row.fetchone()
            await row.close()
            if setting is not None and str(setting["value"]) == legacy_value:
                await db.execute("UPDATE settings SET value = ? WHERE key = ?", (DEFAULT_SETTINGS[key], key))
        await db.commit()
        # Ensure legacy databases get the new icon_custom_emoji_id column
        try:
            cur = await db.execute("PRAGMA table_info('categories')")
            cols = await cur.fetchall()
            await cur.close()
            if not any(str(c[1]) == "icon_custom_emoji_id" for c in cols):
                await db.execute("ALTER TABLE categories ADD COLUMN icon_custom_emoji_id TEXT")
                await db.commit()
            cur = await db.execute("PRAGMA table_info('products')")
            cols = await cur.fetchall()
            await cur.close()
            if not any(str(c[1]) == "icon_custom_emoji_id" for c in cols):
                await db.execute("ALTER TABLE products ADD COLUMN icon_custom_emoji_id TEXT")
                await db.commit()
        except Exception:
            # Best-effort migration; ignore if not possible
            pass

    async def fetchone(self, query: str, params: Iterable[Any] = ()) -> aiosqlite.Row | None:
        cur = await self._db().execute(query, tuple(params))
        row = await cur.fetchone()
        await cur.close()
        return row

    async def fetchall(self, query: str, params: Iterable[Any] = ()) -> list[aiosqlite.Row]:
        cur = await self._db().execute(query, tuple(params))
        rows = await cur.fetchall()
        await cur.close()
        return list(rows)

    async def execute(self, query: str, params: Iterable[Any] = ()) -> int:
        cur = await self._db().execute(query, tuple(params))
        await self._db().commit()
        row_id = cur.lastrowid
        await cur.close()
        return int(row_id or 0)

    async def executescript(self, query: str) -> None:
        await self._db().executescript(query)
        await self._db().commit()

    async def get_setting(self, key: str, default: str = "") -> str:
        row = await self.fetchone("SELECT value FROM settings WHERE key = ?", (key,))
        return str(row["value"]) if row else default

    async def set_setting(self, key: str, value: str) -> None:
        await self.execute(
            """
            INSERT INTO settings(key, value) VALUES(?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )

    async def get_settings(self) -> dict[str, str]:
        rows = await self.fetchall("SELECT key, value FROM settings")
        return {str(row["key"]): str(row["value"]) for row in rows}

    async def list_info_buttons(self) -> list[aiosqlite.Row]:
        return await self.fetchall("SELECT * FROM info_buttons ORDER BY position ASC, id ASC")

    async def get_info_button(self, button_id: int) -> aiosqlite.Row | None:
        return await self.fetchone("SELECT * FROM info_buttons WHERE id = ?", (button_id,))

    async def create_info_button(
        self,
        text: str,
        url: str,
        icon_custom_emoji_id: str | None = None,
        style: str = "default",
    ) -> int:
        row = await self.fetchone("SELECT COALESCE(MAX(position), 0) + 1 AS position FROM info_buttons")
        position = int(row["position"] if row else 1)
        return await self.execute(
            """
            INSERT INTO info_buttons(text, url, icon_custom_emoji_id, style, position, created_at)
            VALUES(?, ?, ?, ?, ?, ?)
            """,
            (text, url, icon_custom_emoji_id, style, position, now_iso()),
        )

    async def update_info_button_field(self, button_id: int, field: str, value: Any) -> None:
        allowed = {"text", "url", "icon_custom_emoji_id", "style", "position"}
        if field not in allowed:
            raise ValueError(f"Field {field!r} is not editable.")
        await self.execute(f"UPDATE info_buttons SET {field} = ? WHERE id = ?", (value, button_id))

    async def delete_info_button(self, button_id: int) -> None:
        await self.execute("DELETE FROM info_buttons WHERE id = ?", (button_id,))
        await self.normalize_info_button_positions()

    async def normalize_info_button_positions(self) -> None:
        buttons = await self.list_info_buttons()
        for position, button in enumerate(buttons, start=1):
            if int(button["position"]) != position:
                await self.execute("UPDATE info_buttons SET position = ? WHERE id = ?", (position, button["id"]))

    async def move_info_button(self, button_id: int, direction: str) -> None:
        buttons = await self.list_info_buttons()
        index = next((idx for idx, button in enumerate(buttons) if int(button["id"]) == button_id), None)
        if index is None:
            return
        target_index = index - 1 if direction == "left" else index + 1
        if target_index < 0 or target_index >= len(buttons):
            return
        ordered = list(buttons)
        ordered[index], ordered[target_index] = ordered[target_index], ordered[index]
        for position, button in enumerate(ordered, start=1):
            await self.execute("UPDATE info_buttons SET position = ? WHERE id = ?", (position, button["id"]))

    async def upsert_user(self, telegram_id: int, username: str | None, full_name: str) -> tuple[aiosqlite.Row, bool]:
        row = await self.fetchone("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        stamp = now_iso()
        if row is None:
            user_id = await self.execute(
                """
                INSERT INTO users(telegram_id, username, full_name, created_at, updated_at)
                VALUES(?, ?, ?, ?, ?)
                """,
                (telegram_id, username, full_name, stamp, stamp),
            )
            created = await self.fetchone("SELECT * FROM users WHERE id = ?", (user_id,))
            if created is None:
                raise RuntimeError("Failed to create user.")
            return created, True

        await self.execute(
            """
            UPDATE users
            SET username = ?, full_name = ?, updated_at = ?
            WHERE telegram_id = ?
            """,
            (username, full_name, stamp, telegram_id),
        )
        updated = await self.fetchone("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        if updated is None:
            raise RuntimeError("Failed to update user.")
        return updated, False

    async def get_user_by_telegram(self, telegram_id: int) -> aiosqlite.Row | None:
        return await self.fetchone("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))

    async def get_user(self, user_id: int) -> aiosqlite.Row | None:
        return await self.fetchone("SELECT * FROM users WHERE id = ?", (user_id,))

    async def count_users(self) -> int:
        row = await self.fetchone("SELECT COUNT(*) AS count FROM users")
        return int(row["count"] if row else 0)

    async def list_users(self, limit: int = 6, offset: int = 0) -> list[aiosqlite.Row]:
        return await self.fetchall(
            "SELECT * FROM users ORDER BY id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )

    async def add_balance(self, user_id: int, amount: float) -> None:
        await self.execute(
            "UPDATE users SET balance = MAX(balance + ?, 0), updated_at = ? WHERE id = ?",
            (amount, now_iso(), user_id),
        )

    async def set_balance(self, user_id: int, amount: float) -> None:
        await self.execute(
            "UPDATE users SET balance = MAX(?, 0), updated_at = ? WHERE id = ?",
            (amount, now_iso(), user_id),
        )

    async def set_user_blocked(self, user_id: int, blocked: bool) -> None:
        await self.execute(
            "UPDATE users SET is_blocked = ?, updated_at = ? WHERE id = ?",
            (1 if blocked else 0, now_iso(), user_id),
        )

    async def list_categories(self) -> list[aiosqlite.Row]:
        return await self.fetchall("SELECT * FROM categories ORDER BY position ASC, id ASC")

    async def create_category(self, title_text: str, title_html: str, icon_custom_emoji_id: str | None = None) -> int:
        row = await self.fetchone("SELECT COALESCE(MAX(position), 0) + 1 AS position FROM categories")
        position = int(row["position"] if row else 1)
        return await self.execute(
            "INSERT INTO categories(title_text, title_html, icon_custom_emoji_id, position, created_at) VALUES(?, ?, ?, ?, ?)",
            (title_text, title_html, icon_custom_emoji_id, position, now_iso()),
        )

    async def get_category(self, category_id: int) -> aiosqlite.Row | None:
        return await self.fetchone("SELECT * FROM categories WHERE id = ?", (category_id,))

    async def update_category(self, category_id: int, title_text: str, title_html: str, icon_custom_emoji_id: str | None = None) -> None:
        await self.execute(
            "UPDATE categories SET title_text = ?, title_html = ?, icon_custom_emoji_id = ? WHERE id = ?",
            (title_text, title_html, icon_custom_emoji_id, category_id),
        )

    async def delete_category(self, category_id: int) -> None:
        await self.execute("DELETE FROM categories WHERE id = ?", (category_id,))

    async def list_products(self, category_id: int) -> list[aiosqlite.Row]:
        return await self.fetchall(
            "SELECT * FROM products WHERE category_id = ? AND is_active = 1 ORDER BY id DESC",
            (category_id,),
        )

    async def list_admin_products(self, category_id: int) -> list[aiosqlite.Row]:
        return await self.fetchall(
            "SELECT * FROM products WHERE category_id = ? ORDER BY id DESC",
            (category_id,),
        )

    async def create_product(
        self,
        category_id: int,
        title_text: str,
        title_html: str,
        icon_custom_emoji_id: str | None,
        price: float,
        description_html: str,
        photo_id: str | None,
        view_url: str | None,
    ) -> int:
        return await self.execute(
            """
            INSERT INTO products(category_id, title_text, title_html, icon_custom_emoji_id, price, description_html, photo_id, view_url, created_at)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                category_id,
                title_text,
                title_html,
                icon_custom_emoji_id,
                price,
                description_html,
                photo_id,
                view_url,
                now_iso(),
            ),
        )

    async def get_product(self, product_id: int) -> aiosqlite.Row | None:
        return await self.fetchone("SELECT * FROM products WHERE id = ?", (product_id,))

    async def update_product_field(self, product_id: int, field: str, value: Any) -> None:
        allowed = {
            "title_text",
            "title_html",
            "icon_custom_emoji_id",
            "price",
            "description_html",
            "photo_id",
            "view_url",
            "is_active",
        }
        if field not in allowed:
            raise ValueError(f"Field {field!r} is not editable.")
        await self.execute(f"UPDATE products SET {field} = ? WHERE id = ?", (value, product_id))

    async def delete_product(self, product_id: int) -> None:
        await self.execute("DELETE FROM products WHERE id = ?", (product_id,))

    async def create_topup(
        self,
        user_id: int,
        method: str,
        amount_usd: float,
        amount_rub: float | None = None,
        provider_invoice_id: str | None = None,
        pay_url: str | None = None,
    ) -> int:
        stamp = now_iso()
        return await self.execute(
            """
            INSERT INTO topups(user_id, method, amount_usd, amount_rub, provider_invoice_id, pay_url, created_at, updated_at)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, method, amount_usd, amount_rub, provider_invoice_id, pay_url, stamp, stamp),
        )

    async def get_topup(self, topup_id: int) -> aiosqlite.Row | None:
        return await self.fetchone(
            """
            SELECT t.*, u.telegram_id, u.username, u.full_name
            FROM topups t
            JOIN users u ON u.id = t.user_id
            WHERE t.id = ?
            """,
            (topup_id,),
        )

    async def set_topup_status(self, topup_id: int, status: str) -> None:
        await self.execute(
            "UPDATE topups SET status = ?, updated_at = ? WHERE id = ?",
            (status, now_iso(), topup_id),
        )

    async def set_topup_screenshot(self, topup_id: int, screenshot_file_id: str) -> None:
        await self.execute(
            "UPDATE topups SET screenshot_file_id = ?, updated_at = ? WHERE id = ?",
            (screenshot_file_id, now_iso(), topup_id),
        )

    async def create_purchase(self, user_id: int, product_id: int, product_title: str, amount: float, code: str) -> int:
        return await self.execute(
            """
            INSERT INTO purchases(user_id, product_id, product_title, amount, code, created_at)
            VALUES(?, ?, ?, ?, ?, ?)
            """,
            (user_id, product_id, product_title, amount, code, now_iso()),
        )

    async def list_user_purchases(self, user_id: int, limit: int = 10) -> list[aiosqlite.Row]:
        return await self.fetchall(
            "SELECT * FROM purchases WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        )

    async def get_promo(self, code: str) -> aiosqlite.Row | None:
        return await self.fetchone(
            "SELECT * FROM promo_codes WHERE LOWER(code) = LOWER(?) AND is_active = 1",
            (code,),
        )

    async def create_promo(self, code: str, amount: float, max_uses: int) -> int:
        return await self.execute(
            "INSERT INTO promo_codes(code, amount, max_uses, created_at) VALUES(?, ?, ?, ?)",
            (code, amount, max_uses, now_iso()),
        )

    async def use_promo(self, promo_id: int, user_id: int) -> bool:
        db = self._db()
        promo = await self.fetchone("SELECT * FROM promo_codes WHERE id = ?", (promo_id,))
        if promo is None or int(promo["used_count"]) >= int(promo["max_uses"]):
            return False
        used = await self.fetchone(
            "SELECT id FROM promo_uses WHERE promo_id = ? AND user_id = ?",
            (promo_id, user_id),
        )
        if used is not None:
            return False
        await db.execute("BEGIN")
        try:
            await db.execute(
                "INSERT INTO promo_uses(promo_id, user_id, created_at) VALUES(?, ?, ?)",
                (promo_id, user_id, now_iso()),
            )
            await db.execute(
                "UPDATE promo_codes SET used_count = used_count + 1 WHERE id = ?",
                (promo_id,),
            )
            await db.execute(
                "UPDATE users SET balance = balance + ?, updated_at = ? WHERE id = ?",
                (float(promo["amount"]), now_iso(), user_id),
            )
            await db.commit()
            return True
        except Exception:
            await db.rollback()
            raise

    async def list_subscriptions(self, active_only: bool = True) -> list[aiosqlite.Row]:
        if active_only:
            return await self.fetchall("SELECT * FROM subscriptions WHERE is_active = 1 ORDER BY id DESC")
        return await self.fetchall("SELECT * FROM subscriptions ORDER BY id DESC")

    async def add_subscription(self, channel_id: str, title: str, invite_url: str | None) -> int:
        return await self.execute(
            """
            INSERT INTO subscriptions(channel_id, title, invite_url, created_at)
            VALUES(?, ?, ?, ?)
            ON CONFLICT(channel_id) DO UPDATE SET title = excluded.title, invite_url = excluded.invite_url, is_active = 1
            """,
            (channel_id, title, invite_url, now_iso()),
        )

    async def delete_subscription(self, subscription_id: int) -> None:
        await self.execute("DELETE FROM subscriptions WHERE id = ?", (subscription_id,))

    async def stats(self) -> dict[str, Any]:
        users = await self.fetchone("SELECT COUNT(*) AS count FROM users")
        sales = await self.fetchone("SELECT COUNT(*) AS count, COALESCE(SUM(amount), 0) AS total FROM purchases")
        topups = await self.fetchone(
            "SELECT COUNT(*) AS count, COALESCE(SUM(amount_usd), 0) AS total FROM topups WHERE status = 'paid'"
        )
        products = await self.fetchone("SELECT COUNT(*) AS count FROM products")
        categories = await self.fetchone("SELECT COUNT(*) AS count FROM categories")
        return {
            "users": int(users["count"] if users else 0),
            "sales_count": int(sales["count"] if sales else 0),
            "sales_total": float(sales["total"] if sales else 0),
            "topups_count": int(topups["count"] if topups else 0),
            "topups_total": float(topups["total"] if topups else 0),
            "products": int(products["count"] if products else 0),
            "categories": int(categories["count"] if categories else 0),
        }

    @staticmethod
    def dumps(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False)

    @staticmethod
    def loads(value: str, default: Any = None) -> Any:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default
