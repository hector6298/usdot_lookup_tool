from sqlmodel import Field, SQLModel
from typing import List, TYPE_CHECKING
from sqlmodel import Relationship

if TYPE_CHECKING:
    from app.models.ocr_results import OCRResult
    from app.models.crm_object_sync_status import CarrierWithCRMSyncStatusResponse

class AppUser(SQLModel, table=True):
    """Represents an application user in the database."""
    user_id: str = Field(primary_key=True)
    user_email: str
    name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    is_active: bool = True

    ocr_results: List["OCRResult"] = Relationship(back_populates="app_user")
    carrier_engagement_status_usr: List["CarrierWithCRMSyncStatusResponse"] = Relationship(back_populates="app_user")
    user_org_membership: List["UserOrgMembership"] = Relationship(back_populates="app_user")

class AppOrg(SQLModel, table=True):
    """Represents an organization in the database."""
    org_id: str = Field(primary_key=True)
    org_name: str
    is_active: bool = True

    user_org_membership: List["UserOrgMembership"] = Relationship(back_populates="app_org")
    carrier_engagement_status_org: List["CarrierWithCRMSyncStatusResponse"] = Relationship(back_populates="app_org")
    ocr_results: List["OCRResult"] = Relationship(back_populates="app_org")

class UserOrgMembership(SQLModel, table=True):
    """Represents a user's membership in an organization."""
    user_id: str = Field(foreign_key="appuser.user_id", primary_key=True)
    org_id: str = Field(foreign_key="apporg.org_id", primary_key=True)
    is_active: bool = Field(default=True)
    
    app_user: "AppUser" = Relationship(back_populates="user_org_membership")
    app_org: "AppOrg" = Relationship(back_populates="user_org_membership")
