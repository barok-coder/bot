import logging
import asyncio
import sys
from telegram.ext import Application

from src.handlers import telegram_app, register_handlers

# Configure clear logging output directly into Render's console panel
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger("telegram_gemini_bot.main")

def main():
    """
    Main execution pipeline running as a continuous background worker.
    Bypasses port binding rules and connects directly using long polling.
    """
    try:
        logger.info("Initializing background worker engine...")
        
        # 1. Force clear any lingering webhook channels on Telegram's core servers
        logger.info("Flushing legacy webhook routes from cloud instances...")
        asyncio.run(telegram_app.bot.delete_webhook(drop_pending_updates=True))
        
        # 2. Run the native long polling execution loop block
        logger.info("Ecosystem initialized successfully. Polling channel is now LIVE 🎉")
        
        # This blocks execution and maintains an open connection channel permanently
        telegram_app.run_polling(close_loop=False)
        
    except Exception as err:
        logger.critical(f"Fatal crash inside background process runtime loop: {err}")
        sys.exit(1)

if __name__ == "__main__":
    main()
