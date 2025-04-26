import logging
from fastapi.templating import Jinja2Templates
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session
from app import crud
from app.database import get_db
from app.routes.verify_login import verify_login, verify_login_json_response

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Set up a module-level logger
logger = logging.getLogger(__name__)


@router.get("/dot_carrier_details/{dot_number}",
            dependencies=[Depends(verify_login)])
def dot_carrier_details(request: Request, 
                dot_number: str, 
                db: Session = Depends(get_db)):
    """Fetch and display carrier details based on DOT number."""
    logger.info(f"🔍 Fetching carrier details for DOT number: {dot_number}")
    carrier = crud.get_carrier_data_by_dot(db, dot_number)

    # If no carrier data is found, return a message
    if not carrier:
        logger.warning(f"⚠ No carrier found for DOT number: {dot_number}")
        return templates.TemplateResponse(
            "dot_carrier_details.html", 
            {
                "request": request, 
                "carrier": None
            })
    
    # Render the template with carrier data
    logger.info(f"✅ Carrier found (USDOT {carrier.usdot}): {carrier.legal_name}")
    logger.info(f"Carrier details: {carrier}")

    return templates.TemplateResponse(
        "dot_carrier_details.html", 
        {
            "request": request, 
            "carrier": carrier
        })
