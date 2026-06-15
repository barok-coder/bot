import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from telegram import Update
from src.handlers import telegram_app, settings  # ensure settings is imported

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialize and start the application locally
    await telegram_app.initialize()
    await telegram_app.start()
    
    # 2. Set the Webhook URL so Telegram knows where to send updates
    # Ensure your RENDER_EXTERNAL_URL environment variable is set in the Render dashboard
    webhook_url = f"{settings.render_url}/webhook" 
    logger.info(f"Setting webhook to: {webhook_url}")
    
    await telegram_app.bot.set_webhook(url=webhook_url)
    
    yield
    
    # 3. Clean up on shutdown
    await telegram_app.bot.delete_webhook()
    await telegram_app.stop()
    await telegram_app.shutdown()

app = FastAPI(lifespan=lifespan)

# 4. THIS ROUTE RECEIVES THE MESSAGES FROM TELEGRAM
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
