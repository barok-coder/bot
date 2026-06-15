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

    if user.concise_mode:
        style_note = "Keep the answer tight and practical."
    else:
        style_note = "Use helpful detail and clean structure."

    history_lines = []
    recent_history = list(user.history)[-settings.max_history_messages :]
    for item in recent_history:
        history_lines.append(f"{item['role'].upper()}: {item['text']}")

    history_text = "\n".join(history_lines) or "No previous messages."

    prompt_parts = []
    prompt_parts.append(settings.system_prompt)
    prompt_parts.append("")
    prompt_parts.append(f"Response style: {user.temperature_label}. {style_note}")
    prompt_parts.append("")
    prompt_parts.append(f"Conversation so far:\n{history_text}")
    prompt_parts.append("")
    prompt_parts.append(f"User message:\n{user_text}")
    return "\n".join(prompt_parts)


def update_token_usage(chat_id: int, usage_metadata: object) -> None:
    prompt_tokens = int(getattr(usage_metadata, "prompt_token_count", 0) or 0)
    response_tokens = int(getattr(usage_metadata, "candidates_token_count", 0) or 0)
    total_tokens = int(getattr(usage_metadata, "total_token_count", 0) or 0)
    db.add_token_usage(chat_id, prompt_tokens, response_tokens, total_tokens)


async def ask_gemini(chat_id: int, user_text: str) -> str:
    user = db.get_user(chat_id)
    response = await gemini_client.aio.models.generate_content(
        model=settings.gemini_model,
        contents=build_prompt(chat_id, user_text),
        config=types.GenerateContentConfig(
            temperature=user.temperature,
            max_output_tokens=settings.max_output_tokens,
        ),
    )

    answer = (response.text or "").strip()
    if not answer:
        answer = "I could not generate a response this time. Please try again."

    usage_metadata = getattr(response, "usage_metadata", None)
    if usage_metadata:
        update_token_usage(chat_id, usage_metadata)

    db.add_exchange(chat_id, user_text, answer)
    return answer

def format_ai_response(answer: str, user: UserSettings) -> str:
    if not user.rich_ui:
        return escape_md(answer)

    return "\n".join(
        [
            f"*{E_BRAIN} Gemini Response*",
            escape_md(DIVIDER),
            escape_md(answer),
            "",
            escape_md(DIVIDER),
            f"{E_GEAR} *Mode:* {inline_code(user.temperature_label)}  {E_BULLET}  "
            f"{E_SPARK} *Tokens:* {inline_code(user.total_tokens)}",
        ]
    )


async def safe_edit_text(message, text: str, reply_markup=None) -> None:
    chunks = split_message(text)
    await message.edit_text(
        chunks[0],
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=reply_markup,
        disable_web_page_preview=True,
    )

    for chunk in chunks[1:]:
        await message.reply_text(
            chunk,
            parse_mode=ParseMode.MARKDOWN_V2,
            disable_web_page_preview=True,
        )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    first_name = update.effective_user.first_name if update.effective_user else None
    await update.message.reply_text(
        welcome_text(first_name),
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=main_menu(),
        disable_web_page_preview=True,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        guide_text(),
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=guide_keyboard(),
        disable_web_page_preview=True,
    )


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db.clear_history(update.effective_chat.id)
    await update.message.reply_text(
        "\n".join(
            [
                format_header(f"{E_BROOM} Memory Reset", "This chat history is now clean."),
                "",
                escape_md("Send a fresh question whenever you are ready."),
            ]
        ),
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=main_menu(),
    )


async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = db.get_user(update.effective_chat.id)
    await update.message.reply_text(
        settings_text(user),
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=settings_keyboard(user),
        disable_web_page_preview=True,
    )


async def show_guide(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        guide_text(),
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=guide_keyboard(),
        disable_web_page_preview=True,
    )


async def show_tokens(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = db.get_user(update.effective_chat.id)
    await update.message.reply_text(
        token_status_text(user),
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(f"{E_GEAR} Open Settings", callback_data="open:settings")]]
        ),
    )

    return answer


def format_ai_response(answer: str, user: UserSettings) -> str:
    if not user.rich_ui:
        return escape_md(answer)

    return "\n".join(
        [
            f"*{E_BRAIN} Gemini Response*",
            escape_md(DIVIDER),
            escape_md(answer),
            "",
            escape_md(DIVIDER),
            f"{E_GEAR} *Mode:* {inline_code(user.temperature_label)}  {E_BULLET}  "
            f"{E_SPARK} *Tokens:* {inline_code(user.total_tokens)}",
        ]
    )


