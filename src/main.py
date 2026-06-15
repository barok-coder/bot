import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, status
from telegram import Update

from src.handlers import telegram_app, settings

logger = logging.getLogger("telegram_gemini_bot.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the application lifecycle. Explicitly initializes the PTB engine
    and tells Telegram where to route live webhook traffic.
    """
    render_url = os.environ.get("RENDER_EXTERNAL_URL")
    if not render_url:
        logger.error("CRITICAL: RENDER_EXTERNAL_URL environment variable is missing!")
        render_url = "https://gemini-telegram-bot-3ekp.onrender.com"
        
    webhook_target = f"{render_url.rstrip('/')}/telegram-webhook"
    logger.info(f"Connecting webhook endpoint at: {webhook_target}")

    # Initialize the basic internal bot engine
    await telegram_app.initialize()
    
    # Secure the webhook mapping on Telegram's servers
    await telegram_app.bot.set_webhook(url=webhook_target, drop_pending_updates=True)
    
    # Spin up the application framework context
    await telegram_app.start()
    
    logger.info("Telegram Bot Webhook Context Fully Online.")
    yield
    
    # Graceful teardown when container scales or cycles
    logger.info("Tearing down webhook structures...")
    await telegram_app.stop()
    await telegram_app.shutdown()


# Spin up the FastAPI server profile
app = FastAPI(lifespan=lifespan)


@app.post("/telegram-webhook")
async def handle_telegram_updates(request: Request):
    """
    Listens directly to incoming POST update matrices from Telegram servers.
    Forces direct synchronous execution without utilizing background concurrent queues.
    """
    try:
        payload = await request.json()
        
        # Coerce the incoming JSON string block into an official structured Update model
        update = Update.de_json(data=payload, bot=telegram_app.bot)
        
        # DEFINITIVE NATIVE FIX: Force direct update execution immediately!
        # This completely skips the background update_queue worker bottleneck.
        await telegram_app.process_update(update)
        
    except Exception as err:
        logger.error(f"Error executing incoming update context matrix: {err}")
        
    # Always send a 200 OK block back immediately so Telegram knows the block arrived safely
    return Response(status_code=status.HTTP_200_OK)


@app.get("/")
@app.get("/healthz")
async def server_health_check():
    """
    Keeps Render's automated architecture health monitors green.
    """
    return {"status": "operational", "engine": "FastAPI + Gemini Bot Engine"}
