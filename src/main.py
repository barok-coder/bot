from contextlib import asynccontextmanager
from fastapi import FastAPI
# Import your telegram application variable from handlers
from src.handlers import telegram_app 

@asynccontextmanager
async def lifespan(app: FastAPI):
    # This initializes your bot on web service startup
    await telegram_app.initialize()
    await telegram_app.start()
    
    yield
    
    await telegram_app.stop()
    await telegram_app.shutdown()

# Initialize the application instance here directly
app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {"status": "running"}

# Add your webhook or other FastAPI routes below...
