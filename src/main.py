import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Header, HTTPException, Request
from telegram import Update

try:
    from .config import settings
    from .handlers import telegram_app
except ImportError:
    from config import settings
    from handlers import telegram_app


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=settings.log_level,
)
logger = logging.getLogger("telegram_gemini_bot")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await telegram_app.initialize()
    await telegram_app.start()

    if settings.webhook_url:
        await telegram_app.bot.set_webhook(
            url=settings.webhook_endpoint(),
            secret_token=settings.webhook_secret or None,
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
        )
        logger.info("Telegram webhook set to %s", settings.webhook_endpoint())
    else:
        logger.warning("WEBHOOK_URL is not set. Telegram will not receive updates.")

    try:
        yield
    finally:
        if settings.webhook_url and settings.delete_webhook_on_shutdown:
            await telegram_app.bot.delete_webhook(drop_pending_updates=False)
        await telegram_app.stop()
        await telegram_app.shutdown()


api = FastAPI(title="Telegram Gemini Bot", lifespan=lifespan)


@api.get("/")
async def root():
    return {
        "status": "ok",
        "service": "telegram-gemini-bot",
        "mode": "webhook",
        "health": "/health",
    }


@api.get("/health")
async def health():
    return {
        "status": "healthy",
        "telegram": "ready",
        "gemini_model": settings.gemini_model,
    }


@api.post(settings.normalized_webhook_path())
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
):
    if settings.webhook_secret and x_telegram_bot_api_secret_token != settings.webhook_secret:
        raise HTTPException(status_code=403, detail="Invalid webhook secret.")

    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True}


if __name__ == "__main__":
    uvicorn.run(api, host="0.0.0.0", port=settings.port)
