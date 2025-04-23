from fastapi import APIRouter
from fastapi.responses import FileResponse
import os

router = APIRouter()

# Path to the landing.html file
LANDING_PAGE_PATH = os.path.join("app", "templates", "home.html")

@router.get("/", response_class=FileResponse)
async def landing_page():
    """Serve the landing page as a static HTML file."""
    return FileResponse(LANDING_PAGE_PATH)