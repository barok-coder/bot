import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, status
from telegram import Update

from src.handlers import telegram_app, settings

# Set up clean logging visibility
logger = logging.getLogger("telegram_gemini_bot.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the application lifecycle. Uses python-telegram-bot's
    async context manager to properly power the internal handler execution engine.
    """
    render_url = os.environ.get("RENDER_EXTERNAL_URL")
    if not render_url:
        logger.error("CRITICAL: RENDER_EXTERNAL_URL environment variable is missing!")
        render_url = "https://gemini-telegram-bot-3ekp.onrender.com"
        
    webhook_target = f"{render_url.rstrip('/')}/telegram-webhook"
    logger.info(f"Connecting webhook endpoint at: {webhook_target}")

    # Set up the webhook mapping directly on Telegram's core servers
    await telegram_app.bot.set_webhook(
        url=webhook_target, 
        allowed_updates=Update.ALL_TYPES, 
        drop_pending_updates=True
    )
    
    # OFFICIAL PTB PATTERN: Initialize, start, and run inside the async context manager block
    async with telegram_app:
        await telegram_app.start()
        logger.info("Telegram Bot Webhook Application Runtime Engine Fully Online.")
        yield
        await telegram_app.stop()


# Initialize the primary FastAPI routing server instance
app = FastAPI(lifespan=lifespan)


@app.post("/telegram-webhook")
async def handle_telegram_updates(request: Request):
    """
    Listens directly to incoming POST update matrices from Telegram servers.
    Safely feeds the objects into the shared context execution engine.
    """
    try:
        payload = await request.json()
        
        # Coerce the incoming dictionary payload block into a structured Update object
        update = Update.de_json(data=payload, bot=telegram_app.bot)
        
        # This processes instantly since the "async with telegram_app" context is active
        await telegram_app.process_update(update)
        
    except Exception as err:
        logger.error(f"Error executing incoming update context matrix: {err}")
        
    # Always send a 200 OK block back immediately so Telegram knows the receipt is secured
    return Response(status_code=status.HTTP_200_OK)


@app.get("/")
@app.get("/healthz")
async def server_health_check():
    """
    Keeps Render's automated platform architecture monitoring systems green.
    """
    return {"status": "operational", "engine": "FastAPI + Gemini Bot Engine"}
