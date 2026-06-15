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
    lines = [f"<b>{title.upper()}</b>", DIVIDER]
    if subtitle:
        lines.append(f"<i>{subtitle}</i>")
    return "\n".join(lines)


def welcome_text(first_name: str | None) -> str:
    name = first_name or "User"
    return "\n".join(
        [
            format_header("Gemini AI Core", f"Welcome, {name}."),
            "",
            "A clean, cloud-hosted assistant powered by Google Gemini AI.",
            "",
            "• Submit text queries, images, or document files",
            "• Tune response engines via settings",
            "• Explore documentation guides",
            "• Track session token metadata profiles",
            "",
            "Interact with the terminal menu below or attach media to begin.",
        ]
    )


def settings_text(user: UserSettings) -> str:
    return "\n".join(
        [
            format_header("System Settings", "Configure engine behavioral traits."),
            "",
            f"<b>Engine Model:</b> <code>{settings.gemini_model}</code>",
            f"<b>Temperature:</b> <code>{user.temperature}</code> ({user.temperature_label})",
            f"<b>Concise Mode:</b> <code>{'Enabled' if user.concise_mode else 'Disabled'}</code>",
            f"<b>Rich UI Elements:</b> <code>{'Enabled' if user.rich_ui else 'Disabled'}</code>",
            "",
            "Select an interface option below to update configurations.",
        ]
    )


def guide_text() -> str:
    return "\n".join(
        [
            format_header("Operational Guide", "System control panel documentation."),
            "",
            "<b>Ask Gemini AI</b>",
            "Processes code inquiries, explanations, study modules, or text generation tasks.",
            "",
            "<b>Multimodal Inputs</b>",
            "Send an image or attach a file directly. You can add a caption with your question alongside the attachment.",
            "",
            "<b>Bot Settings</b>",
            "Adjust system creativity indexes: Creative (0.95), Balanced (0.7), or Precise (0.25).",
            "",
            "<b>Token Status</b>",
            "Evaluates structural payload usage for the active runtime instance environment.",
        ]
    )


def token_status_text(user: UserSettings) -> str:
    return "\n".join(
        [
            format_header("Token Payload Diagnostics", "Live runtime performance parameters."),
            "",
            f"<b>Prompt Metrics:</b> <code>{user.prompt_tokens}</code>",
            f"<b>Response Metrics:</b> <code>{user.response_tokens}</code>",
            f"<b>Aggregate Context:</b> <code>{user.total_tokens}</code>",
            "",
            "Note: Payload counters cycle when the hosting container switches states.",
        ]
    )


def prompt_for_question_text(user: UserSettings) -> str:
    return "\n".join(
        [
            format_header("Input Request Mode", "Awaiting query payload entry..."),
            "",
            f"<b>Active Target Engine:</b> <code>{user.temperature_label}</code>",
            f"<b>Compression Protocol:</b> <code>{'Concise' if user.concise_mode else 'Standard'}</code>",
            "",
            "Prototyping Example: Upload a data sheet or query text logic.",
        ]
    )


def build_prompt(chat_id: int, user_text: str) -> str:
    user = db.get_user(chat_id)

    if user.concise_mode:
        style_note = "Keep the answer tight, optimized, and highly practical."
    else:
        style_note = "Use helpful professional details and clear structural organization."

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
    prompt_parts.append(f"User message/caption:\n{user_text}")
    return "\n".join(prompt_parts)


def update_token_usage(chat_id: int, usage_metadata: object) -> None:
    prompt_tokens = int(getattr(usage_metadata, "prompt_token_count", 0) or 0)
    response_tokens = int(getattr(usage_metadata, "candidates_token_count", 0) or 0)
    total_tokens = int(getattr(usage_metadata, "total_token_count", 0) or 0)
    db.add_token_usage(chat_id, prompt_tokens, response_tokens, total_tokens)


async def ask_gemini(chat_id: int, user_text: str, file_path: str | None = None) -> str:
    user = db.get_user(chat_id)
    
    contents = []
    
    # If a media file path exists, load it directly into the contents payload using the GenAI File System API helpers
    if file_path and os.path.exists(file_path):
        try:
            uploaded_file = await gemini_client.aio.files.upload(file=file_path)
            contents.append(uploaded_file)
        except Exception as upload_err:
            logger.error(f"Failed to stream asset payload to Gemini API storage: {upload_err}")

    contents.append(build_prompt(chat_id, user_text))

    response = await gemini_client.aio.models.generate_content(
        model=settings.gemini_model,
        contents=contents,
        config=types.GenerateContentConfig(
            temperature=user.temperature,
            max_output_tokens=1000,
        ),
    )

    # Clean up uploaded cloud file handles if they exist
    if file_path and 'uploaded_file' in locals():
        try:
            await gemini_client.aio.files.delete(name=uploaded_file.name)
        except Exception:
            pass

    answer = (response.text or "").strip()
    if not answer:
        answer = "System failed to generate text output. Please re-verify query params."

    usage_metadata = getattr(response, "usage_metadata", None)
    if usage_metadata:
        update_token_usage(chat_id, usage_metadata)

    db.add_exchange(chat_id, user_text, answer)
    return answer


def format_ai_response(answer: str, user: UserSettings) -> str:
    if not user.rich_ui:
        return answer

    return "\n".join(
        [
            "<b>GENAI RESPONSE ENGINE</b>",
            DIVIDER,
            answer,
            "",
            DIVIDER,
            f"<b>Profile:</b> <code>{user.temperature_label}</code>  |  "
            f"<b>Tokens:</b> <code>{user.total_tokens}</code>",
        ]
    )


