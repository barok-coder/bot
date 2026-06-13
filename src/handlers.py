from telegram import Update
from telegram.ext import ContextTypes
from google import genai
from google.genai import types
from src.config import GEMINI_API_KEY, logger
from src.database import add_user # Ensure this exists now!

client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_INSTRUCTION = (
    "You are a professional, structured AI assistant. "
    "Always use clear, bold headings for sections, use bullet points for lists, "
    "and use code blocks for any technical expressions. "
    "Keep your explanations concise and well-organized."
)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    add_user(update.effective_user.id)
    await update.message.reply_text("💠 *Hybrid Assistant Online*")

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 *Memory reset.*")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    try:
        # gemini-2.5-flash is the stable production model as of June 2026
        response = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=update.message.text,
            config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION)
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
