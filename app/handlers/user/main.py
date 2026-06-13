from __future__ import annotations

import html

from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import Config
from app.database import Database
from app.keyboards.admin import topup_decision
from app.keyboards.user import (
    back_main,
    categories_menu,
    invoice_menu,
    main_menu,
    owner_button,
    product_menu,
    products_menu,
    profile_menu,
    subscription_menu,
    topup_methods,
)
from app.services.crypto_pay import CryptoPayClient
from app.services.logs import send_log
from app.services.screens import answer_screen
from app.services.subscriptions import missing_subscriptions
from app.states import PromoStates, TopupStates
from app.utils.formatting import (
    money,
    order_code,
    parse_amount,
    parse_rub_rate,
    product_card,
    profile_text,
    purchase_user_text,
    user_link,
)
from app.keyboards.premium import tg

router = Router(name="user")


async def _load_user(
    target: Message | CallbackQuery,
    db: Database,
    bot: Bot,
    config: Config,
    check_subscriptions: bool = True,
):
    tg_user = target.from_user
    if tg_user is None:
        return None

    user, created = await db.upsert_user(
        telegram_id=tg_user.id,
        username=tg_user.username,
        full_name=tg_user.full_name,
    )
    if created:
        await send_log(
            bot,
            db,
            f"{tg('👤')} <b>Новый пользователь</b>\n"
            f"Пользователь: {user_link(tg_user.id, tg_user.full_name)}\n"
            f"ID: <code>{tg_user.id}</code>",
        )

    if int(user["is_blocked"]) and tg_user.id not in config.owner_ids:
        owner_username = await db.get_setting("owner_username")
        await answer_screen(
            target,
            db,
            "Вы заблокированы в боте. Если возникли вопросы, напишите владельцу.",
            owner_button(owner_username),
        )
        return None

    if check_subscriptions and tg_user.id not in config.owner_ids:
        missing = await missing_subscriptions(bot, db, tg_user.id)
        if missing:
            await answer_screen(
                target,
                db,
                f"{tg('🔐')} Для доступа к магазину подпишитесь на обязательные каналы.",
                subscription_menu(missing),
            )
            return None
    return user


@router.message(CommandStart())
async def start(message: Message, db: Database, bot: Bot, config: Config) -> None:
    user = await _load_user(message, db, bot, config)
    if user is None:
        return
    await show_main(message, db, config)


@router.callback_query(F.data == "u:sub:check")
async def check_subscription(callback: CallbackQuery, db: Database, bot: Bot, config: Config) -> None:
    await callback.answer()
    user = await _load_user(callback, db, bot, config)
    if user is None:
        return
    await show_main(callback, db, config)


@router.callback_query(F.data == "u:main")
async def main_callback(callback: CallbackQuery, db: Database, bot: Bot, config: Config) -> None:
    await callback.answer()
    user = await _load_user(callback, db, bot, config)
    if user is None:
        return
    await show_main(callback, db, config)


async def show_main(target: Message | CallbackQuery, db: Database, config: Config) -> None:
    text = await db.get_setting("main_text")
    is_admin = bool(target.from_user and target.from_user.id in config.owner_ids)
    await answer_screen(target, db, text, main_menu(is_admin=is_admin))


@router.callback_query(F.data == "u:info")
async def info(callback: CallbackQuery, db: Database, bot: Bot, config: Config) -> None:
    await callback.answer()
    if await _load_user(callback, db, bot, config) is None:
        return
    await answer_screen(callback, db, await db.get_setting("info_text"), back_main())


@router.callback_query(F.data == "u:faq")
async def faq(callback: CallbackQuery, db: Database, bot: Bot, config: Config) -> None:
    await callback.answer()
    if await _load_user(callback, db, bot, config) is None:
        return
    await answer_screen(callback, db, await db.get_setting("faq_text"), back_main())


@router.callback_query(F.data == "u:profile")
async def profile(callback: CallbackQuery, db: Database, bot: Bot, config: Config) -> None:
    await callback.answer()
    user = await _load_user(callback, db, bot, config)
    if user is None:
        return
    text = profile_text(await db.get_setting("profile_text"), user)
    await answer_screen(callback, db, text, profile_menu())


@router.callback_query(F.data == "u:watch")
async def price_watch(callback: CallbackQuery, db: Database, bot: Bot, config: Config) -> None:
    await callback.answer()
    if await _load_user(callback, db, bot, config) is None:
        return
    await answer_screen(
        callback,
        db,
        f"{tg('📈')} Отслеживание изменения цен включено в структуру. Уведомления можно расширить под конкретные товары.",
        profile_menu(),
    )


