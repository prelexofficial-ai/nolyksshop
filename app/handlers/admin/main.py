from __future__ import annotations

import html
from typing import Any

from aiogram import Bot, F, Router
from aiogram.enums import ButtonStyle
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.database import Database
from app.filters import IsAdmin
from app.keyboards.premium import emoji_id, premiumize_html, tg, first_custom_emoji_id, split_button_icon
from app.keyboards.admin import (
    ALL_SETTING_LABELS,
    PAYMENT_LABELS,
    TEXT_LABELS,
    admin_main,
    appearance_menu,
    broadcast_button_style_menu,
    broadcast_buttons_menu,
    broadcast_photo_menu,
    broadcast_start,
    catalog_menu,
    category_menu,
    payments_menu,
    product_admin_menu,
    promo_menu,
    settings_menu,
    subscriptions_menu,
    user_admin_menu,
    users_menu,
)
from app.keyboards.user import owner_button
from app.services.logs import send_log
from app.services.screens import answer_screen
from app.states import (
    BroadcastStates,
    CategoryStates,
    ProductEditStates,
    ProductStates,
    PromoAdminStates,
    SettingStates,
    SubscriptionStates,
    UserBalanceStates,
)
from app.utils.formatting import (
    html_from_message,
    money,
    parse_amount,
    plain_from_message,
    product_card,
    user_link,
)

router = Router(name="admin")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


