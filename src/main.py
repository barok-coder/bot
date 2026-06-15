import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, status
from telegram import Update

from src.handlers import telegram_app

# Configure clear logging output directly into Render's console panel
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger("telegram_gemini_bot.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the application lifecycle. Sets up the live webhook route 
    mapping target on Telegram's core servers during startup.
    """
    render_url = os.environ.get("RENDER_EXTERNAL_URL")
    if not render_url:
        logger.error("CRITICAL: RENDER_EXTERNAL_URL environment variable is missing!")
        render_url = "https://gemini-telegram-bot-3ekp.onrender.com"
        
    webhook_target = f"{render_url.rstrip('/')}/telegram-webhook"
    logger.info(f"Connecting webhook endpoint at: {webhook_target}")

    # Explicitly clear out old states and link the webhook
    await telegram_app.bot.initialize()
    await telegram_app.bot.set_webhook(
        url=webhook_target, 
        allowed_updates=Update.ALL_TYPES, 
        drop_pending_updates=True
    )
    
    logger.info("Web service interface hook verified. Standing by for incoming payload updates...")
    yield
    
    # Graceful teardown when container scales or cycles
    logger.info("Tearing down web service channels...")
    await telegram_app.bot.shutdown()


# Spin up the primary FastAPI entry point object instance
app = FastAPI(lifespan=lifespan)


@app.post("/telegram-webhook")
async def handle_telegram_updates(request: Request):
    """
    Listens directly to incoming POST update matrices from Telegram servers.
    Forces direct runtime context mapping to eliminate worker deadlocks.
    """
    try:
        payload = await request.json()
        update = Update.de_json(data=payload, bot=telegram_app.bot)
        
        # DEFINITIVE FIX: Open a localized async context state block
        # This forces the underlying aiohttp network pipes open for this request
        async with telegram_app:
            await telegram_app.process_update(update)
            
    except Exception as err:
        logger.error(f"Error executing incoming update context matrix: {err}")
        
    # Always send a 200 OK block back immediately so Telegram stops spamming retries
    return Response(status_code=status.HTTP_200_OK)


@app.get("/")
@app.get("/healthz")
async def server_health_check():
    """
    Keeps Render's automated architecture health monitors green.
    """
    return {"status": "operational", "engine": "FastAPI + Gemini Webhook Engine"}
