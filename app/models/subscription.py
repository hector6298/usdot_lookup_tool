from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from pydantic import ConfigDict

if TYPE_CHECKING:
    from app.models.user_org_membership import AppUser, AppOrg


class SubscriptionMapping(SQLModel, table=True):
    """Minimal mapping between local users/orgs and Stripe entities."""
    __tablename__ = "subscription_mapping"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="appuser.user_id")
    org_id: str = Field(foreign_key="apporg.org_id")
    stripe_customer_id: str = Field(max_length=255)
    stripe_subscription_id: str = Field(max_length=255)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    app_user: "AppUser" = Relationship(back_populates="subscription_mappings")
    app_org: "AppOrg" = Relationship(back_populates="subscription_mappings")


# Pydantic schemas for API requests/responses
class SubscriptionCreate(SQLModel):
    """Schema for creating a subscription."""
    user_id: str
    org_id: str
    stripe_price_id: str  # Pass Stripe price ID directly


class SubscriptionResponse(SQLModel):
    """Schema for returning subscription data from Stripe."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str  # Stripe subscription ID
    customer_id: str  # Stripe customer ID
    status: str  # Stripe subscription status
    price_id: str  # Stripe price ID
    product_id: str  # Stripe product ID
    product_name: str  # Product name from Stripe metadata
    current_period_start: datetime
    current_period_end: datetime


class UsageResponse(SQLModel):
    """Schema for returning current usage data from Stripe."""
    period_start: datetime
    period_end: datetime
    usage_count: int
    free_quota: int  # From Stripe product metadata