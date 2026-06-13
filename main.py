import asyncio
import os
from aiohttp import web
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from src.config import TELEGRAM_BOT_TOKEN, logger
from src.database import init_db
from src.handlers import start_command, handle_message, reset_command
async def handle_ping(request):
    return web.Response(text="Bot is alive and polling!")

async def main():
    # 1. Initialize database
    init_db()

    # 2. Build the Telegram application
    logger.info("Building Telegram application...")
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # 3. Setup Web Server (The crucial part)
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Get port from Render (default to 8080 if not provided)
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"Web server started on port {port}")

    # 4. Start polling
    async with application:
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        logger.info("Polling loop activated successfully. Bot is running!")
        
        # Keep alive
        await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
