from sqlmodel import Field, SQLModel
from typing import List, TYPE_CHECKING
from sqlmodel import Relationship
from enum import Enum

if TYPE_CHECKING:
    from app.models.ocr_results import OCRResult
    from app.models.crm_object_sync_status import CRMObjectSyncStatus

class UserRole(str, Enum):
    """User roles within an organization."""
    USER = "user"  # Normal user - can use the app but cannot manage subscriptions
    MANAGER = "manager"  # Manager - can subscribe to products for the organization

class AppUser(SQLModel, table=True):
    """Represents an application user in the database."""
    user_id: str = Field(primary_key=True)
    user_email: str
    name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    is_active: bool = True

    ocr_results: List["OCRResult"] = Relationship(back_populates="app_user")
    crm_object_sync_status_usr: List["CRMObjectSyncStatus"] = Relationship(back_populates="app_user")
    user_org_membership: List["UserOrgMembership"] = Relationship(back_populates="app_user")

class AppOrg(SQLModel, table=True):
    """Represents an organization in the database."""
    org_id: str = Field(primary_key=True)
    org_name: str
    is_active: bool = True

    user_org_membership: List["UserOrgMembership"] = Relationship(back_populates="app_org")
    crm_object_sync_status_org: List["CRMObjectSyncStatus"] = Relationship(back_populates="app_org")
    ocr_results: List["OCRResult"] = Relationship(back_populates="app_org")

class UserOrgMembership(SQLModel, table=True):
    """Represents a user's membership in an organization."""
    user_id: str = Field(foreign_key="appuser.user_id", primary_key=True)
    org_id: str = Field(foreign_key="apporg.org_id", primary_key=True)
    is_active: bool = Field(default=True)
    role: UserRole = Field(default=UserRole.USER)  # Default role is normal user
    
    app_user: "AppUser" = Relationship(back_populates="user_org_membership")
    app_org: "AppOrg" = Relationship(back_populates="user_org_membership")
