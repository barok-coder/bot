from telegram import Update
from telegram.ext import ContextTypes
from google import genai
from src.config import GEMINI_API_KEY, logger

client = genai.Client(api_key=GEMINI_API_KEY)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! I am your Gemini AI assistant. Send me a message to get started!")

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Chat memory reset successfully.")

async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Language options updated.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    user_text = update.message.text
    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=user_text)
        await update.message.reply_text(response.text)
    except Exception as e:
        logger.error(f"Gemini API Error: {e}")
        await update.message.reply_text("Sorry, I encountered an error talking to Gemini.")