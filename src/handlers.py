# src/handlers.py
from telegram import Update
from telegram.ext import ContextTypes
from google import genai
from google.genai import types
from src.config import GEMINI_API_KEY, logger
from src.database import add_user

client = genai.Client(api_key=GEMINI_API_KEY)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    add_user(update.effective_user.id)
    await update.message.reply_text("💠 *Hybrid Assistant Online*")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=update.message.text
        )
        
        ui_card = (
            f"💠 *Gemini | Hybrid Assistant*\n"
            f"━━━━━━━━━━━━━━━━━━\n\n{response.text}\n\n"
            f"━━━━━━━━━━━━━━━━━━\n✨ _System: `Active`_"
        )
        await update.message.reply_text(ui_card, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"API Error: {e}")
        await update.message.reply_text("⚠️ *System Error*")
