import os
import asyncio
import threading
from aiohttp import web
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from src.handlers import start_command, handle_message, reset_command
from src.database import init_db

# --- Dummy Web Server to satisfy Render Free Tier ---
async def handle(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.add_routes([web.get('/', handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    # Render provides the PORT in an environment variable
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

def run_web_server():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_web_server())
    loop.run_forever()

# --- Main Bot Logic ---
if __name__ == "__main__":
    # Start the dummy web server in a separate thread
    threading.Thread(target=run_web_server, daemon=True).start()
    
    init_db()
    app = ApplicationBuilder().token(os.environ.get("TELEGRAM_TOKEN")).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("reset", reset_command))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("Bot is running...")
    app.run_polling()
