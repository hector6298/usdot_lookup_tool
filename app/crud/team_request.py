from sqlmodel import Session, select
from app.models.team_request import TeamRequest, RequestStatus
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

def create_team_request(
    db: Session,
    company_name: str,
    contact_name: str,
    contact_email: str,
    team_size: int,
    team_members: list,
    contact_phone: str = None,
    message: str = None
) -> TeamRequest:
    """Create a new team request."""
    try:
        team_request = TeamRequest(
            company_name=company_name,
            contact_name=contact_name,
            contact_email=contact_email,
            contact_phone=contact_phone,
            team_size=team_size,
            team_members=json.dumps(team_members),
            message=message
        )
        
        db.add(team_request)
        db.commit()
        db.refresh(team_request)
        
        logger.info(f"Created team request for {company_name} with {team_size} members")
        return team_request
        
    except Exception as e:
        logger.error(f"Failed to create team request: {str(e)}")
        db.rollback()
        raise

def get_all_team_requests(db: Session, status: RequestStatus = None) -> list[TeamRequest]:
    """Get all team requests, optionally filtered by status."""
    try:
        query = select(TeamRequest)
        if status:
            query = query.where(TeamRequest.status == status)
        
        return db.exec(query.order_by(TeamRequest.created_at.desc())).all()
        
    except Exception as e:
        logger.error(f"Failed to get team requests: {str(e)}")
        return []

def update_team_request_status(
    db: Session,
    request_id: int,
    status: RequestStatus,
    processed_by: str = None,
    notes: str = None
) -> bool:
    """Update the status of a team request."""
    try:
        team_request = db.exec(select(TeamRequest).where(TeamRequest.id == request_id)).first()
        
        if team_request:
            team_request.status = status
            team_request.processed_at = datetime.utcnow()
            team_request.processed_by = processed_by
            team_request.notes = notes
            
            db.add(team_request)
            db.commit()
            
            logger.info(f"Updated team request {request_id} status to {status}")
            return True
        else:
            logger.error(f"Team request {request_id} not found")
            return False
            
    except Exception as e:
        logger.error(f"Failed to update team request status: {str(e)}")
        db.rollback()
        return False
