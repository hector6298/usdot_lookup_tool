from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/privacy-policy", name="privacy_policy", response_class=HTMLResponse)
async def privacy_policy(request: Request):
    """Serve the privacy policy page."""
    return templates.TemplateResponse("privacy_policy.html", {"request": request})