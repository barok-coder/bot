from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import Response
from telegram import Update
import os

from src.handlers import telegram_app, settings

# 1. Use an async lifecycle to initialize and cleanly close the Telegram application
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Set up the webhook target address pointing to your unique Render Web URL
    # Replace with your actual Render URL or use an environment variable
    RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://your-bot-subdomain.onrender.com")
    webhook_url = f"{RENDER_URL}/telegram-webhook"
    
    await telegram_app.initialize()
    await telegram_app.updater.set_webhook(url=webhook_url)
    await telegram_app.start()
    yield
    # Clean shutdown handling when Render cycles containers
    await telegram_app.updater.delete_webhook()
    await telegram_app.stop()
    await telegram_app.shutdown()

app = FastAPI(lifespan=lifespan)

# 2. Endpoint to receive incoming binary payload updates pushed from Telegram
@app.post("/telegram-webhook")
async def handle_webhook(request: Request):
    try:
        payload = await request.json()
        update = Update.de_json(payload, telegram_app.bot)
        await telegram_app.process_update(update)
        return Response(status_code=status.HTTP_200_OK)
    except Exception as e:
        # Prevents Telegram from spamming retries if an update crashes internally
        return Response(status_code=status.HTTP_200_OK)

@app.get("/healthz")
async def health_check():
    return {"status": "healthy"}
