import logging
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from app.database import init_db
from app.routes import dashboard, upload, auth, home, data

# Configure Logging to Console
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,  # Set logging level
    format="%(asctime)s - %(levelname)s - %(message)s",  # Log format
    datefmt="%Y-%m-%d %H:%M:%S",  # Date format
)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Starting up...")
    init_db()
    yield
    logger.info("Shutting down...")
    logger.info("Finished shutting down.")

app = FastAPI(title="DOJ OCR Truck Recognition",
              lifespan=lifespan)


# Middleware to be able to access session data
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get('WEBAPP_SESSION_SECRET')
)

# Include routers
app.include_router(auth.router)
app.include_router(home.router)
app.include_router(dashboard.router)
app.include_router(upload.router)
app.include_router(data.router)

# Serve static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

for route in app.routes:
    logger.info(f"Path: {route.path}, Name: {route.name}")