"""Authentication and authorization utilities."""
import logging
from fastapi import HTTPException, Request
from sqlmodel import Session, select
from app.models.user_org_membership import UserOrgMembership, UserRole
from app.database import get_db
from fastapi import Depends

logger = logging.getLogger(__name__)


def get_user_role(user_id: str, org_id: str, 
                  db: Session = Depends(get_db)) -> UserRole:
    """Get user's role in the organization."""
    try:
        statement = select(UserOrgMembership).where(
            UserOrgMembership.user_id == user_id,
            UserOrgMembership.org_id == org_id,
            UserOrgMembership.is_active == True
        )
        
        membership = db.exec(statement).first()
        if membership:
            return membership.role
        
        # Default to USER role if membership not found
        return UserRole.USER
        
    except Exception as e:
        logger.error(f"Error getting user role: {e}")
        return UserRole.USER


def require_manager_role(request: Request, 
                         db: Session = Depends(get_db)) -> None:
    """
    Dependency that ensures the user has manager role.
    Returns user info if manager, raises HTTPException otherwise.
    """
    if 'id_token' not in request.session:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated"
        )
    
    user_id = request.session['userinfo']['sub']
    org_id = request.session['userinfo'].get('org_id', user_id)
    
    user_role = get_user_role(user_id, org_id, db)
    
    if user_role != UserRole.MANAGER:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "insufficient_permissions",
                "message": "Only organization managers can manage subscriptions. Please contact your manager.",
                "required_role": "manager",
                "current_role": user_role.value
            }
        )

def get_org_name_from_request(request: Request) -> str:
    """Get organization name from request session."""
    # For now, use org_id as org_name - in a real app this would come from the organization table
    return request.session['userinfo'].get('org_name', request.session['userinfo']['email'])


def is_user_manager(user_id: str, org_id: str, db: Session) -> bool:
    """Check if user is a manager in the organization."""
    user_role = get_user_role(user_id, org_id, db)
    return user_role == UserRole.MANAGER