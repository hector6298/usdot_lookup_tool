from sqlmodel import Field, SQLModel
from typing import Optional
from datetime import datetime, timezone
from pydantic import ConfigDict


class CRMObjectSyncHistory(SQLModel, table=True):
    """Append-only log table for tracking all CRM sync attempts."""
    
    __tablename__ = "sobject_sync_history"
    
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True
    )
    
    id: Optional[int] = Field(default=None, primary_key=True)
    usdot: str = Field(index=True)
    sync_status: str  # "SUCCESS" or "FAILED"
    sync_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: str = Field(index=True)
    org_id: str = Field(index=True)
    crm_object_type: str = Field(default="account")  # account, opportunity, etc
    crm_object_id: Optional[str] = None  # CRM object ID if successful
    detail: Optional[str] = None  # Error messages or success details

