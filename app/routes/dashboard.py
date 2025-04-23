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

@router.get("/dashboard", name="dashboard")
async def dashboard(request: Request, 
                    page: int = 1,
                    page_size: int = 10,
                    result_ids: str = None, 
                    db: Session = Depends(get_db)):
    """Render the home page with optional OCR results."""
    result_texts = []
    dot_readings = []

    # If result_ids are provided, fetch the OCR results from the database
    if result_ids:
        ids = map(int, result_ids.split(","))
        for result_id in ids:
            ocr_result = crud.get_ocr_result_by_id(db, result_id)
            if ocr_result:
                result_texts.append(ocr_result.extracted_text)
                if ocr_result.dot_reading:
                    dot_readings.append(ocr_result.dot_reading)

    # Retrieve table with all results
    carriers = crud.get_paginated_carrier_data(db, page, page_size)

    return templates.TemplateResponse(
        "dashboard.html", 
        {
            "request": request, 
            "result_texts": result_texts,
            "dot_readings": dot_readings,
            "carriers_data": carriers["results"],
            "total_pages": carriers["total_pages"],
            "current_page": page,
        })


@router.post("/update_carrier_interests")
async def update_carrier_interests(request: Request,
                                    db: Session = Depends(get_db)):
    """Update carrier interests based on user input."""
    form_data = await request.json()
    logger.info("🔄 Updating carrier interests..."
                f"Changes received: {form_data}")
    
    try:
        for change_item in form_data.get("changes"):
            dot_number = change_item.get("usdot")
            field = change_item.get("field")
            value = change_item.get("value")

            if not dot_number or not field or value is None:
                raise HTTPException(status_code=400, detail="Invalid input data")

            crud.update_carrier_engagement(db, change_item)
            
        return {"status": "ok", "message": "Changes updated successfully"}
    except Exception as e:
        logger.error(f"Error updating carrier interests: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))