async def safe_edit_text(message, text: str, reply_markup=None) -> None:
    chunks = split_message(text)
    await message.edit_text(
        chunks[0],
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=reply_markup,
        disable_web_page_preview=True,
    )

    for chunk in chunks[1:]:
        await message.reply_text(
            chunk,
            parse_mode=ParseMode.MARKDOWN_V2,
            disable_web_page_preview=True,
        )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    first_name = update.effective_user.first_name if update.effective_user else None
    await update.message.reply_text(
        welcome_text(first_name),
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=main_menu(),
        disable_web_page_preview=True,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        guide_text(),
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=guide_keyboard(),
        disable_web_page_preview=True,
    )


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db.clear_history(update.effective_chat.id)
    await update.message.reply_text(
        "\n".join(
            [
                format_header(f"{E_BROOM} Memory Reset", "This chat history is now clean."),
                "",
                escape_md("Send a fresh question whenever you are ready."),
            ]
        ),
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=main_menu(),
    )


async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = db.get_user(update.effective_chat.id)
    await update.message.reply_text(
        settings_text(user),
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=settings_keyboard(user),
        disable_web_page_preview=True,
    )


async def show_guide(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        guide_text(),
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=guide_keyboard(),
        disable_web_page_preview=True,
    )


async def show_tokens(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = db.get_user(update.effective_chat.id)
    await update.message.reply_text(
        token_status_text(user),
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(f"{E_GEAR} Open Settings", callback_data="open:settings")]]
        ),
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    user = db.get_user(chat_id)
    data = query.data

    if data == "temp:creative":
        user.temperature = 0.95
        user.temperature_label = "Creative"
        text = settings_text(user)
        keyboard = settings_keyboard(user)
    elif data == "temp:balanced":
        user.temperature = 0.7
        user.temperature_label = "Balanced"
        text = settings_text(user)
        keyboard = settings_keyboard(user)
    elif data == "temp:precise":
        user.temperature = 0.25
        user.temperature_label = "Precise"
        text = settings_text(user)
        keyboard = settings_keyboard(user)
    elif data == "toggle:concise":
        user.concise_mode = not user.concise_mode
        text = settings_text(user)
        keyboard = settings_keyboard(user)
    elif data == "toggle:rich_ui":
        user.rich_ui = not user.rich_ui
        text = settings_text(user)
        keyboard = settings_keyboard(user)
    elif data == "memory:reset":
        db.clear_history(chat_id)
        text = "\n".join(
            [
                format_header(f"{E_BROOM} Memory Reset", "Conversation memory has been cleared."),
                "",
                escape_md("Your settings stayed exactly the same."),
            ]
        )
        keyboard = settings_keyboard(user)
    elif data == "open:settings":
        text = settings_text(user)
        keyboard = settings_keyboard(user)
    elif data == "open:tokens":
        text = token_status_text(user)
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton(f"{E_GEAR} Open Settings", callback_data="open:settings")]]
        )
    else:
        text = escape_md("Unknown action.")
        keyboard = None

    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=keyboard,
        disable_web_page_preview=True,
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    text = (update.message.text or "").strip()
    user = db.get_user(chat_id)

    if text == MENU_ASK:
        await update.message.reply_text(
            prompt_for_question_text(user),
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=main_menu(),
        )
        return

    if text == MENU_SETTINGS:
        await show_settings(update, context)
        return

    if text == MENU_GUIDE:
        await show_guide(update, context)
        return

    if text == MENU_TOKENS:
        await show_tokens(update, context)
        return

    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    placeholder = await update.message.reply_text(
        f"{E_SPARK} *Thinking\\.\\.\\.*\n"
        f"{escape_md(DIVIDER)}\n"
        f"{E_SEARCH} *Analyzing your request\\.\\.\\.*",
        parse_mode=ParseMode.MARKDOWN_V2,
    )

    try:
        answer = await ask_gemini(chat_id, text)
        await safe_edit_text(placeholder, format_ai_response(answer, user))
    except Exception:
        logger.exception("Failed to generate Gemini response")
        await safe_edit_text(
            placeholder,
            "\n".join(
                [
                    format_header(f"{E_TOOLS} Something Went Wrong", "Gemini could not answer this request."),
                    "",
                    escape_md("Please check your API key, model name, and Render logs, then try again."),
                ]
            ),
        )


def register_handlers() -> None:
    global telegram_app
    if "telegram_app" not in globals():
        telegram_app = Application.builder().token(settings.bot_token).build()

    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("help", help_command))
    telegram_app.add_handler(CommandHandler("reset", reset_command))
    telegram_app.add_handler(CallbackQueryHandler(handle_callback))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))


register_handlers()


def get_telegram_app() -> Application:
    return telegram_app
