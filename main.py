import os
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from src.handlers import start_command, handle_message, reset_command
from src.database import init_db

# የAPI Key እና Token ከRender Environment variable ይወሰዳሉ
TOKEN = os.environ.get("TELEGRAM_TOKEN")

if __name__ == "__main__":
    init_db() # Database መጀመር
    
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Commands
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("reset", reset_command))
    
    # Messages
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    # Bot-ውን ማስጀመር (Polling mode for Render)
    print("Bot is running on Render...")
    app.run_polling()
