from sqlmodel import Field, SQLModel
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlmodel import Relationship

if TYPE_CHECKING:
    from app.models.user_org_membership import AppUser, AppOrg
    from app.models.carrier_data import CarrierData

class CarrierChangeItem(SQLModel):
    """Schema for carrier checkbox input."""
    usdot: str
    field: str
    value: bool | datetime | str

class CarrierChangeRequest(SQLModel):
    """Schema for carrier checkbox input."""
    changes: List[CarrierChangeItem] = Field(default_factory=list)


class CarrierEngagementStatus(SQLModel, table=True):
    usdot: str = Field(foreign_key="carrierdata.usdot", primary_key=True)
    org_id: str = Field(primary_key=True, foreign_key="apporg.org_id")
    user_id: str = Field(nullable=False, foreign_key="appuser.user_id")
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    carrier_interested: bool = Field(default=False, nullable=False)
    carrier_interested_timestamp: datetime = Field(default=None, nullable=True)
    carrier_interested_by_user_id: str = Field(default=None, nullable=True)

    carrier_contacted: bool = Field(default=False, nullable=False)
    carrier_contacted_timestamp: datetime = Field(default=None, nullable=True)
    carrier_contacted_by_user_id: str = Field(default=None, nullable=True)

    carrier_followed_up: bool = Field(default=False, nullable=False)
    carrier_followed_up_timestamp: datetime = Field(default=None, nullable=True)
    carrier_followed_up_by_user_id: str = Field(default=None, nullable=True)
    carrier_follow_up_by_date: datetime = Field(default=None, nullable=True)

    carrier_emailed: bool = Field(default=False, nullable=False)
    carrier_emailed_timestamp: datetime = Field(default=None, nullable=True)
    carrier_emailed_by_user_id: str = Field(default=None, nullable=True)
    rental_notes: str | None = Field(default=None, max_length=360)

    # Relationship attributes
    carrier_data: Optional["CarrierData"] = Relationship(back_populates="carrier_engagement_status")
    app_user: "AppUser" = Relationship(back_populates="carrier_engagement_status_usr")
    app_org: "AppOrg" = Relationship(back_populates="carrier_engagement_status_org")

class CarrierWithEngagementResponse(SQLModel):
    usdot: str
    legal_name: str
    phone: Optional[str]
    mailing_address: str
    created_at: str
    carrier_interested: bool
    carrier_contacted: bool
    carrier_followed_up: bool
    carrier_follow_up_by_date: Optional[str]