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

E_BRAIN = "\U0001f9e0"
E_GEAR = "\u2699\ufe0f"
E_SCROLL = "\U0001f4dc"
E_CHART = "\U0001f4ca"
E_FIRE = "\U0001f525"
E_SCALE = "\u2696\ufe0f"
E_TARGET = "\U0001f3af"
E_CHECK = "\u2705"
E_BOX = "\u2b1c"
E_BROOM = "\U0001f9f9"
E_ROCKET = "\U0001f680"
E_SPARK = "\u26a1"
E_SCISSORS = "\u2702\ufe0f"
E_STARS = "\u2728"
E_CHAT = "\U0001f4ac"
E_DIAMOND_BLUE = "\U0001f539"
E_DIAMOND_ORANGE = "\U0001f538"
E_SEARCH = "\U0001f50d"
E_TOOLS = "\U0001f6e0\ufe0f"
E_TEMP = "\U0001f321\ufe0f"
E_BULLET = "\u2022"

MENU_ASK = f"{E_BRAIN} Ask Gemini AI"
MENU_SETTINGS = f"{E_GEAR} Bot Settings"
MENU_GUIDE = f"{E_SCROLL} Feature Guide"
MENU_TOKENS = f"{E_CHART} Token Status"
DIVIDER = "\u2500" * 15


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
    concise_status = f"{E_CHECK} Concise" if user.concise_mode else f"{E_BOX} Concise"
    rich_status = f"{E_CHECK} Rich UI" if user.rich_ui else f"{E_BOX} Rich UI"

    keyboard = list()
    keyboard.append(
        [
            InlineKeyboardButton(f"{E_FIRE} Creative", callback_data="temp:creative"),
            InlineKeyboardButton(f"{E_SCALE} Balanced", callback_data="temp:balanced"),
            InlineKeyboardButton(f"{E_TARGET} Precise", callback_data="temp:precise"),
        ]
    )
    keyboard.append(
        [
            InlineKeyboardButton(concise_status, callback_data="toggle:concise"),
            InlineKeyboardButton(rich_status, callback_data="toggle:rich_ui"),
        ]
    )
    keyboard.append(
        [InlineKeyboardButton(f"{E_BROOM} Reset Memory", callback_data="memory:reset")]
    )

    return InlineKeyboardMarkup(keyboard)


def guide_keyboard() -> InlineKeyboardMarkup:
    keyboard = list()
    keyboard.append(
        [
            InlineKeyboardButton(f"{E_GEAR} Open Settings", callback_data="open:settings"),
            InlineKeyboardButton(f"{E_CHART} Token Status", callback_data="open:tokens"),
        ]
    )
    keyboard.append(
        [
            InlineKeyboardButton(f"{E_FIRE} Creative Mode", callback_data="temp:creative"),
            InlineKeyboardButton(f"{E_TARGET} Precise Mode", callback_data="temp:precise"),
        ]
    )

    return InlineKeyboardMarkup(keyboard)


def format_header(title: str, subtitle: str | None = None) -> str:
    lines = [f"*{escape_md(title)}*", escape_md(DIVIDER)]
    if subtitle:
        lines.append(escape_md(subtitle))
    return "\n".join(lines)


def welcome_text(first_name: str | None) -> str:
    name = first_name or "there"
    return "\n".join(
        [
            format_header(f"{E_ROCKET} Gemini AI Bot", f"Welcome, {name}."),
            "",
            escape_md("A vibrant Telegram assistant powered by Google AI."),
            "",
            f"{E_BRAIN} *Ask smart questions*",
            f"{E_GEAR} *Tune response style*",
            f"{E_SCROLL} *Explore interactive features*",
            f"{E_CHART} *Track session token usage*",
            "",
            escape_md("Use the menu below to begin."),
        ]
    )


def settings_text(user: UserSettings) -> str:
    return "\n".join(
        [
            format_header(f"{E_GEAR} Bot Settings", "Tune how Gemini responds in this chat."),
            "",
            f"{E_BRAIN} *Model:* {inline_code(settings.gemini_model)}",
            f"{E_TEMP} *Temperature:* {inline_code(user.temperature)} \\({escape_md(user.temperature_label)}\\)",
            f"{E_SCISSORS} *Concise Mode:* {inline_code('On' if user.concise_mode else 'Off')}",
            f"{E_STARS} *Rich UI:* {inline_code('On' if user.rich_ui else 'Off')}",
            "",
            escape_md("Use the buttons below to update your experience instantly."),
        ]
    )


def guide_text() -> str:
    return "\n".join(
        [
            format_header(f"{E_SCROLL} Feature Guide", "Your premium Gemini control center."),
            "",
            f"{E_BRAIN} *Ask Gemini AI*",
            escape_md("Send any question, idea, draft, code issue, or study topic."),
            "",
            f"{E_GEAR} *Bot Settings*",
            escape_md("Switch between creative, balanced, and precise response styles."),
            "",
            f"{E_CHART} *Token Status*",
            escape_md("See your approximate Gemini token usage for this bot session."),
            "",
            f"{E_CHAT} *Quick Tip*",
            code_block("Explain this like I am new to it: async webhooks in Telegram bots"),
        ]
    )


def token_status_text(user: UserSettings) -> str:
    return "\n".join(
        [
            format_header(f"{E_CHART} Token Status", "Approximate usage for this live bot session."),
            "",
            f"{E_DIAMOND_BLUE} *Prompt Tokens:* {inline_code(user.prompt_tokens)}",
            f"{E_DIAMOND_ORANGE} *Response Tokens:* {inline_code(user.response_tokens)}",
            f"{E_SPARK} *Total Tokens:* {inline_code(user.total_tokens)}",
            "",
            escape_md("Usage resets when the Render service restarts on the free plan."),
        ]
    )


def prompt_for_question_text(user: UserSettings) -> str:
    return "\n".join(
        [
            format_header(f"{E_BRAIN} Ask Gemini AI", "Send your question in the next message."),
            "",
            f"{E_SPARK} *Current Mode:* {inline_code(user.temperature_label)}",
            f"{E_SCISSORS} *Concise:* {inline_code('On' if user.concise_mode else 'Off')}",
            "",
            escape_md("Try: Build me a 7-day learning plan for Python webhooks."),
        ]
    )


def build_prompt(chat_id: int, user_text: str) -> str:
    user = db.get_user(chat_id)
    style_note = (
