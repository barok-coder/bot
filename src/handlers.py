from telegram import Update
from telegram.ext import ContextTypes
from google import genai
from src.config import GEMINI_API_KEY, logger
from src.database import add_user

# Initialize the official Gemini SDK Client
try:
    ai_client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    logger.error(f"Failed to initialize Gemini Client: {e}")
    ai_client = None

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /start command."""
    user = update.effective_user
    add_user(user.id, user.username, user.first_name)
    
    welcome_text = (
        f"Hi {user.first_name}! 👋\n\n"
        "I am an intelligent assistant powered by Google's Gemini LLM. "
        "Send me any text message or question, and I'll think up a response for you!"
    )
    await update.message.reply_text(welcome_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Routes incoming text messages to Gemini and replies with the generated answer."""
    user_text = update.message.text
    user = update.effective_user
    
    # Ensure user is stored
    add_user(user.id, user.username, user.first_name)
    
    if not ai_client:
        await update.message.reply_text("System Error: Gemini API client is not configured properly.")
        return

    # Send a typing indicator while processing
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        # Request generation using the standard flash model
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_text,
        )
        
        if response.text:
            await update.message.reply_text(response.text)
        else:
            await update.message.reply_text("I processed that, but couldn't generate a text response.")
            
    except Exception as e:
        logger.error(f"Gemini generation exception: {e}")
        await update.message.reply_text("Sorry, I ran into an error processing your prompt. Please try again.")
