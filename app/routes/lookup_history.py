import logging
from typing import Annotated
from fastapi import APIRouter, Depends, Request, HTTPException, Body
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session
from app.database import get_db
from app.models import CarrierChangeItem, CarrierChangeRequest
from app import crud

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Set up a module-level logger
logger = logging.getLogger(__name__)

@router.get("/lookup_history", name="dashboard")
async def dashboard(request: Request, 
                    page: int = 1,
                    page_size: int = 10,
                    db: Session = Depends(get_db)):
    """Render the home page with optional OCR results."""

    # Retrieve table with all results
    results = crud.get_paginated_ocr_results(db, page, page_size, valid_dot_only=False)

    return templates.TemplateResponse(
        "dashboard.html", 
        {
            "request": request, 
            "carriers_data": results["results"],
            "total_pages": results["total_pages"],
            "current_page": page,
        })
