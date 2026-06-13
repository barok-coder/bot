from telegram.ext import Application, CommandHandler, MessageHandler, filters
from src.config import TELEGRAM_BOT_TOKEN, logger
from src.database import init_db
from src.handlers import start_command, reset_command, language_command, handle_message

def main():
    logger.info("Initializing database...")
    init_db()

    logger.info("Building Telegram application...")
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler(["start", "star"], start_command))
    app.add_handler(CommandHandler(["reset", "reseat"], reset_command))
    app.add_handler(CommandHandler("language", language_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Polling loop activated successfully. Bot is running!")
    app.run_polling()

if __name__ == '__main__':
    main()