from contextlib import asynccontextmanager
from fastapi import FastAPI

# 1. IMPORT the telegram_app we defined in your handlers file
# (Adjust the path if your handlers code is in a file named handlers.py)
from src.handlers import telegram_app  

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 2. This will now work perfectly because it's imported above!
    await telegram_app.initialize()
    await telegram_app.start()
    
    yield
    
    await telegram_app.stop()
    await telegram_app.shutdown()

app = FastAPI(lifespan=lifespan)

# Rest of your FastAPI routes (like webhooks) go below...
