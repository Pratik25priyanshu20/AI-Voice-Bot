from fastapi import FastAPI

from config.settings import settings
from src.api.routes import router
from src.database.db import init_db
from src.utils.logger import get_logger

logger = get_logger(__name__)

app = FastAPI(title="AI Voice Bot", version="0.1.0", debug=settings.debug)
app.include_router(router)


@app.on_event("startup")
async def startup_event() -> None:
    logger.info("Starting AI Voice Bot in %s mode", settings.environment)
    init_db()
