from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from pydantic import ConfigDict

if TYPE_CHECKING:
    from app.models.carrier_data import CarrierData
    from app.models.user_org_membership import AppUser, AppOrg


class CRMObjectSyncStatus(SQLModel, table=True):
    """SCD type 1 table for maintaining current sync status per carrier and org."""
        
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True
    )
    
    usdot: str = Field(primary_key=True, foreign_key="carrierdata.usdot")
    org_id: str = Field(primary_key=True, foreign_key="apporg.org_id")
    user_id: str = Field(nullable=False, foreign_key="appuser.user_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    crm_sync_status: str  # "SUCCESS" or "FAILED"
    crm_synched_at: Optional[datetime]
    crm_object_id: Optional[str] = None  # CRM Object ID if successful
    crm_platform: Optional[str] 

    # Relationship to CarrierData
    carrier_data: Optional["CarrierData"] = Relationship(back_populates="sync_status")
    app_user: "AppUser" = Relationship(back_populates="crm_object_sync_status_usr")
    app_org: "AppOrg" = Relationship(back_populates="crm_object_sync_status_org")


class CarrierWithCRMSyncStatusResponse(SQLModel):
    usdot: str
    legal_name: str
    phone: Optional[str]
    mailing_address: str
    created_at: str
    updated_at: str
    crm_sync_status: Optional[str] = None  # "SUCCESS", "FAILED", or None
    crm_object_id: Optional[str] = None 
    crm_synched_at: Optional[str] = None  # When last sync was attempted
    crm_platform: Optional[str] = None  # e.g. "salesforce", "hubspot"