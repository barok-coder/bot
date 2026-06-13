from telegram import Update
from telegram.ext import ContextTypes
from google import genai
from google.genai import types
from src.config import GEMINI_API_KEY, logger

# Initialize the Gemini Client
client = genai.Client(api_key=GEMINI_API_KEY)

# Define the Copilot-style persona
SYSTEM_INSTRUCTION = (
    "You are a professional, structured AI assistant. "
    "Always use clear, bold headings for sections, use bullet points for lists, "
    "and use code blocks for any technical or mathematical expressions. "
    "Keep your explanations concise and well-organized."
)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("I'm mintu's Assistant Online thanks to him! \n\nI am ready. Send me a message to begin.")

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 Memory reset successfully.")

async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🌐 Language settings updated.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    user_text = update.message.text
    
    # Typing action for professional feel
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    try:
        # Use gemini-1.5-flash for Free Tier reliability
        response = client.models.generate_content(
            model="gemini-1.5-flash", 
            contents=user_text,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION
            )
        )
        
        # Hybrid UI Card Structure
        ui_card = (
            f"💠 *Gemini | Hybrid Assistant*\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"{response.text}\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"✨ _System: `Active` | Model: `gemini-1.5-flash`_"
        )
        
        await update.message.reply_text(ui_card, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Gemini API Error: {e}")
        # Notify user if the free quota is hit
        if "429" in str(e):
            await update.message.reply_text("⚠️ *Rate Limit Exceeded*\n\nThe free tier quota is full. Please try again in a few minutes.")
        else:
            await update.message.reply_text("⚠️ *System Error*\n\nUnable to process. Please check the logs.")
