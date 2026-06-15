import logging
import re

from google import genai
from google.genai import types
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.constants import ChatAction, ParseMode
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

MENU_ASK = "🧠 Ask Gemini AI"
MENU_SETTINGS = "⚙️ Bot Settings"
MENU_GUIDE = "📜 Feature Guide"
MENU_TOKENS = "📊 Token Status"
DIVIDER = "───────────────"


def escape_md(text: object) -> str:
    raw = "" if text is None else str(text)
    return re.sub(r"([_*\[\]()~`>#+\-=|{}.!\\])", r"\\\1", raw)


def inline_code(text: object) -> str:
    raw = "" if text is None else str(text)
    safe = raw.replace("\\", "\\\\").replace("`", "\\`")
    return f"`{safe}`"


def code_block(text: object) -> str:
    raw = "" if text is None else str(text)
    safe = raw.replace("\\", "\\\\").replace("`", "\\`")
    return f"```text\n{safe}\n```"


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
        input_field_placeholder="Ask Gemini anything...",
    )


def settings_keyboard(user: UserSettings) -> InlineKeyboardMarkup:
    concise_status = "✅ Concise" if user.concise_mode else "⬜ Concise"
    rich_status = "✅ Rich UI" if user.rich_ui else "⬜ Rich UI"

    keyboard = [
