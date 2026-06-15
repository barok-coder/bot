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
    Manages the ecosystem lifecycle. Registers webhooks when the Render 
    container spins up and cleans up hooks when cycling states.
    """
    # Fetch Render's automatically injected public URL path string
    render_url = os.environ.get("RENDER_EXTERNAL_URL")
    
    if not render_url:
        logger.error("CRITICAL: RENDER_EXTERNAL_URL environment variable is missing!")
        render_url = "https://your-custom-app-subdomain.onrender.com"
        
    webhook_target = f"{render_url.rstrip('/')}/telegram-webhook"
    logger.info(f"Establishing primary connection route at: {webhook_target}")

    # Initialize components inside the active event loop
    await telegram_app.initialize()
    
    # Establish the webhook directly on Telegram's servers
    await telegram_app.bot.set_webhook(url=webhook_target, drop_pending_updates=True)
    
    # Start the application instance context loop
    await telegram_app.start()
    
    logger.info("Bot ecosystem routing verified. Event pipeline active.")
    yield
    
    # Tear down pipelines gracefully on host termination signals
    logger.info("Disconnecting webhook channels...")
    await telegram_app.stop()
    await telegram_app.shutdown()


# Initialize the primary FastAPI routing instance using the explicit lifecycle hook
app = FastAPI(lifespan=lifespan)


@app.post("/telegram-webhook")
async def handle_telegram_updates(request: Request):
    """
    Listens directly to incoming POST update matrices from Telegram servers.
    """
    try:
        payload = await request.json()
        
        # Coerce raw dictionary blocks into an explicit, structured Update profile
        update = Update.de_json(data=payload, bot=telegram_app.bot)
        
        # DEFINITIVE V20+ FIX: Push directly to the native framework update queue
        await telegram_app.update_queue.put(update)
        
    except Exception as err:
        logger.error(f"Error handling incoming update payload matrix: {err}")
        
    # Always send a 200 OK block back immediately so Telegram stops spamming retries
    return Response(status_code=status.HTTP_200_OK)


@app.get("/")
@app.get("/healthz")
async def server_health_check():
    """
    Keeps Render's automated platform monitoring systems green.
    """
    return {"status": "operational", "engine": "FastAPI + Gemini Bot Core"}
