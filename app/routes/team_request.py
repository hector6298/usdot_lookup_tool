from fastapi import APIRouter, Request, Depends, Body
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from sqlmodel import Session
from app.database import get_db
from app.crud.team_request import create_team_request
import logging

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger(__name__)

@router.get("/team-request")
async def team_request_page(request: Request):
    """Display the team request form."""
    return templates.TemplateResponse("team_request.html", {"request": request})

@router.post("/team-request")
async def submit_team_request(
    request: Request,
    data: dict = Body(...),
    db: Session = Depends(get_db)
):
    """Process team request submission."""
    try:
        # Extract data from request
        company_name = data.get('company_name')
        contact_name = data.get('contact_name')
        contact_email = data.get('contact_email')
        contact_phone = data.get('contact_phone')
        team_size = int(data.get('team_size', 2))
        message = data.get('message')
        team_members = data.get('team_members', [])
        
        # Validate required fields
        if not all([company_name, contact_name, contact_email]):
            return JSONResponse(
                status_code=400,
                content={"detail": "Company name, contact name, and email are required."}
            )
        
        # Create the team request
        team_request = create_team_request(
            db=db,
            company_name=company_name,
            contact_name=contact_name,
            contact_email=contact_email,
            contact_phone=contact_phone,
            team_size=team_size,
            team_members=team_members,
            message=message
        )
        
        logger.info(f"New team request created: {team_request.id} for {company_name}")
        
        # TODO: Send notification email to admin
        # TODO: Send confirmation email to requester
        
        return JSONResponse(content={"detail": "Team request submitted successfully!"})
        
    except Exception as e:
        logger.error(f"Failed to process team request: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Failed to submit team request. Please try again."}
        )
