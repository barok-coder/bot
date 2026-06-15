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
