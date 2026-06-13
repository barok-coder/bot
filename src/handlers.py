from telegram import Update
from telegram.ext import ContextTypes
from google import genai
from google.genai import types  # <--- Essential import for the new SDK
from src.config import GEMINI_API_KEY, logger

client = genai.Client(api_key=GEMINI_API_KEY)

# Define the persona
SYSTEM_INSTRUCTION = (
    "You are a professional, structured AI assistant. "
    "Always use clear, bold headings for sections, use bullet points for lists, "
    "and use code blocks for any technical or mathematical expressions. "
    "Keep your explanations concise and well-organized."
)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    user_text = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    try:
        # Use the correct types.GenerateContentConfig for the new SDK
        response = client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=user_text,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION
            )
        )
        
        # UI Card Wrapper
        ui_card = (
            f"💠 *Gemini | Hybrid Assistant*\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"{response.text}\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"✨ _System: `Active` | Mode: `Hybrid-Logic`_"
        )
        
        await update.message.reply_text(ui_card, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Gemini API Error details: {e}") # This will show the real error
        await update.message.reply_text("⚠️ *System Error*\n\nUnable to process. Please check the logs.")