@router.callback_query(F.data == "u:catalog")
async def catalog(callback: CallbackQuery, db: Database, bot: Bot, config: Config) -> None:
    await callback.answer()
    if await _load_user(callback, db, bot, config) is None:
        return
    categories = await db.list_categories()
    text = f"{tg('🛒')} <b>Каталог</b>\n\nВыберите категорию." if categories else "Категории пока не добавлены."
    await answer_screen(callback, db, text, categories_menu(categories))


@router.callback_query(F.data.startswith("u:cat:"))
async def category(callback: CallbackQuery, db: Database, bot: Bot, config: Config) -> None:
    await callback.answer()
    if await _load_user(callback, db, bot, config) is None:
        return
    category_id = int(callback.data.split(":")[-1])
    category_row = await db.get_category(category_id)
    if category_row is None:
        await answer_screen(callback, db, "Категория не найдена.", categories_menu(await db.list_categories()))
        return
    products = await db.list_products(category_id)
    text = f"{tg('🛒')} <b>{category_row['title_html']}</b>\n\nВыберите товар." if products else "В этой категории пока нет товаров."
    await answer_screen(callback, db, text, products_menu(products, category_id))


@router.callback_query(F.data.startswith("u:prod:"))
async def product(callback: CallbackQuery, db: Database, bot: Bot, config: Config) -> None:
    await callback.answer()
    if await _load_user(callback, db, bot, config) is None:
        return
    product_id = int(callback.data.split(":")[-1])
    product_row = await db.get_product(product_id)
    if product_row is None or not int(product_row["is_active"]):
        await answer_screen(callback, db, "Товар не найден или выключен.", back_main())
        return
    category_row = await db.get_category(int(product_row["category_id"]))
    if category_row is None:
        await answer_screen(callback, db, "Категория товара не найдена.", back_main())
        return
    await answer_screen(
        callback,
        db,
        product_card(category_row, product_row),
        product_menu(product_row, int(category_row["id"])),
        photo=product_row["photo_id"],
    )


@router.callback_query(F.data.startswith("u:buy:"))
async def buy_product(callback: CallbackQuery, db: Database, bot: Bot, config: Config) -> None:
    await callback.answer()
    user = await _load_user(callback, db, bot, config)
    if user is None:
        return

    product_id = int(callback.data.split(":")[-1])
    product_row = await db.get_product(product_id)
    if product_row is None or not int(product_row["is_active"]):
        await answer_screen(callback, db, "Товар не найден или выключен.", back_main())
        return

    price = float(product_row["price"])
    if float(user["balance"]) < price:
        await answer_screen(
            callback,
            db,
            f"Недостаточно баланса. Цена товара: ${money(price)}, ваш баланс: ${money(user['balance'])}.",
            topup_methods(await db.get_setting("owner_username")),
        )
        return

    await db.add_balance(int(user["id"]), -price)
    code = order_code()
    await db.create_purchase(int(user["id"]), int(product_row["id"]), str(product_row["title_text"]), price, code)
    owner_username = await db.get_setting("owner_username")

    await answer_screen(
        callback,
        db,
        purchase_user_text(str(product_row["title_text"]), price, code, owner_username),
        owner_button(owner_username),
    )
    await send_log(
        bot,
        db,
        f"{tg('🛒')} <b>Покупка товара</b>\n"
        f"Пользователь: {user_link(int(user['telegram_id']), str(user['full_name']))}\n"
        f"Товар: {html.escape(str(product_row['title_text']))}\n"
        f"Сумма: ${money(price)}\n"
        f"Код: <code>{html.escape(code)}</code>",
    )


@router.callback_query(F.data == "u:topup")
async def topup(callback: CallbackQuery, db: Database, bot: Bot, config: Config) -> None:
    await callback.answer()
    if await _load_user(callback, db, bot, config) is None:
        return
    await answer_screen(
        callback,
        db,
        await db.get_setting("topup_text", f"{tg('💳')} <b>Пополнение баланса</b>\n\nВыберите способ пополнения."),
        topup_methods(await db.get_setting("owner_username")),
    )


