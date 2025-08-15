from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum

class RequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"

class TeamRequest(SQLModel, table=True):
    """Represents a request for multi-user organization setup."""
    id: int = Field(primary_key=True)
    company_name: str
    contact_name: str
    contact_email: str
    contact_phone: Optional[str] = None
    team_size: int
    team_members: str  # JSON string of team member details
    message: Optional[str] = None
    status: RequestStatus = Field(default=RequestStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    processed_by: Optional[str] = None
    notes: Optional[str] = None
