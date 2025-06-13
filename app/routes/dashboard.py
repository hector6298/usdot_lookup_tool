import logging
from enum import Enum
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.templating import Jinja2Templates
from sqlmodel import Session
from app.database import get_db
from app.routes.verify_login import verify_login
from app import crud

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Set up a module-level logger
logger = logging.getLogger(__name__)

class DashboardType(str, Enum):
    """Enum for different dashboard types."""
    carriers = "carriers"
    lookup_history = "lookup_history"


@router.get("/dashboards/{dashboard_type}",
            dependencies=[Depends(verify_login)])
async def dashboard(request: Request,
                    dashboard_type: DashboardType,
                    db: Session = Depends(get_db)):
    
    """Render the Dashboard using User info from session."""

    if dashboard_type == DashboardType.lookup_history:
        dashboard_file = "lookup_history.html"
    elif dashboard_type == DashboardType.carriers:
        dashboard_file = "dashboard.html"
    else:
        raise HTTPException(status_code=404, detail="Dashboard not found")
        
    return templates.TemplateResponse(
        dashboard_file, 
        {
            "request": request, 
            "user_name": request.session['userinfo']['name'],
            "user_image": request.session['userinfo']['picture'],
            "dashboard_type": dashboard_type.value  # Use .value to get the string representation
        })


@router.get("/dashboards/carrier_details/{dot_number}",
            dependencies=[Depends(verify_login)])
def fetch_carrier(request: Request, 
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
                "carrier": None,
                "user_name": request.session['userinfo']['name'],
                "user_image": request.session['userinfo']['picture'],
            })
    
    # Render the template with carrier data
    logger.info(f"✅ Carrier found (USDOT {carrier.usdot}): {carrier.legal_name}")
    logger.info(f"Carrier details: {carrier}")

    return templates.TemplateResponse(
        "dot_carrier_details.html", 
        {
            "request": request, 
            "carrier": carrier,
            "user_name": request.session['userinfo']['name'],
            "user_image": request.session['userinfo']['picture'],
        })