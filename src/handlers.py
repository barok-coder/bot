async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    user_text = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    try:
        # Use 'gemini-2.0-flash' which is the current standard. 
        # If this still gives 404, the model might need to be 'gemini-2.0-flash-001'
        response = client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=user_text,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION
            )
        )
        
        ui_card = (
            f"💠Gemini | Mintu's Assistant\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"{response.text}\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"✨ _System: `Active` | Model: `gemini-2.0-flash`_"
        )
        
        await update.message.reply_text(ui_card, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Gemini API Error: {e}")
        # If it's still 404, this log will tell us exactly what the API thinks is available
        await update.message.reply_text("⚠️ *System Error*\n\nPlease check the Render logs for the exact model name required.")
