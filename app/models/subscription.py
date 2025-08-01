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
    """Represents a subscription plan with pricing and quotas."""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)
    price_cents: int  # Price in cents (e.g., 999 for $9.99)
    monthly_quota: int  # Number of operations allowed per month
    stripe_price_id: Optional[str] = Field(default=None, max_length=255)
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
    stripe_subscription_id: Optional[str] = Field(default=None, max_length=255)
    status: SubscriptionStatus = Field(default=SubscriptionStatus.ACTIVE)
    current_period_start: datetime
    current_period_end: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)
    
    # Relationships
    plan: SubscriptionPlan = Relationship(back_populates="subscriptions")
    app_user: "AppUser" = Relationship(back_populates="subscriptions")
    app_org: "AppOrg" = Relationship(back_populates="subscriptions")
    usage_quotas: List["UsageQuota"] = Relationship(back_populates="subscription")


class UsageQuota(SQLModel, table=True):
    """Tracks monthly usage quotas for subscriptions."""
    id: Optional[int] = Field(default=None, primary_key=True)
    subscription_id: int = Field(foreign_key="subscription.id")
    user_id: str = Field(foreign_key="appuser.user_id")
    org_id: str = Field(foreign_key="apporg.org_id")
    period_start: datetime
    period_end: datetime
    quota_limit: int  # Total quota for this period
    quota_used: int = Field(default=0)  # Amount used in this period
    quota_remaining: int  # Computed field: quota_limit - quota_used
    carryover_from_previous: int = Field(default=0)  # Unused quota from previous period
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)
    
    # Relationships
    subscription: Subscription = Relationship(back_populates="usage_quotas")
    app_user: "AppUser" = Relationship(back_populates="usage_quotas")
    app_org: "AppOrg" = Relationship(back_populates="usage_quotas")


class OneTimePayment(SQLModel, table=True):
    """Tracks one-time payments for quota resets."""
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="appuser.user_id")
    org_id: str = Field(foreign_key="apporg.org_id")
    stripe_payment_intent_id: str = Field(max_length=255)
    amount_cents: int  # Amount paid in cents
    quota_purchased: int  # Additional quota purchased
    description: Optional[str] = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    app_user: "AppUser" = Relationship(back_populates="one_time_payments")
    app_org: "AppOrg" = Relationship(back_populates="one_time_payments")


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
    current_period_start: datetime
    current_period_end: datetime
    plan: SubscriptionPlan


class UsageQuotaResponse(SQLModel):
    """Schema for returning usage quota data."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    subscription_id: int
    period_start: datetime
    period_end: datetime
    quota_limit: int
    quota_used: int
    quota_remaining: int
    carryover_from_previous: int


class OneTimePaymentCreate(SQLModel):
    """Schema for creating a one-time payment."""
    user_id: str
    org_id: str
    amount_cents: int
    quota_purchased: int
    description: Optional[str] = None