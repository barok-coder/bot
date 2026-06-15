import logging
import re
import html
import os

from google import genai
from google.genai import types
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

try:
    from .config import settings
    from .database import UserSettings, db
except ImportError:
    from config import settings
    from database import UserSettings, db


logger = logging.getLogger("telegram_gemini_bot.handlers")

settings.validate()

telegram_app = Application.builder().token(settings.bot_token).build()
gemini_client = genai.Client(api_key=settings.gemini_api_key)

MENU_ASK = "Ask Gemini AI"
MENU_SETTINGS = "Bot Settings"
MENU_GUIDE = "Feature Guide"
MENU_TOKENS = "Token Status"
DIVIDER = "──────────────────────────────"


def split_message(text: str, limit: int = 3900) -> list[str]:
    if len(text) <= limit:
        return [text]

    chunks = []
    current = []
    current_length = 0

    for line in text.splitlines(keepends=True):
        if current and current_length + len(line) > limit:
            chunks.append("".join(current))
            current = []
            current_length = 0
        current.append(line)
        current_length += len(line)

    if current:
        chunks.append("".join(current))
            
    return chunks


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [MENU_ASK],
            [MENU_SETTINGS, MENU_GUIDE],
            [MENU_TOKENS],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Ask Gemini or send a photo/file...",
    )


def settings_keyboard(user: UserSettings) -> InlineKeyboardMarkup:
    concise_status = "Concise: ON" if user.concise_mode else "Concise: OFF"
    rich_status = "Rich UI: ON" if user.rich_ui else "Rich UI: OFF"

    keyboard = list()
    keyboard.append(
        [
            InlineKeyboardButton("Creative", callback_data="temp:creative"),
            InlineKeyboardButton("Balanced", callback_data="temp:balanced"),
            InlineKeyboardButton("Precise", callback_data="temp:precise"),
        ]
    )
    keyboard.append(
        [
            InlineKeyboardButton(concise_status, callback_data="toggle:concise"),
            InlineKeyboardButton(rich_status, callback_data="toggle:rich_ui"),
        ]
    )
    keyboard.append(
        [InlineKeyboardButton("Reset Memory", callback_data="memory:reset")]
    )

    return InlineKeyboardMarkup(keyboard)


def guide_keyboard() -> InlineKeyboardMarkup:
    keyboard = list()
    keyboard.append(
        [
            InlineKeyboardButton("Open Settings", callback_data="open:settings"),
            InlineKeyboardButton("Token Status", callback_data="open:tokens"),
        ]
    )
    keyboard.append(
        [
            InlineKeyboardButton("Creative Mode", callback_data="temp:creative"),
            InlineKeyboardButton("Precise Mode", callback_data="temp:precise"),
        ]
    )

    return InlineKeyboardMarkup(keyboard)


def format_header(title: str, subtitle: str | None = None) -> str:
    if subtitle:
        return f"<b>{title.upper()}</b>\n{DIVIDER}\n<i>{subtitle}</i>"
    return f"<b>{title.upper()}</b>\n{DIVIDER}"


def welcome_text(first_name: str | None) -> str:
    name = first_name or "User"
    header = format_header("Gemini AI Core", f"Welcome, {name}.")
    return f"""{header}

A clean, cloud-hosted assistant powered by Google Gemini AI.

• Submit text queries, images, or document files
• Tune response engines via settings
• Explore documentation guides
• Track session token metadata profiles

Interact with the terminal menu below or attach media to begin."""


def settings_text(user: UserSettings) -> str:
    concise_flag = "Enabled" if user.concise_mode else "Disabled"
    rich_flag = "Enabled" if user.rich_ui else "Disabled"
    header = format_header("System Settings", "Configure engine behavioral traits.")
    
    return f"""{header}

<b>Engine Model:</b> <code>{settings.gemini_model}</code>
<b>Temperature:</b> <code>{user.temperature}</code> ({user.temperature_label})
<b>Concise Mode:</b> <code>{concise_flag}</code>
<b>Rich UI Elements:</b> <code>{rich_flag}</code>

Select an interface option below to update
