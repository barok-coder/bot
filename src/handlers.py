# src/handlers.py
from telegram import Update
from telegram.ext import ContextTypes
from google import genai
from google.genai import types
from src.config import GEMINI_API_KEY, logger
from src.database import add_user

# Initialize the Gemini client
client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_INSTRUCTION = (
    "You are a helpful AI assistant. "
    "Keep responses structured using clear headings and bullet points. "
    "Avoid using characters that break Markdown like unclosed brackets."
)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    add_user(update.effective_user.id)
    await update.message.reply_text("💠 *Hybrid Assistant Online*")

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 *Memory reset.*")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    try:
        # Generate content from Gemini
        response = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=update.message.text,
            config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION)
        )
        
        # Simple text sanitization to prevent parsing errors
        # We replace Markdown-breaking characters with safe versions
        raw_text = response.text
        clean_text = raw_text.replace('[', '(').replace(']', ')')
        
        ui_card = (
            f"💠 *Gemini Assistant*\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"{clean_text}\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"✨ _Status: Active_"
        )
        
        # We use parse_mode="Markdown" (version 1) 
        # It is much more forgiving than MarkdownV2
        await update.message.reply_text(ui_card, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Handler Error: {e}")
        await update.message.reply_text("⚠️ *System Error: Could not process request.*")
