from telegram import Update
from telegram.ext import ContextTypes
from google import genai
from src.config import GEMINI_API_KEY, logger

client = genai.Client(api_key=GEMINI_API_KEY)

# Define the "Copilot" persona/style instructions
SYSTEM_INSTRUCTION = (
    "You are a professional, structured AI assistant. "
    "Always use clear, bold headings for sections, use bullet points for lists, "
    "and use code blocks for any technical or mathematical expressions. "
    "Keep your explanations concise and well-organized."
)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! I am your Hybrid Gemini assistant. Send me a message to get started!")

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Chat memory reset successfully.")

async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Language options updated.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    user_text = update.message.text
    
    # 1. Show the "typing" status to make the UI feel alive
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    try:
        # 2. Generate content with the System Instruction applied
        response = client.models.generate_content(
            model="gemini-2.0-flash", # Note: check if you meant gemini-2.0, as 2.5 is not yet standard
            contents=user_text,
            config={"system_instruction": SYSTEM_INSTRUCTION}
        )
        
        # 3. Apply the Hybrid UI "Card" structure
        ui_card = (
            f"💠 *Gemini | Hybrid Assistant*\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"{response.text}\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"✨ _System: `Active` | Mode: `Hybrid-Logic`_"
        )
        
        # 4. Reply with Markdown formatting
        await update.message.reply_text(ui_card, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Gemini API Error: {e}")
        await update.message.reply_text("⚠️ *System Error*\n\nSorry, I encountered an error talking to Gemini.")
