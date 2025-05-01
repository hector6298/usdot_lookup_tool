import logging
import csv
from io import StringIO
from typing import Annotated
from fastapi import APIRouter, Depends, Request, HTTPException, Body
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session
from app.database import get_db
from app import crud
from app.routes.verify_login import verify_login, verify_login_json_response


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Set up a module-level logger
logger = logging.getLogger(__name__)

@router.get("/dashboard", name="dashboard",
            dependencies=[Depends(verify_login)])
async def dashboard(request: Request, 
                    page: int = 1,
                    page_size: int = 10,
                    result_ids: str = None, 
                    db: Session = Depends(get_db)):
    
    """Render the home page with optional OCR results."""
    result_texts = []
    dot_readings = []
    user_id = request.session['userinfo']['sub']

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
    carriers = crud.get_carrier_data(db, 
                                     user_id=user_id,
                                     page=page,
                                     page_size=page_size,
                                     do_pagination=True)
    return templates.TemplateResponse(
        "dashboard.html", 
        {
            "request": request, 
            "result_texts": result_texts,
            "dot_readings": dot_readings,
            "carriers_data": carriers["results"],
            "total_pages": carriers["total_pages"],
            "current_page": page,
            "user_name": request.session['userinfo']['name'],
            "user_image": request.session['userinfo']['picture']
        })


@router.post("/update_carrier_interests",
             dependencies=[Depends(verify_login_json_response)])
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
            
        return JSONResponse(status_code=200, 
                            content={"status": "ok", "message": "Changes updated successfully"})
    except Exception as e:
        logger.error(f"Error updating carrier interests: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    

@router.get("/export_carrier_data",
            dependencies=[Depends(verify_login)])
async def export_csv(request: Request, db: Session = Depends(get_db)):
    """Export carrier data to a CSV file."""

    user_id = request.session['userinfo']['sub']
    logger.info(f"🔍 Fetching carrier data for user ID: {user_id}")

    carriers = crud.get_carrier_data(db,
                                     user_id=user_id,
                                     do_pagination=False)['results'] 
    
    logger.info(f"📥 Exporting {len(carriers)} carriers to CSV...")

    # Create a CSV in memory
    output = StringIO()
    writer = csv.writer(output)

    # Write the header row
    writer.writerow(["DOT Number", "Legal Name", "Phone Number", "Mailing Address", "Created At", "Carrier Interested", "Client Contacted"])
    # Write data rows
    for carrier in carriers:

        writer.writerow([
            carrier.usdot,
            carrier.legal_name,
            carrier.phone,
            carrier.mailing_address,
            carrier.max_ocr_timestamp,
            carrier.carrier_interested,
            carrier.carrier_contacted
        ])
    output.seek(0)
    logger.info("📥 CSV export completed successfully.")
    
    # Return the CSV as a streaming response
    response = StreamingResponse(output, media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=carrier_data.csv"
    return response