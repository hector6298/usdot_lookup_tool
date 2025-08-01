from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from pydantic import ConfigDict
from enum import Enum

if TYPE_CHECKING:
    from app.models.user_org_membership import AppUser, AppOrg


class SubscriptionStatus(str, Enum):
    """Subscription status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    CANCELLED = "cancelled"
    PAST_DUE = "past_due"
    UNPAID = "unpaid"


class SubscriptionPlan(SQLModel, table=True):
    """Represents a subscription plan with Stripe metered billing."""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)
    stripe_price_id: str = Field(max_length=255)  # Required for Stripe metered billing
    free_quota: int = Field(default=0)  # Free operations included (for quantity transformation)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    subscriptions: List["Subscription"] = Relationship(back_populates="plan")


class Subscription(SQLModel, table=True):
    """Represents a user's subscription to a plan."""
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="appuser.user_id")
    org_id: str = Field(foreign_key="apporg.org_id")
    plan_id: int = Field(foreign_key="subscriptionplan.id")
    stripe_subscription_id: str = Field(max_length=255)  # Required for metered billing
    stripe_customer_id: str = Field(max_length=255)  # Store Stripe customer ID
    status: SubscriptionStatus = Field(default=SubscriptionStatus.ACTIVE)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)
    
    # Relationships
    plan: SubscriptionPlan = Relationship(back_populates="subscriptions")
    app_user: "AppUser" = Relationship(back_populates="subscriptions")
    app_org: "AppOrg" = Relationship(back_populates="subscriptions")


# Pydantic schemas for API requests/responses
class SubscriptionCreate(SQLModel):
    """Schema for creating a subscription."""
    user_id: str
    org_id: str
    plan_id: int


class SubscriptionResponse(SQLModel):
    """Schema for returning subscription data."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: str
    org_id: str
    plan_id: int
    status: SubscriptionStatus
    stripe_subscription_id: str
    stripe_customer_id: str
    plan: SubscriptionPlan


class UsageResponse(SQLModel):
    """Schema for returning current usage data from Stripe."""
    period_start: datetime
    period_end: datetime
    usage_count: int
    plan_free_quota: int