async def safe_edit_text(message, text: str, reply_markup=None) -> None:
    chunks = split_message(text)
    try:
        await message.edit_text(
            chunks[0],
            parse_mode="HTML",
            reply_markup=reply_markup,
            disable_web_page_preview=True,
        )
    except Exception:
        await message.edit_text(
            html.escape(chunks[0]),
            parse_mode=None,
            reply_markup=reply_markup,
        )

    for chunk in chunks[1:]:
        try:
            await message.reply_text(
                chunk,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
        except Exception:
            await message.reply_text(html.escape(chunk), parse_mode=None)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    first_name = update.effective_user.first_name if update.effective_user else None
    await update.message.reply_text(
        welcome_text(first_name),
        parse_mode="HTML",
        reply_markup=main_menu(),
        disable_web_page_preview=True,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        guide_text(),
        parse_mode="HTML",
        reply_markup=guide_keyboard(),
        disable_web_page_preview=True,
    )


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db.clear_history(update.effective_chat.id)
    await update.message.reply_text(
        "\n".join(
            [
                format_header("Memory Flush Complete", "Context memory fields cleared clean."),
                "",
                "The system is primed for fresh processing parameters.",
            ]
        ),
        parse_mode="HTML",
        reply_markup=main_menu(),
    )


async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = db.get_user(update.effective_chat.id)
    await update.message.reply_text(
        settings_text(user),
        parse_mode="HTML",
        reply_markup=settings_keyboard(user),
        disable_web_page_preview=True,
    )


async def show_guide(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        guide_text(),
        parse_mode="HTML",
        reply_markup=guide_keyboard(),
        disable_web_page_preview=True,
    )


async def show_tokens(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = db.get_user(update.effective_chat.id)
    await update.message.reply_text(
        token_status_text(user),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Open Settings", callback_data="open:settings")]]
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
                format_header("Context Memory Reset", "Conversation tracking elements cleared."),
                "",
                "System architecture metrics remain unchanged.",
            ]
        )
        keyboard = settings_keyboard(user)
    elif data == "open:settings":
        text = settings_text(user)
        keyboard = settings_keyboard(user)
    elif data == "open:tokens":
        text = token_status_text(user)
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Open Settings", callback_data="open:settings")]]
        )
    else:
        text = "Unknown transaction protocol handling error."
        keyboard = None

    await query.edit_message_text(
        text,
        parse_mode="HTML",
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
            parse_mode="HTML",
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
        f"<b>Processing Query...</b>\n"
        f"{DIVIDER}\n"
        f"<i>Analyzing transaction instructions...</i>",
        parse_mode="HTML",
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
                    format_header("Processing Interrupted", "Core framework could not execute statement."),
                    "",
                    "Review environmental API tokens, configuration parameters, and cluster logging streams.",
                ]
            ),
        )


async def handle_multimodal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Downloads files or photos locally, forwards them to the Gemini API, and returns the analysis."""
    chat_id = update.effective_chat.id
    user = db.get_user(chat_id)
    
    # Grab optional captions attached along with the media, default to a generic analysis string if none provided
    caption = (update.message.caption or "Analyze this file attachment in detail.").strip()
    
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    placeholder = await update.message.reply_text(
        f"<b>Downloading Media Payload...</b>\n"
        f"{DIVIDER}\n"
        f"<i>Streaming binary data blocks to cluster engine...</i>",
        parse_mode="HTML",
    )

    local_path = None
    try:
        # Determine whether input is an explicit file document or a photostream snapshot
        if update.message.document:
            telegram_file = await context.bot.get_file(update.message.document.file_id)
            filename = update.message.document.file_name or "attached_doc"
        elif update.message.photo:
            # Grab the highest resolution copy from the Telegram photostream array
            telegram_file = await context.bot.get_file(update.message.photo[-1].file_id)
            filename = "attached_image.jpg"
        else:
            await safe_edit_text(placeholder, "Unsupported transmission payload format.")
            return

        # Explicitly track target landing file strings inside container runtime temporary folders
        local_path = os.path.join("/tmp", f"{chat_id}_{filename}")
        await telegram_file.download_to_drive(custom_path=local_path)
        
        await placeholder.edit_text(
            f"<b>Processing Multimodal Matrix...</b>\n"
            f"{DIVIDER}\n"
            f"<i>Executing AI neural parsing pass...</i>",
            parse_mode="HTML"
        )
        
        # Forward downloaded system attachment pathways to the Gemini API layer
        answer = await ask_gemini(chat_id, caption, file_path=local_path)
        await safe_edit_text(placeholder, format_ai_response(answer, user))

    except Exception:
        logger.exception("Multimodal transaction routine runtime crash")
        await safe_edit_text(
            placeholder,
            "<b>Processing Interrupted</b>\n"
            "──────────────────────────────\n"
            "Core engine failed to decode media payload blocks cleanly."
        )
    finally:
        # Clean up temporary disk files on Render
        if local_path and os.path.exists(local_path):
            try:
                os.remove(local_path)
            except Exception:
                pass


def register_handlers() -> None:
    global telegram_app
    
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("help", help_command))
    telegram_app.add_handler(CommandHandler("reset", reset_command))
    telegram_app.add_handler(CallbackQueryHandler(handle_callback))
    
    # Catch structural multimedia, snapshots, photos, and general data sheets
    telegram_app.add_handler(
        MessageHandler(filters.PHOTO | filters.Document.ALL, handle_multimodal)
    )
    
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))


register_handlers()


def get_telegram_app() -> Application:
    return telegram_app
