import logging
import csv
from io import StringIO
from typing import Annotated
from fastapi import APIRouter, Depends, Request, HTTPException, Body
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session
from app.database import get_db
from app import crud
from app.routes.verify_login import verify_login

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Set up a module-level logger
logger = logging.getLogger(__name__)

@router.get("/lookup_history", name="lookup_history",
            dependencies=[Depends(verify_login)])
async def dashboard(request: Request, 
                    page: int = 1,
                    page_size: int = 10,
                    db: Session = Depends(get_db)):
    """Render the home page with optional OCR results."""

    user_id = request.session['userinfo']['sub']
    logger.info(f"🔍 Fetching lookup history for user ID: {user_id}")
    
    # Retrieve table with paginated results
    results = crud.get_ocr_results(db, 
                                   user_id=user_id,
                                   page=page, 
                                   page_size=page_size, 
                                   do_pagination=True,
                                   valid_dot_only=False)

    return templates.TemplateResponse(
        "lookup_history.html", 
        {
            "request": request, 
            "results": results["results"],
            "total_pages": results["total_pages"],
            "current_page": page,
            "user_name": request.session['userinfo']['name'],
            "user_image": request.session['userinfo']['picture']
        })

@router.get("/export_lookup_history",
            dependencies=[Depends(verify_login)])
async def export_csv(db: Session = Depends(get_db),
                     request: Request = None):
    """Export the lookup history to a CSV file."""

    user_id = request.session['userinfo']['sub']
    logger.info(f"🔍 Fetching lookup history for user ID: {user_id}"
                )
    history = crud.get_ocr_results(db, 
                                   user_id=user_id,
                                   do_pagination=False,
                                   valid_dot_only=False)['results'] 
    logger.info(f"📥 Exporting {len(history)} history to CSV...")

    # Create a CSV in memory
    output = StringIO()
    writer = csv.writer(output)

    # Write the header row
    writer.writerow(["DOT Number", "Legal Name", "Phone Number", "Mailing Address", "Created At", "Carrier Interested", "Client Contacted"])
    # Write data rows
    for record in history:

        writer.writerow([
            record.dot_reading,
            record.carrier_data.legal_name if record.carrier_data else "",
            record.carrier_data.phone if record.carrier_data else "",
            record.carrier_data.mailing_address if record.carrier_data else "",
            record.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            record.filename
        ])
    output.seek(0)
    logger.info("📥 CSV export completed successfully.")
    
    # Return the CSV as a streaming response
    response = StreamingResponse(output, media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=lookup_history.csv"
    return response