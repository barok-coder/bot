import os
import logging

logger = logging.getLogger(__name__)

# Make sure these variable names match exactly what you put in Render
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DB_PATH = "bot_data.db"
