from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/blog", name="blog", response_class=HTMLResponse)
async def blog_index(request: Request):
    """Serve the blog index page."""
    return templates.TemplateResponse("blog_index.html", {"request": request})

@router.get("/blog/automated-lead-capture-pipeline", name="blog_post_lead_capture", response_class=HTMLResponse)
async def blog_post_lead_capture(request: Request):
    """Serve the blog post about automated lead capture pipeline."""
    return templates.TemplateResponse("blog_post_lead_capture.html", {"request": request})