@router.callback_query(F.data == "u:topup:crypto")
async def crypto_amount(callback: CallbackQuery, state: FSMContext, db: Database, bot: Bot, config: Config) -> None:
    await callback.answer()
    if await _load_user(callback, db, bot, config) is None:
        return
    await state.set_state(TopupStates.crypto_amount)
    await answer_screen(
        callback,
        db,
        await db.get_setting("crypto_amount_text", "Введите сумму пополнения в долларах. Минимум $1."),
        back_main(),
    )


@router.message(TopupStates.crypto_amount)
async def create_crypto_invoice(
    message: Message,
    state: FSMContext,
    db: Database,
    bot: Bot,
    config: Config,
    crypto: CryptoPayClient,
) -> None:
    user = await _load_user(message, db, bot, config)
    if user is None:
        return
    amount = parse_amount(message.text or "")
    if amount is None or amount < 1:
        await message.answer("Введите корректную сумму от $1.")
        return
    if not crypto.enabled:
        await state.clear()
        await answer_screen(message, db, "CryptoBot сейчас не настроен. Выберите карту или пополнение через владельца.", profile_menu())
        return

    asset = "USDT"
    invoice = await crypto.create_invoice(asset, amount, f"Top up user {user['telegram_id']}")
    if invoice is None:
        await state.clear()
        await message.answer("Не удалось создать счет. Попробуйте позже.")
        return
    topup_id = await db.create_topup(
        int(user["id"]),
        method="crypto",
        amount_usd=amount,
        provider_invoice_id=invoice.invoice_id,
        pay_url=invoice.pay_url,
    )
    await state.clear()
    await answer_screen(
        message,
        db,
        await db.get_setting("crypto_invoice_text", "Оплатите счет, затем нажмите кнопку проверки оплаты."),
        invoice_menu(invoice.pay_url, topup_id),
    )


@router.callback_query(F.data.startswith("u:topup:check:"))
async def check_crypto_invoice(
    callback: CallbackQuery,
    db: Database,
    bot: Bot,
    config: Config,
    crypto: CryptoPayClient,
) -> None:
    await callback.answer()
    user = await _load_user(callback, db, bot, config)
    if user is None:
        return

    topup_id = int(callback.data.split(":")[-1])
    topup_row = await db.get_topup(topup_id)
    if topup_row is None or int(topup_row["user_id"]) != int(user["id"]):
        await answer_screen(callback, db, "Счет не найден.", profile_menu())
        return
    if topup_row["status"] == "paid":
        await answer_screen(callback, db, "Этот счет уже оплачен.", profile_menu())
        return

    paid = await crypto.is_invoice_paid(str(topup_row["provider_invoice_id"]))
    if not paid:
        await answer_screen(callback, db, "Оплата пока не найдена. Если вы уже оплатили, попробуйте проверить еще раз.", profile_menu())
        return

    await db.set_topup_status(topup_id, "paid")
    await db.add_balance(int(user["id"]), float(topup_row["amount_usd"]))
    await answer_screen(callback, db, f"{tg('✅')} Баланс пополнен на ${money(topup_row['amount_usd'])}.", profile_menu())
    await send_log(
        bot,
        db,
        f"{tg('✅')} <b>Crypto пополнение</b>\n"
        f"Пользователь: {user_link(int(user['telegram_id']), str(user['full_name']))}\n"
        f"Сумма: ${money(topup_row['amount_usd'])}",
    )


@router.callback_query(F.data == "u:topup:card")
async def card_amount(callback: CallbackQuery, state: FSMContext, db: Database, bot: Bot, config: Config) -> None:
    await callback.answer()
    if await _load_user(callback, db, bot, config) is None:
        return
    await state.set_state(TopupStates.card_amount)
    await answer_screen(
        callback,
        db,
        await db.get_setting("card_amount_text", "Введите сумму пополнения в долларах. Минимум $1."),
        back_main(),
    )


@router.message(TopupStates.card_amount)
async def card_details(message: Message, state: FSMContext, db: Database, bot: Bot, config: Config) -> None:
    user = await _load_user(message, db, bot, config)
    if user is None:
        return
    amount = parse_amount(message.text or "")
    if amount is None or amount < 1:
        await message.answer("Введите корректную сумму от $1.")
        return
    try:
        rate = parse_rub_rate(await db.get_setting("rub_rate", "100"))
    except ValueError:
        rate = 100
    amount_rub = round(amount * rate, 2)
    topup_id = await db.create_topup(int(user["id"]), method="card", amount_usd=amount, amount_rub=amount_rub)
    await state.update_data(topup_id=topup_id)
    await state.set_state(TopupStates.card_screenshot)

    card = await db.get_setting("bank_card")
    holder = await db.get_setting("bank_holder")
    bank = await db.get_setting("bank_name")
    parts = [
        f"{tg('💳')} <b>Пополнение банковской картой</b>",
        f"Сумма: ${money(amount)} / {money(amount_rub)} RUB",
        f"Карта: <code>{html.escape(card or 'не указана')}</code>",
    ]
    if holder and holder != "-":
        parts.append(f"ФИО: {html.escape(holder)}")
    if bank and bank != "-":
        parts.append(f"Банк: {html.escape(bank)}")
    parts.append("\nПосле перевода отправьте сюда скриншот оплаты.")
    await answer_screen(message, db, "\n".join(parts), back_main())


