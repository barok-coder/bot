import uvicorn

from src.config import settings
from src.main import api


if __name__ == "__main__":
    uvicorn.run(api, host="0.0.0.0", port=settings.port)
