import os  # Make sure to import os at the top of your file

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialize and start the application locally
    await telegram_app.initialize()
    await telegram_app.start()
    
    # 2. Pull the URL directly from Render's environment variables
    render_external_url = os.environ.get("RENDER_EXTERNAL_URL")
    
    if not render_external_url:
        logger.error("RENDER_EXTERNAL_URL environment variable is missing!")
        # Fallback just in case you named it something else manually
        render_external_url = getattr(settings, "webhook_url", "https://your-bot-fallback.onrender.com")

    webhook_url = f"{render_external_url}/webhook" 
    logger.info(f"Setting webhook to: {webhook_url}")
    
    await telegram_app.bot.set_webhook(url=webhook_url)
    
    yield
    
    # 3. Clean up on shutdown
    await telegram_app.bot.delete_webhook()
    await telegram_app.stop()
    await telegram_app.shutdown()