@router.message(TopupStates.card_screenshot, F.photo)
async def card_screenshot(message: Message, state: FSMContext, db: Database, bot: Bot, config: Config) -> None:
    user = await _load_user(message, db, bot, config)
    if user is None:
        return
    data = await state.get_data()
    topup_id = int(data["topup_id"])
    photo_id = message.photo[-1].file_id
    await db.set_topup_screenshot(topup_id, photo_id)
    topup_row = await db.get_topup(topup_id)
    await state.clear()

    await answer_screen(
        message,
        db,
        await db.get_setting("card_pending_text", f"{tg('✅')} Ваша заявка будет проверена в течение часа."),
        profile_menu(),
    )
    if topup_row:
        await send_log(
            bot,
            db,
            f"{tg('💳')} <b>Заявка на пополнение картой</b>\n"
            f"Пользователь: {user_link(int(user['telegram_id']), str(user['full_name']))}\n"
            f"Сумма: ${money(topup_row['amount_usd'])} / {money(topup_row['amount_rub'])} RUB\n"
            f"Время: <code>{html.escape(str(topup_row['created_at']))}</code>",
            reply_markup=topup_decision(topup_id),
            photo=photo_id,
        )


@router.message(TopupStates.card_screenshot)
async def card_screenshot_required(message: Message) -> None:
    await message.answer("Отправьте скриншот оплаты фотографией.")


@router.callback_query(F.data == "u:promo")
async def promo_start(callback: CallbackQuery, state: FSMContext, db: Database, bot: Bot, config: Config) -> None:
    await callback.answer()
    if await _load_user(callback, db, bot, config) is None:
        return
    await state.set_state(PromoStates.code)
    await answer_screen(callback, db, "Введите промокод.", back_main())


@router.message(PromoStates.code)
async def promo_apply(message: Message, state: FSMContext, db: Database, bot: Bot, config: Config) -> None:
    user = await _load_user(message, db, bot, config)
    if user is None:
        return
    code = (message.text or "").strip()
    promo = await db.get_promo(code)
    if promo is None:
        await message.answer("Промокод не найден или выключен.")
        return
    ok = await db.use_promo(int(promo["id"]), int(user["id"]))
    await state.clear()
    if not ok:
        await answer_screen(message, db, "Этот промокод уже использован или закончился.", profile_menu())
        return
    await answer_screen(message, db, f"{tg('🎁')} Промокод активирован. Баланс пополнен на ${money(promo['amount'])}.", profile_menu())
    await send_log(
        bot,
        db,
        f"{tg('🎁')} <b>Промокод активирован</b>\n"
        f"Пользователь: {user_link(int(user['telegram_id']), str(user['full_name']))}\n"
        f"Код: <code>{html.escape(str(promo['code']))}</code>\n"
        f"Сумма: ${money(promo['amount'])}",
    )


@router.callback_query(F.data == "u:history")
async def history(callback: CallbackQuery, db: Database, bot: Bot, config: Config) -> None:
    await callback.answer()
    user = await _load_user(callback, db, bot, config)
    if user is None:
        return
    purchases = await db.list_user_purchases(int(user["id"]))
    if not purchases:
        await answer_screen(callback, db, "История покупок пока пустая.", profile_menu())
        return
    lines = [f"{tg('🧾')} <b>История покупок</b>"]
    for purchase in purchases:
        lines.append(
            f"\n{html.escape(str(purchase['product_title']))}\n"
            f"Сумма: ${money(purchase['amount'])}\n"
            f"Код: <code>{html.escape(str(purchase['code']))}</code>\n"
            f"Дата: <code>{html.escape(str(purchase['created_at']))}</code>"
        )
    await answer_screen(callback, db, "\n".join(lines), profile_menu())
