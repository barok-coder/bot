import os
import logging

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Direct token configuration
TELEGRAM_BOT_TOKEN = "8695539966:AAFe_MBIiB8gSeeOoEvOVujQJHn5Fm3_rtA"
GEMINI_API_KEY = "AQ.Ab8RN6K9WLGdsvbF5cNW4ulrHjB8TQ-EwqtOjGDI0ic6blsf6w"

PORT = int(os.getenv("PORT", "8080"))
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")
DAILY_TOKEN_LIMIT = 1000

DB_DIR = "./data"
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "bot_user_data.db")