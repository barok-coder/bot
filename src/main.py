import os
import logging
from contextlib import asynccontextmanager  # <--- ADD THIS LINE HERE
from fastapi import FastAPI, Request, Response
from telegram import Update
from src.handlers import telegram_app, settings

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await telegram_app.initialize()
    await telegram_app.start()
    
    render_external_url = os.environ.get("RENDER_EXTERNAL_URL")
    if not render_external_url:
        render_external_url = getattr(settings, "webhook_url", "https://your-bot-fallback.onrender.com")

    webhook_url = f"{render_external_url}/webhook" 
    logger.info(f"Setting webhook to: {webhook_url}")
    
    await telegram_app.bot.set_webhook(url=webhook_url)
    
    yield
    
    await telegram_app.bot.delete_webhook()
    await telegram_app.stop()
    await telegram_app.shutdown()

app = FastAPI(lifespan=lifespan)

@app.post("/webhook")
async def webhook_handler(request: Request):
    try:
        data = await request.json()
        update = Update.de_json(data, telegram_app.bot)
        await telegram_app.process_update(update)
    except Exception as e:
        logger.error(f"Error processing update: {e}")
    return Response(status_code=200)

@app.get("/")
async def root():
    return {"status": "healthy"}
