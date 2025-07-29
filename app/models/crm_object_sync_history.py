from sqlmodel import Field, SQLModel
from typing import Optional
from datetime import datetime
from pydantic import ConfigDict


class CRMObjectSyncHistory(SQLModel, table=True):
    """Append-only log table for tracking all Salesforce sync attempts."""
        
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True
    )
    
    id: Optional[int] = Field(default=None, primary_key=True)
    usdot: str = Field(index=True)
    crm_sync_status: str  # "SUCCESS" or "FAILED"
    crm_synched_at: datetime = Field(default_factory=datetime.utcnow)
    crm_object_type: str = Field(default="account")  # account, opportunity, etc
    crm_object_id: Optional[str] = None  # Salesforce ID if successful
    crm_platform: str = Field(nullable=False)  # e.g. "salesforce", "hubspot"
    user_id: str = Field(index=True)
    org_id: str = Field(index=True)
    detail: Optional[str] = None  # Error messages or success details