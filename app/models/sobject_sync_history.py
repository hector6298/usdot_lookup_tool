from sqlmodel import Field, SQLModel
from typing import Optional
from datetime import datetime
from pydantic import ConfigDict


class SObjectSyncHistory(SQLModel, table=True):
    """Append-only log table for tracking all Salesforce sync attempts."""
    
    __tablename__ = "sobject_sync_history"
    
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True
    )
    
    id: Optional[int] = Field(default=None, primary_key=True)
    usdot: str = Field(index=True)
    sync_status: str  # "SUCCESS" or "FAILED"
    sync_timestamp: datetime = Field(default_factory=datetime.utcnow)
    sobject_type: str = Field(default="account")  # account, opportunity, etc
    user_id: str = Field(index=True)
    org_id: str = Field(index=True)
    sobject_id: Optional[str] = None  # Salesforce ID if successful
    detail: Optional[str] = None  # Error messages or success details