def _broadcast_markup(buttons: list[dict[str, str]]) -> InlineKeyboardMarkup | None:
    if not buttons:
        return None
    keyboard = [[_styled_url_button(button)] for button in buttons]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def _broadcast_preview_markup(buttons: list[dict[str, str]]) -> InlineKeyboardMarkup:
    keyboard = [[_styled_url_button(button)] for button in buttons]
    keyboard.append(
        [
            InlineKeyboardButton(
                text="Отправить",
                callback_data="a:bc:send",
                icon_custom_emoji_id=emoji_id("✅"),
            ),
            InlineKeyboardButton(
                text="Отмена",
                callback_data="a:bc:cancel",
                icon_custom_emoji_id=emoji_id("❌"),
            ),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


STYLE_MAP = {
    "danger": ButtonStyle.DANGER,
    "success": ButtonStyle.SUCCESS,
    "primary": ButtonStyle.PRIMARY,
}


def _styled_url_button(button: dict[str, str]) -> InlineKeyboardButton:
    style = STYLE_MAP.get(button.get("style", "default"))
    kwargs: dict[str, Any] = {"text": button["text"], "url": button["url"]}
    if style is not None:
        kwargs["style"] = style
    return InlineKeyboardButton(**kwargs)


def _broadcast_state_text(data: dict[str, Any]) -> str:
    photo = "есть" if data.get("photo_id") else "нет"
    text = "есть" if data.get("text") else "нет"
    buttons: list[dict[str, str]] = data.get("buttons") or []
    lines = [
        f"{tg('📣')} <b>Конструктор рассылки</b>",
        "",
        f"Фото: <b>{photo}</b>",
        f"Текст: <b>{text}</b>",
        f"Inline кнопок: <b>{len(buttons)}</b>",
    ]
    if buttons:
        lines.append("")
        for index, button in enumerate(buttons, start=1):
            style = button.get("style", "default")
            lines.append(f"{index}. {html.escape(button['text'])} · <code>{html.escape(style)}</code>")
    return "\n".join(lines)


def _setting_back_menu(key: str) -> InlineKeyboardMarkup:
    if key == "banner_url" or key in TEXT_LABELS:
        return appearance_menu()
    if key in PAYMENT_LABELS:
        return payments_menu()
    return settings_menu()


async def _remember_prompt(state: FSMContext, message: Message | None) -> None:
    if message is None:
        return
    await state.update_data(prompt_chat_id=message.chat.id, prompt_message_id=message.message_id)


async def _show_prompt(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    prompt = await answer_screen(callback, db, text, reply_markup)
    await _remember_prompt(state, prompt)


async def _delete_input(message: Message) -> None:
    try:
        await message.delete()
    except TelegramBadRequest:
        pass


async def _edit_prompt(
    bot: Bot,
    state: FSMContext,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> bool:
    text = premiumize_html(text)
    data = await state.get_data()
    chat_id = data.get("prompt_chat_id")
    message_id = data.get("prompt_message_id")
    if not chat_id or not message_id:
        return False
    try:
        await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup)
        return True
    except TelegramBadRequest:
        try:
            await bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption=text, reply_markup=reply_markup)
            return True
        except TelegramBadRequest:
            return False


async def _update_prompt_from_input(
    message: Message,
    state: FSMContext,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    clear_state: bool = False,
) -> None:
    await _delete_input(message)
    edited = await _edit_prompt(message.bot, state, text, reply_markup)
    if clear_state:
        await state.clear()
    if not edited:
        await message.answer(premiumize_html(text), reply_markup=reply_markup)


@router.message(Command("admin"))
async def admin_command(message: Message, db: Database) -> None:
    await answer_screen(message, db, f"{tg('⚙️')} <b>Админ-панель</b>", admin_main())
    await _delete_input(message)


@router.callback_query(F.data == "a:main")
async def admin_home(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    await state.clear()
    await callback.answer()
    await answer_screen(callback, db, f"{tg('⚙️')} <b>Админ-панель</b>", admin_main())


@router.callback_query(F.data == "a:settings")
async def settings(callback: CallbackQuery, db: Database) -> None:
    await callback.answer()
    await answer_screen(callback, db, f"{tg('⚙️')} <b>Настройки</b>\n\nВыберите параметр.", settings_menu())


@router.callback_query(F.data == "a:appearance")
@router.callback_query(F.data == "a:banner")
@router.callback_query(F.data == "a:texts")
async def appearance_settings(callback: CallbackQuery, db: Database) -> None:
    await callback.answer()
    current = await db.get_setting("banner_url")
    text = (
        f"{tg('🎨')} <b>Оформление</b>\n\n"
        "Здесь меняются общий баннер и все тексты меню/платежей.\n\n"
        f"Баннер сейчас: <code>{html.escape(current or '-')}</code>"
    )
    await answer_screen(callback, db, text, appearance_menu())


@router.callback_query(F.data == "a:payments")
async def payments_settings(callback: CallbackQuery, db: Database) -> None:
    await callback.answer()
    await answer_screen(callback, db, f"{tg('💳')} <b>Платежи</b>\n\nВыберите платежный параметр.", payments_menu())


@router.callback_query(F.data.startswith("a:set:"))
async def setting_edit(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    await callback.answer()
    key = callback.data.split(":", maxsplit=2)[-1]
    await state.set_state(SettingStates.value)
    await state.update_data(key=key)
    current = await db.get_setting(key)
    label = ALL_SETTING_LABELS.get(key, key)
    await _show_prompt(
        callback,
        state,
        db,
        f"Введите новое значение для <b>{html.escape(label)}</b>.\n\n"
        f"Сейчас: <code>{html.escape(current or '-')}</code>\n\n"
        "Для баннера вставьте прямую ссылку на картинку или отправьте фото.\n"
        "Для текстов можно отправлять форматированный текст Telegram.",
        _setting_back_menu(key),
    )


@router.message(SettingStates.value)
async def setting_save(message: Message, state: FSMContext, db: Database) -> None:
    data = await state.get_data()
    key = str(data["key"])
    menu = _setting_back_menu(key)
    if key == "banner_url":
        if message.photo:
            value = message.photo[-1].file_id
        else:
            value = plain_from_message(message).strip()
            if value == "-":
                value = ""
        if value and not message.photo and not (value.startswith("http://") or value.startswith("https://")):
            await _update_prompt_from_input(
                message,
                state,
                "Баннер должен быть прямой ссылкой http/https на фото. Чтобы очистить баннер, отправьте <code>-</code>.",
                menu,
            )
            return
        if value:
            sent: Message | None = None
            try:
                sent = await message.bot.send_photo(message.chat.id, value, caption=f"{tg('✅')} Баннер проверен.")
                await sent.delete()
            except Exception as exc:
                if sent is not None:
                    try:
                        await sent.delete()
                    except TelegramBadRequest:
                        pass
                await _update_prompt_from_input(
                    message,
                    state,
                    "Telegram не смог загрузить это фото. Проверьте, что это прямая ссылка на картинку, "
                    f"а не страница сайта.\n\n<code>{html.escape(str(exc))}</code>",
                    menu,
                )
                return
    elif key.endswith("_text"):
        value = html_from_message(message)
    else:
        value = plain_from_message(message).strip()
    await db.set_setting(key, value)
    await _update_prompt_from_input(message, state, f"{tg('✅')} Настройка сохранена.", menu, clear_state=True)


@router.callback_query(F.data == "a:catalog")
async def admin_catalog(callback: CallbackQuery, db: Database) -> None:
    await callback.answer()
    categories = await db.list_categories()
    await answer_screen(callback, db, f"{tg('🛒')} <b>Каталог</b>", catalog_menu(categories))


@router.callback_query(F.data == "a:cat:add")
async def category_add_start(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    await callback.answer()
    await state.set_state(CategoryStates.title)
    await _show_prompt(callback, state, db, "Введите название категории.", catalog_menu(await db.list_categories()))


@router.message(CategoryStates.title)
async def category_add_save(message: Message, state: FSMContext, db: Database) -> None:
    title_text = plain_from_message(message).strip()
    if not title_text:
        await _update_prompt_from_input(message, state, "Название не должно быть пустым.", catalog_menu(await db.list_categories()))
        return
    # try to extract custom emoji id from message entities (tg-emoji)
    custom_id = first_custom_emoji_id(message)
    # if no custom id, try to detect known premium symbol in text
    cleaned_title, mapped_icon = split_button_icon(title_text)
    title_text = cleaned_title
    icon_id = custom_id or mapped_icon
    await db.create_category(title_text, html_from_message(message), icon_id)
    await _update_prompt_from_input(
        message,
        state,
        f"{tg('✅')} Категория добавлена.",
        catalog_menu(await db.list_categories()),
        clear_state=True,
    )


@router.callback_query(F.data.regexp(r"^a:cat:\d+$"))
async def category_open(callback: CallbackQuery, db: Database) -> None:
    await callback.answer()
    category_id = int(callback.data.split(":")[-1])
    category = await db.get_category(category_id)
    if category is None:
        await answer_screen(callback, db, "Категория не найдена.", catalog_menu(await db.list_categories()))
        return
    products = await db.list_admin_products(category_id)
    await answer_screen(
        callback,
        db,
        f"{tg('🛒')} <b>{category['title_html']}</b>\n\nТоваров: {len(products)}",
        category_menu(category, products),
    )


@router.callback_query(F.data.startswith("a:cat:edit:"))
async def category_edit_start(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    await callback.answer()
    category_id = int(callback.data.split(":")[-1])
    await state.set_state(CategoryStates.edit_title)
    await state.update_data(category_id=category_id)
    category = await db.get_category(category_id)
    products = await db.list_admin_products(category_id)
    await _show_prompt(
        callback,
        state,
        db,
        "Введите новое название категории.",
        category_menu(category, products) if category else catalog_menu(await db.list_categories()),
    )


@router.message(CategoryStates.edit_title)
async def category_edit_save(message: Message, state: FSMContext, db: Database) -> None:
    data = await state.get_data()
    title_text = plain_from_message(message).strip()
    category_id = int(data["category_id"])
    category = await db.get_category(category_id)
    products = await db.list_admin_products(category_id)
    menu = category_menu(category, products) if category else catalog_menu(await db.list_categories())
    if not title_text:
        await _update_prompt_from_input(message, state, "Название не должно быть пустым.", menu)
        return
    custom_id = first_custom_emoji_id(message)
    cleaned_title, mapped_icon = split_button_icon(title_text)
    title_text = cleaned_title
    icon_id = custom_id or mapped_icon
    await db.update_category(category_id, title_text, html_from_message(message), icon_id)
    category = await db.get_category(category_id)
    products = await db.list_admin_products(category_id)
    await _update_prompt_from_input(
        message,
        state,
        f"{tg('✅')} Категория обновлена.",
        category_menu(category, products) if category else catalog_menu(await db.list_categories()),
        clear_state=True,
    )


@router.callback_query(F.data.startswith("a:cat:del:"))
async def category_delete(callback: CallbackQuery, db: Database) -> None:
    await callback.answer("Удалено")
    category_id = int(callback.data.split(":")[-1])
    await db.delete_category(category_id)
    await answer_screen(callback, db, f"{tg('🗑')} Категория удалена.", catalog_menu(await db.list_categories()))


@router.callback_query(F.data.startswith("a:prod:add:"))
async def product_add_start(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    await callback.answer()
    category_id = int(callback.data.split(":")[-1])
    await state.set_state(ProductStates.title)
    await state.update_data(category_id=category_id)
    category = await db.get_category(category_id)
    products = await db.list_admin_products(category_id)
    await _show_prompt(
        callback,
        state,
        db,
        "Введите название товара.",
        category_menu(category, products) if category else catalog_menu(await db.list_categories()),
    )


@router.message(ProductStates.title)
async def product_title(message: Message, state: FSMContext) -> None:
    title = plain_from_message(message).strip()
    if not title:
        await _update_prompt_from_input(message, state, "Название не должно быть пустым.")
        return
    await state.update_data(title_text=title, title_html=html_from_message(message))
    await state.set_state(ProductStates.price)
    await _update_prompt_from_input(message, state, "Введите цену товара в долларах.")


@router.message(ProductStates.price)
async def product_price(message: Message, state: FSMContext) -> None:
    amount = parse_amount(message.text or "")
    if amount is None:
        await _update_prompt_from_input(message, state, "Введите корректную цену.")
        return
    await state.update_data(price=amount)
    await state.set_state(ProductStates.description)
    await _update_prompt_from_input(message, state, "Введите описание товара. Форматирование Telegram сохранится.")


@router.message(ProductStates.description)
async def product_description(message: Message, state: FSMContext) -> None:
    await state.update_data(description_html=html_from_message(message))
    await state.set_state(ProductStates.photo)
    await _update_prompt_from_input(
        message,
        state,
        "Отправьте фото товара или ссылку на фото. Если фото не нужно, отправьте <code>-</code>.",
    )


@router.message(ProductStates.photo)
async def product_photo(message: Message, state: FSMContext) -> None:
    photo_id: str | None = None
    if message.photo:
        photo_id = message.photo[-1].file_id
    else:
        text = (message.text or "").strip()
        if text and text != "-":
            photo_id = text
    await state.update_data(photo_id=photo_id)
    await state.set_state(ProductStates.view_url)
    await _update_prompt_from_input(
        message,
        state,
        "Введите ссылку для кнопки «Подробнее». Если ссылка не нужна, отправьте <code>-</code>.",
    )


@router.message(ProductStates.view_url)
async def product_save(message: Message, state: FSMContext, db: Database) -> None:
    data = await state.get_data()
    view_url = (message.text or "").strip()
    if view_url == "-":
        view_url = ""
    product_id = await db.create_product(
        category_id=int(data["category_id"]),
        title_text=str(data["title_text"]),
        title_html=str(data["title_html"]),
        price=float(data["price"]),
        description_html=str(data["description_html"]),
        photo_id=data.get("photo_id"),
        view_url=view_url or None,
    )
    await state.clear()
    product = await db.get_product(product_id)
    category = await db.get_category(int(data["category_id"]))
    await _delete_input(message)
    if product and category:
        await answer_screen(message, db, product_card(category, product), product_admin_menu(product), photo=product["photo_id"])


@router.callback_query(F.data.regexp(r"^a:prod:\d+$"))
async def product_admin(callback: CallbackQuery, db: Database) -> None:
    await callback.answer()
    product_id = int(callback.data.split(":")[-1])
    product = await db.get_product(product_id)
    if product is None:
        await answer_screen(callback, db, "Товар не найден.", catalog_menu(await db.list_categories()))
        return
    category = await db.get_category(int(product["category_id"]))
    if category is None:
        await answer_screen(callback, db, "Категория товара не найдена.", catalog_menu(await db.list_categories()))
        return
    await answer_screen(callback, db, product_card(category, product), product_admin_menu(product), photo=product["photo_id"])


@router.callback_query(F.data.startswith("a:pe:"))
async def product_edit_start(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    await callback.answer()
    _, _, product_id, field = callback.data.split(":")
    await state.set_state(ProductEditStates.value)
    await state.update_data(product_id=int(product_id), field=field)
    prompts = {
        "title": "Введите новое название товара.",
        "price": "Введите новую цену товара.",
        "desc": "Введите новое описание товара.",
        "photo": "Отправьте новое фото/ссылку или <code>-</code>, чтобы очистить.",
        "view": "Введите новую ссылку подробнее или <code>-</code>, чтобы очистить.",
    }
    product = await db.get_product(int(product_id))
    await _show_prompt(
        callback,
        state,
        db,
        prompts.get(field, "Введите новое значение."),
        product_admin_menu(product) if product else catalog_menu(await db.list_categories()),
    )


@router.message(ProductEditStates.value)
async def product_edit_save(message: Message, state: FSMContext, db: Database) -> None:
    data = await state.get_data()
    product_id = int(data["product_id"])
    field = str(data["field"])
    product = await db.get_product(product_id)
    menu = product_admin_menu(product) if product else catalog_menu(await db.list_categories())
    if field == "title":
        title = plain_from_message(message).strip()
        if not title:
            await _update_prompt_from_input(message, state, "Название не должно быть пустым.", menu)
            return
        await db.update_product_field(product_id, "title_text", title)
        await db.update_product_field(product_id, "title_html", html_from_message(message))
    elif field == "price":
        amount = parse_amount(message.text or "")
        if amount is None:
            await _update_prompt_from_input(message, state, "Введите корректную цену.", menu)
            return
        await db.update_product_field(product_id, "price", amount)
    elif field == "desc":
        await db.update_product_field(product_id, "description_html", html_from_message(message))
    elif field == "photo":
        if message.photo:
            value = message.photo[-1].file_id
        else:
            raw = (message.text or "").strip()
            value = None if raw == "-" else raw
        await db.update_product_field(product_id, "photo_id", value)
    elif field == "view":
        raw = (message.text or "").strip()
        await db.update_product_field(product_id, "view_url", None if raw == "-" else raw)
    product = await db.get_product(product_id)
    category = await db.get_category(int(product["category_id"])) if product else None
    await _delete_input(message)
    await state.clear()
    if product and category:
        await answer_screen(message, db, product_card(category, product), product_admin_menu(product), photo=product["photo_id"])


@router.message()
async def _admin_fallback(message: Message, state: FSMContext, db: Database) -> None:
    st = await state.get_state()
    if st == ProductStates.view_url.state:
        data = await state.get_data()
        view_url = (message.text or "").strip()
        if view_url == "-":
            view_url = ""
        product_id = await db.create_product(
            category_id=int(data["category_id"]),
            title_text=str(data["title_text"]),
            title_html=str(data["title_html"]),
            price=float(data["price"]),
            description_html=str(data["description_html"]),
            photo_id=data.get("photo_id"),
            view_url=view_url or None,
        )
        await state.clear()
        product = await db.get_product(product_id)
        category = await db.get_category(int(data["category_id"]))
        await _delete_input(message)
        if product and category:
            await answer_screen(message, db, product_card(category, product), product_admin_menu(product), photo=product["photo_id"])
        return

    if st == ProductEditStates.value.state:
        data = await state.get_data()
        field = str(data.get("field") or "")
        if field == "view":
            raw = (message.text or "").strip()
            await db.update_product_field(int(data["product_id"]), "view_url", None if raw == "-" else raw)
            product = await db.get_product(int(data["product_id"]))
            category = await db.get_category(int(product["category_id"])) if product else None
            await _delete_input(message)
            await state.clear()
            if product and category:
                await answer_screen(message, db, product_card(category, product), product_admin_menu(product), photo=product["photo_id"])
            return


@router.callback_query(F.data.startswith("a:prod:toggle:"))
async def product_toggle(callback: CallbackQuery, db: Database) -> None:
    await callback.answer("Готово")
    product_id = int(callback.data.split(":")[-1])
    product = await db.get_product(product_id)
    if product is None:
        return
    await db.update_product_field(product_id, "is_active", 0 if int(product["is_active"]) else 1)
    product = await db.get_product(product_id)
    if product:
        await answer_screen(callback, db, "Статус товара изменен.", product_admin_menu(product))


@router.callback_query(F.data.startswith("a:prod:del:"))
async def product_delete(callback: CallbackQuery, db: Database) -> None:
    await callback.answer("Удалено")
    product_id = int(callback.data.split(":")[-1])
    product = await db.get_product(product_id)
    category_id = int(product["category_id"]) if product else 0
    await db.delete_product(product_id)
    category = await db.get_category(category_id)
    products = await db.list_admin_products(category_id) if category_id else []
    await answer_screen(callback, db, f"{tg('🗑')} Товар удален.", category_menu(category, products) if category else catalog_menu(await db.list_categories()))


@router.callback_query(F.data.startswith("a:users:"))
async def users(callback: CallbackQuery, db: Database) -> None:
    await callback.answer()
    page = int(callback.data.split(":")[-1])
    per_page = 6
    total = await db.count_users()
    user_rows = await db.list_users(per_page, page * per_page)
    await answer_screen(
        callback,
        db,
        f"{tg('👥')} <b>Пользователи</b>\n\nВсего: {total}",
        users_menu(user_rows, page, total, per_page),
    )


@router.callback_query(F.data.regexp(r"^a:u:\d+$"))
async def user_open(callback: CallbackQuery, db: Database) -> None:
    await callback.answer()
    user_id = int(callback.data.split(":")[-1])
    user = await db.get_user(user_id)
    if user is None:
        total = await db.count_users()
        await answer_screen(callback, db, "Пользователь не найден.", users_menu(await db.list_users(), 0, total))
        return
    username = f"@{html.escape(user['username'])}" if user["username"] else "нет"
    text = (
        f"{tg('👤')} <b>Пользователь</b>\n\n"
        f"ID: <code>{user['telegram_id']}</code>\n"
        f"Username: {username}\n"
        f"Имя: {html.escape(str(user['full_name']))}\n"
        f"Баланс: ${money(user['balance'])}\n"
        f"Блокировка: {'да' if int(user['is_blocked']) else 'нет'}"
    )
    await answer_screen(callback, db, text, user_admin_menu(user))


@router.callback_query(F.data.startswith("a:ub:"))
async def user_balance_start(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    await callback.answer()
    _, _, action, user_id = callback.data.split(":")
    await state.set_state(UserBalanceStates.amount)
    await state.update_data(action=action, user_id=int(user_id))
    user = await db.get_user(int(user_id))
    await _show_prompt(callback, state, db, "Введите сумму.", user_admin_menu(user) if user else admin_main())


@router.message(UserBalanceStates.amount)
async def user_balance_save(message: Message, state: FSMContext, db: Database, bot: Bot) -> None:
    data = await state.get_data()
    amount = parse_amount(message.text or "")
    if amount is None:
        await _update_prompt_from_input(message, state, "Введите корректную сумму.")
        return
    user_id = int(data["user_id"])
    action = str(data["action"])
    user = await db.get_user(user_id)
    if user is None:
        await _update_prompt_from_input(message, state, "Пользователь не найден.", admin_main(), clear_state=True)
        return
    if action == "add":
        await db.add_balance(user_id, amount)
        delta_text = f"пополнен на ${money(amount)}"
    elif action == "sub":
        await db.add_balance(user_id, -amount)
        delta_text = f"уменьшен на ${money(amount)}"
    else:
        await db.set_balance(user_id, amount)
        delta_text = f"установлен: ${money(amount)}"
    updated = await db.get_user(user_id)
    try:
        await bot.send_message(user["telegram_id"], f"Ваш баланс {delta_text}.")
    except Exception:
        pass
    await _update_prompt_from_input(
        message,
        state,
        f"{tg('✅')} Баланс изменен.",
        user_admin_menu(updated) if updated else admin_main(),
        clear_state=True,
    )


@router.callback_query(F.data.startswith("a:u:block:"))
async def user_block(callback: CallbackQuery, db: Database, bot: Bot) -> None:
    await callback.answer("Готово")
    user_id = int(callback.data.split(":")[-1])
    user = await db.get_user(user_id)
    if user is None:
        return
    blocked = not bool(int(user["is_blocked"]))
    await db.set_user_blocked(user_id, blocked)
    owner_username = await db.get_setting("owner_username")
    try:
        if blocked:
            await bot.send_message(
                user["telegram_id"],
                "Вы заблокированы в боте. Если возникли вопросы, напишите владельцу.",
                reply_markup=owner_button(owner_username),
            )
        else:
            await bot.send_message(user["telegram_id"], "Вы разблокированы. Приятного пользования.")
    except Exception:
        pass
    updated = await db.get_user(user_id)
    if updated:
        await answer_screen(callback, db, "Статус пользователя изменен.", user_admin_menu(updated))


@router.callback_query(F.data == "a:stats")
async def stats(callback: CallbackQuery, db: Database) -> None:
    await callback.answer()
    data = await db.stats()
    text = (
        f"{tg('📊')} <b>Статистика</b>\n\n"
        f"Пользователей: <b>{data['users']}</b>\n"
        f"Категорий: <b>{data['categories']}</b>\n"
        f"Товаров: <b>{data['products']}</b>\n"
        f"Покупок: <b>{data['sales_count']}</b>\n"
        f"Продаж на сумму: <b>${money(data['sales_total'])}</b>\n"
        f"Пополнений: <b>{data['topups_count']}</b>\n"
        f"Пополнено: <b>${money(data['topups_total'])}</b>\n"
        f"Оборот общий: <b>${money(data['sales_total'])}</b>"
    )
    await answer_screen(callback, db, text, admin_main())


@router.callback_query(F.data.startswith("a:top:ok:"))
async def approve_topup(callback: CallbackQuery, db: Database, bot: Bot) -> None:
    await callback.answer("Пополнено")
    topup_id = int(callback.data.split(":")[-1])
    topup = await db.get_topup(topup_id)
    if topup is None or topup["status"] == "paid":
        return
    await db.set_topup_status(topup_id, "paid")
    await db.add_balance(int(topup["user_id"]), float(topup["amount_usd"]))
    try:
        await bot.send_message(topup["telegram_id"], f"{tg('✅')} Баланс пополнен на ${money(topup['amount_usd'])}.")
    except Exception:
        pass
    await send_log(
        bot,
        db,
        f"{tg('✅')} <b>Пополнение принято</b>\n"
        f"Пользователь: {user_link(int(topup['telegram_id']), str(topup['full_name']))}\n"
        f"Сумма: ${money(topup['amount_usd'])}",
    )
    if callback.message:
        status_text = f"{callback.message.caption or callback.message.text or ''}\n\n{tg('✅')} Заявка принята."
        try:
            await callback.message.edit_caption(caption=status_text, reply_markup=None)
        except Exception:
            await callback.message.edit_text(status_text, reply_markup=None)


@router.callback_query(F.data.startswith("a:top:no:"))
async def reject_topup(callback: CallbackQuery, db: Database, bot: Bot) -> None:
    await callback.answer("Отклонено")
    topup_id = int(callback.data.split(":")[-1])
    topup = await db.get_topup(topup_id)
    if topup is None or topup["status"] != "pending":
        return
    await db.set_topup_status(topup_id, "rejected")
    try:
        await bot.send_message(topup["telegram_id"], f"{tg('❌')} Заявка на пополнение отклонена.")
    except Exception:
        pass
    if callback.message:
        status_text = f"{callback.message.caption or callback.message.text or ''}\n\n{tg('❌')} Заявка отклонена."
        try:
            await callback.message.edit_caption(caption=status_text, reply_markup=None)
        except Exception:
            await callback.message.edit_text(status_text, reply_markup=None)


@router.callback_query(F.data == "a:bc")
async def broadcast_menu(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    await callback.answer()
    await state.set_state(None)
    data = await state.get_data()
    if "buttons" not in data:
        await state.update_data(buttons=[])
        data = await state.get_data()
    await answer_screen(callback, db, _broadcast_state_text(data), broadcast_start())


@router.callback_query(F.data == "a:bc:photo")
async def broadcast_photo_menu_open(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    await callback.answer()
    await state.set_state(None)
    await answer_screen(callback, db, f"{tg('🖼')} <b>Фото рассылки</b>\n\nВыберите действие.", broadcast_photo_menu())


@router.callback_query(F.data == "a:bc:photo:set")
async def broadcast_photo_start(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    await callback.answer()
    await state.set_state(BroadcastStates.photo)
    await _show_prompt(callback, state, db, "Отправьте фото для рассылки.", broadcast_photo_menu())


@router.callback_query(F.data == "a:bc:photo:clear")
async def broadcast_photo_clear(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    await callback.answer("Фото очищено")
    await state.update_data(photo_id=None)
    data = await state.get_data()
    await answer_screen(callback, db, _broadcast_state_text(data), broadcast_start())


@router.message(BroadcastStates.photo, F.photo)
async def broadcast_photo_save(message: Message, state: FSMContext) -> None:
    await state.update_data(photo_id=message.photo[-1].file_id)
    await state.set_state(None)
    data = await state.get_data()
    await _update_prompt_from_input(
        message,
        state,
        f"{tg('✅')} Фото сохранено.\n\n{_broadcast_state_text(data)}",
        broadcast_start(),
    )


@router.message(BroadcastStates.photo)
async def broadcast_photo_required(message: Message, state: FSMContext) -> None:
    await _update_prompt_from_input(message, state, "Нужно отправить фотографию.", broadcast_photo_menu())


@router.callback_query(F.data == "a:bc:text")
async def broadcast_text_start(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    await callback.answer()
    await state.set_state(BroadcastStates.text)
    await _show_prompt(callback, state, db, f"{tg('📝')} Отправьте текст рассылки. Форматирование Telegram сохранится.", broadcast_start())


@router.message(BroadcastStates.text)
async def broadcast_text_save(message: Message, state: FSMContext) -> None:
    await state.update_data(text=html_from_message(message))
    await state.set_state(None)
    data = await state.get_data()
    await _update_prompt_from_input(
        message,
        state,
        f"{tg('✅')} Текст сохранен.\n\n{_broadcast_state_text(data)}",
        broadcast_start(),
    )


@router.callback_query(F.data == "a:bc:buttons")
async def broadcast_buttons_open(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    await callback.answer()
    data = await state.get_data()
    buttons = data.get("buttons") or []
    await answer_screen(
        callback,
        db,
        f"{tg('🔗')} <b>Inline кнопки</b>\n\n"
        "Добавляйте кнопки по одной: текст, ссылка, стиль. "
        "Стили сохраняются в структуре, но Telegram отображает обычные inline-кнопки.",
        broadcast_buttons_menu(buttons),
    )


@router.callback_query(F.data == "a:bc:btn:add")
async def broadcast_button_add(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    await callback.answer()
    await state.set_state(BroadcastStates.button_text)
    await _show_prompt(
        callback,
        state,
        db,
        "Введите текст inline-кнопки.",
        broadcast_buttons_menu((await state.get_data()).get("buttons") or []),
    )


@router.message(BroadcastStates.button_text)
async def broadcast_button_text_save(message: Message, state: FSMContext) -> None:
    text = plain_from_message(message).strip()
    if not text:
        await _update_prompt_from_input(
            message,
            state,
            "Текст кнопки не должен быть пустым.",
            broadcast_buttons_menu((await state.get_data()).get("buttons") or []),
        )
        return
    await state.update_data(button_text=text)
    await state.set_state(BroadcastStates.button_url)
    await _update_prompt_from_input(message, state, "Теперь отправьте ссылку для кнопки.")


@router.message(BroadcastStates.button_url)
async def broadcast_button_url_save(message: Message, state: FSMContext) -> None:
    url = (message.text or "").strip()
    if not (url.startswith("http://") or url.startswith("https://") or url.startswith("tg://")):
        await _update_prompt_from_input(message, state, "Ссылка должна начинаться с http://, https:// или tg://.")
        return
    await state.update_data(button_url=url)
    await state.set_state(None)
    await _update_prompt_from_input(message, state, "Выберите стиль кнопки.", broadcast_button_style_menu())


@router.callback_query(F.data.startswith("a:bc:style:"))
async def broadcast_button_style_save(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    await callback.answer("Кнопка добавлена")
    style = callback.data.split(":")[-1]
    data = await state.get_data()
    buttons: list[dict[str, str]] = data.get("buttons") or []
    buttons.append(
        {
            "text": str(data.get("button_text") or "Кнопка"),
            "url": str(data.get("button_url") or "https://t.me"),
            "style": style,
        }
    )
    await state.update_data(buttons=buttons, button_text=None, button_url=None)
    await answer_screen(callback, db, _broadcast_state_text(await state.get_data()), broadcast_start())


@router.callback_query(F.data == "a:bc:btn:clear")
async def broadcast_buttons_clear(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    await callback.answer("Кнопки очищены")
    await state.update_data(buttons=[])
    await answer_screen(callback, db, _broadcast_state_text(await state.get_data()), broadcast_start())


@router.callback_query(F.data == "a:bc:preview")
async def broadcast_preview(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    await callback.answer()
    data = await state.get_data()
    text = str(data.get("text") or "Текст рассылки не задан.")
    buttons: list[dict[str, str]] = data.get("buttons") or []
    markup = _broadcast_preview_markup(buttons)
    if data.get("photo_id"):
        await answer_screen(callback, db, text, markup, photo=str(data["photo_id"]))
    else:
        await answer_screen(callback, db, text, markup)


@router.callback_query(F.data == "a:bc:cancel")
async def broadcast_cancel(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    await state.clear()
    await callback.answer("Отменено")
    await answer_screen(callback, db, "Рассылка отменена.", admin_main())


@router.callback_query(F.data == "a:bc:send")
async def broadcast_send(callback: CallbackQuery, state: FSMContext, db: Database, bot: Bot) -> None:
    data = await state.get_data()
    text = str(data.get("text") or "")
    if not text:
        await callback.answer("Сначала добавьте текст", show_alert=True)
        return
    await callback.answer("Отправляю")
    photo_id = data.get("photo_id")
    buttons: list[dict[str, str]] = data.get("buttons") or []
    markup = _broadcast_markup(buttons)
    users = await db.fetchall("SELECT telegram_id FROM users WHERE is_blocked = 0")
    sent = 0
    for user in users:
        try:
            if photo_id:
                await bot.send_photo(user["telegram_id"], photo_id, caption=text, reply_markup=markup)
            else:
                await bot.send_message(user["telegram_id"], text, reply_markup=markup)
            sent += 1
        except Exception:
            continue
    await state.clear()
    await answer_screen(callback, db, f"{tg('✅')} Рассылка завершена. Доставлено: {sent}/{len(users)}.", admin_main())


@router.callback_query(F.data == "a:subs")
async def subscriptions(callback: CallbackQuery, db: Database) -> None:
    await callback.answer()
    channels = await db.list_subscriptions(active_only=False)
    await answer_screen(callback, db, f"{tg('🔐')} <b>Обязательные подписки</b>", subscriptions_menu(channels))


@router.callback_query(F.data == "a:sub:add")
async def subscription_add_start(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    await callback.answer()
    await state.set_state(SubscriptionStates.channel_id)
    await _show_prompt(
        callback,
        state,
        db,
        "Отправьте ID канала, например <code>-1001234567890</code> или username канала. "
        "Бот должен быть добавлен в канал.",
        subscriptions_menu(await db.list_subscriptions(active_only=False)),
    )


@router.message(SubscriptionStates.channel_id)
async def subscription_add_save(message: Message, state: FSMContext, db: Database, bot: Bot) -> None:
    channel_id = (message.text or "").strip()
    if not channel_id:
        await _update_prompt_from_input(
            message,
            state,
            "ID канала не должен быть пустым.",
            subscriptions_menu(await db.list_subscriptions(active_only=False)),
        )
        return
    try:
        chat = await bot.get_chat(channel_id)
    except Exception as exc:
        await _update_prompt_from_input(
            message,
            state,
            f"Не удалось получить канал: <code>{html.escape(str(exc))}</code>",
            subscriptions_menu(await db.list_subscriptions(active_only=False)),
        )
        return
    invite_url = chat.invite_link
    if not invite_url and chat.username:
        invite_url = f"https://t.me/{chat.username}"
    await db.add_subscription(str(chat.id), chat.title or str(chat.id), invite_url)
    await _update_prompt_from_input(
        message,
        state,
        f"{tg('✅')} Канал добавлен.",
        subscriptions_menu(await db.list_subscriptions(active_only=False)),
        clear_state=True,
    )


@router.callback_query(F.data.startswith("a:sub:del:"))
async def subscription_delete(callback: CallbackQuery, db: Database) -> None:
    await callback.answer("Удалено")
    subscription_id = int(callback.data.split(":")[-1])
    await db.delete_subscription(subscription_id)
    await answer_screen(callback, db, "Канал удален.", subscriptions_menu(await db.list_subscriptions(active_only=False)))


@router.callback_query(F.data == "a:promo")
async def promo_admin(callback: CallbackQuery, db: Database) -> None:
    await callback.answer()
    await answer_screen(callback, db, f"{tg('🎁')} <b>Промокоды</b>", promo_menu())


@router.callback_query(F.data == "a:promo:add")
async def promo_add_start(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    await callback.answer()
    await state.set_state(PromoAdminStates.code)
    await _show_prompt(callback, state, db, "Введите код промокода.", promo_menu())


@router.message(PromoAdminStates.code)
async def promo_code_save(message: Message, state: FSMContext) -> None:
    code = (message.text or "").strip()
    if not code:
        await _update_prompt_from_input(message, state, "Код не должен быть пустым.", promo_menu())
        return
    await state.update_data(code=code)
    await state.set_state(PromoAdminStates.amount)
    await _update_prompt_from_input(message, state, "Введите сумму пополнения по промокоду в долларах.", promo_menu())


@router.message(PromoAdminStates.amount)
async def promo_amount_save(message: Message, state: FSMContext) -> None:
    amount = parse_amount(message.text or "")
    if amount is None:
        await _update_prompt_from_input(message, state, "Введите корректную сумму.", promo_menu())
        return
    await state.update_data(amount=amount)
    await state.set_state(PromoAdminStates.max_uses)
    await _update_prompt_from_input(message, state, "Введите максимальное количество использований.", promo_menu())


@router.message(PromoAdminStates.max_uses)
async def promo_max_save(message: Message, state: FSMContext, db: Database) -> None:
    try:
        max_uses = int((message.text or "").strip())
    except ValueError:
        await _update_prompt_from_input(message, state, "Введите число.", promo_menu())
        return
    if max_uses <= 0:
        await _update_prompt_from_input(message, state, "Количество должно быть больше нуля.", promo_menu())
        return
    data = await state.get_data()
    try:
        await db.create_promo(str(data["code"]), float(data["amount"]), max_uses)
    except Exception as exc:
        await _update_prompt_from_input(
            message,
            state,
            f"Не удалось создать промокод: <code>{html.escape(str(exc))}</code>",
            promo_menu(),
        )
        return
    await _update_prompt_from_input(message, state, f"{tg('✅')} Промокод создан.", promo_menu(), clear_state=True)
