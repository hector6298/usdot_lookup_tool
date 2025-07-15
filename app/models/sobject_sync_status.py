from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from pydantic import ConfigDict

if TYPE_CHECKING:
    from app.models.carrier_data import CarrierData


class SObjectSyncStatus(SQLModel, table=True):
    """SCD type 1 table for maintaining current sync status per carrier and org."""
    
    __tablename__ = "sobject_sync_status"
    
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True
    )
    
    usdot: str = Field(primary_key=True, foreign_key="carrierdata.usdot")
    org_id: str = Field(primary_key=True)
    user_id: str  # User who last attempted sync
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    sync_status: str  # "SUCCESS" or "FAILED"
    sobject_id: Optional[str] = None  # Salesforce ID if successful
    
    # Relationship to CarrierData
    carrier_data: Optional["CarrierData"] = Relationship(back_populates="sync_status")