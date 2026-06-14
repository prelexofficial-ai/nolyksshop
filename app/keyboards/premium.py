from __future__ import annotations

import re
from typing import Any

from aiogram.enums import ButtonStyle
from aiogram.utils.keyboard import InlineKeyboardBuilder


PREMIUM_EMOJI_IDS = {
    "🎨": "5814690801665446789",
    "💳": "4924998397997352581",
    "⚙": "5870982283724328568",
    "⚙️": "5870982283724328568",
    "🛒": "5210997770567062009",
    "👥": "5870772616305839506",
    "📊": "5213399275760814479",
    "📣": "5345952175652629268",
    "📢": "5345952175652629268",
    "🔐": "5211096541929968385",
    "🎁": "4924874531140535819",
    "🏠": "5843680709926981861",
    "⬅️": "5877536313623711363",
    "➡️": "5875506366050734240",
    "🖼": "5870782662234346251",
    "➕": "5775937998948404844",
    "➖": "5287558899807827494",
    "✏️": "5879841310902324730",
    "🗑": "5870875489362513438",
    "💵": "5967390100357648692",
    "📝": "6006038041448156880",
    "🔗": "4924794760712948756",
    "🔁": "6005843436479975944",
    "🚫": "5872829476143894491",
    "✅": "5776375003280838798",
    "❌": "5778527486270770928",
    "👁": "4927329001870984503",
    "👁️": "4927329001870984503",
    "🧹": "5870977305857232786",
    "👤": "5260399854500191689",
    "ℹ️": "5879785854284599288",
    "❓": "5220053623211305785",
    "📈": "5994378914636500516",
    "🧾": "4927428662292121601",
    "👛": "5361914370068613491",
    "👑": "5807868868886009920",
    "🔎": "5870974879200711167",
    "💸": "5211010719893460599",
}

STYLE_MAP = {
    "danger": ButtonStyle.DANGER,
    "success": ButtonStyle.SUCCESS,
    "primary": ButtonStyle.PRIMARY,
}


def emoji_id(symbol: str) -> str | None:
    return PREMIUM_EMOJI_IDS.get(symbol)


def tg(symbol: str) -> str:
    icon_id = emoji_id(symbol)
    if not icon_id:
        return symbol
    return f'<tg-emoji emoji-id="{icon_id}">{symbol}</tg-emoji>'


def premiumize_html(text: str) -> str:
    parts = re.split(r"(<tg-emoji\b[^>]*>.*?</tg-emoji>)", text, flags=re.DOTALL)
    for index, part in enumerate(parts):
        if part.startswith("<tg-emoji"):
            continue
        for symbol in sorted(PREMIUM_EMOJI_IDS, key=len, reverse=True):
            if symbol in part:
                part = part.replace(symbol, tg(symbol))
        parts[index] = part
    return "".join(parts)


def first_custom_emoji_id(message: Any) -> str | None:
    entities = getattr(message, "entities", None) or getattr(message, "caption_entities", None) or []
    for entity in entities:
        entity_type = getattr(entity, "type", "")
        value = getattr(entity_type, "value", str(entity_type))
        custom_emoji_id = getattr(entity, "custom_emoji_id", None)
        if value == "custom_emoji" and custom_emoji_id:
            return str(custom_emoji_id)
    return None


def _remove_utf16_span(text: str, offset: int, length: int) -> str:
    encoded = text.encode("utf-16-le")
    start = max(offset, 0) * 2
    end = max(offset + length, 0) * 2
    try:
        cleaned = (encoded[:start] + encoded[end:]).decode("utf-16-le")
    except UnicodeDecodeError:
        return text
    return re.sub(r"\s{2,}", " ", cleaned).strip()


def split_button_icon(text: str, custom_emoji_id: str | None = None) -> tuple[str, str | None]:
    clean_text = text.strip()
    icon_id = custom_emoji_id
    for symbol in sorted(PREMIUM_EMOJI_IDS, key=len, reverse=True):
        if symbol in clean_text:
            clean_text = clean_text.replace(symbol, "", 1).strip()
            icon_id = icon_id or emoji_id(symbol)
            break
    return clean_text or text.strip(), icon_id


def split_message_button_icon(message: Any, text: str | None = None) -> tuple[str, str | None]:
    raw_text = text if text is not None else getattr(message, "text", None) or getattr(message, "caption", None) or ""
    entities = getattr(message, "entities", None) or getattr(message, "caption_entities", None) or []
    for entity in entities:
        entity_type = getattr(entity, "type", "")
        value = getattr(entity_type, "value", str(entity_type))
        custom_emoji_id = getattr(entity, "custom_emoji_id", None)
        if value == "custom_emoji" and custom_emoji_id:
            offset = int(getattr(entity, "offset", 0))
            length = int(getattr(entity, "length", 0))
            clean_text = _remove_utf16_span(raw_text, offset, length)
            return split_button_icon(clean_text, str(custom_emoji_id))
    return split_button_icon(raw_text)


def url_button_kwargs(
    text: str,
    url: str,
    style: str = "default",
    icon_custom_emoji_id: str | None = None,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {"text": text, "url": url}
    if icon_custom_emoji_id:
        kwargs["icon_custom_emoji_id"] = icon_custom_emoji_id
    style_value = STYLE_MAP.get(style)
    if style_value is not None:
        kwargs["style"] = style_value
    return kwargs


def button(builder: InlineKeyboardBuilder, icon: str, text: str, **kwargs: Any) -> None:
    icon_id = emoji_id(icon)
    if icon_id:
        kwargs["icon_custom_emoji_id"] = icon_id
    builder.button(text=text, **kwargs)
