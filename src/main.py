import os
import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, status
from telegram import Update

from src.handlers import telegram_app, settings

logger = logging.getLogger("telegram_gemini_bot.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the web application lifecycle. Initializes concurrent workers,
    establishes secure webhook targets, and triggers clean runtime teardowns.
    """
    render_url = os.environ.get("RENDER_EXTERNAL_URL")
    if not render_url:
        logger.error("CRITICAL: RENDER_EXTERNAL_URL environment variable is missing!")
        render_url = "https://gemini-telegram-bot-3ekp.onrender.com"
        
    webhook_target = f"{render_url.rstrip('/')}/telegram-webhook"
    logger.info(f"Establishing primary connection route at: {webhook_target}")

    # 1. Initialize components inside the running ASGI event loop
    await telegram_app.initialize()
    
    # 2. Establish the webhook directly on Telegram's servers
    await telegram_app.bot.set_webhook(url=webhook_target, drop_pending_updates=True)
    
    # 3. Start the core application engine infrastructure
    await telegram_app.start()
    
    # 4. DEFINITIVE WORKER FIX: Spin up the internal concurrent execution pool tasks
    # This instructs python-telegram-bot to start processing updates pushed to the queue!
    await telegram_app.updater.start_polling() if telegram_app.updater else None
    # If using standard custom build queue architecture:
    asyncio.create_task(telegram_app.start_execution_pool()) if hasattr(telegram_app, 'start_execution_pool') else None

    logger.info("Bot execution pool initialized. Background tasks active.")
    yield
    
    # Tear down pipelines gracefully on container cycling signals
    logger.info("Disconnecting webhook channels and shutting down task threads...")
    await telegram_app.stop()
    await telegram_app.shutdown()


# Initialize the primary FastAPI routing instance
app = FastAPI(lifespan=lifespan)


@app.post("/telegram-webhook")
async def handle_telegram_updates(request: Request):
    """
    Listens directly to incoming POST update matrices from Telegram servers.
    """
    try:
        payload = await request.json()
        
        # Coerce raw dictionary blocks into a structured Update profile
        update = Update.de_json(data=payload, bot=telegram_app.bot)
        
        # Safely deposit the object into the background task execution queue
        await telegram_app.update_queue.put(update)
        
    except Exception as err:
        logger.error(f"Error handling incoming update payload matrix: {err}")
        
    # Always send a 200 OK block back immediately so Telegram knows the receipt is secured
    return Response(status_code=status.HTTP_200_OK)


@app.get("/")
@app.get("/healthz")
async def server_health_check():
    """
    Keeps Render's automated platform monitoring systems green.
    """
    return {"status": "operational", "engine": "FastAPI + Gemini Bot Core"}
