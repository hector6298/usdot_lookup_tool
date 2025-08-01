import logging
from datetime import datetime, timedelta
from typing import Optional, List
from sqlmodel import Session, select
from app.models.subscription import (
    Subscription, SubscriptionPlan, UsageQuota, OneTimePayment,
    SubscriptionCreate, SubscriptionStatus
)
from app.models.user_org_membership import AppUser, AppOrg
from fastapi import HTTPException

logger = logging.getLogger(__name__)


def get_subscription_plans(db: Session) -> List[SubscriptionPlan]:
    """Get all active subscription plans."""
    try:
        statement = select(SubscriptionPlan).where(SubscriptionPlan.is_active == True)
        plans = db.exec(statement).all()
        return list(plans)
    except Exception as e:
        logger.error(f"Error fetching subscription plans: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch subscription plans")


def get_plan_by_id(db: Session, plan_id: int) -> Optional[SubscriptionPlan]:
    """Get a subscription plan by ID."""
    try:
        return db.get(SubscriptionPlan, plan_id)
    except Exception as e:
        logger.error(f"Error fetching plan {plan_id}: {e}")
        return None


def get_user_subscription(db: Session, user_id: str, org_id: str) -> Optional[Subscription]:
    """Get active subscription for user and org."""
    try:
        statement = select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.org_id == org_id,
            Subscription.status == SubscriptionStatus.ACTIVE
        )
        return db.exec(statement).first()
    except Exception as e:
        logger.error(f"Error fetching subscription for user {user_id}, org {org_id}: {e}")
        return None


def create_subscription(db: Session, subscription_data: SubscriptionCreate) -> Subscription:
    """Create a new subscription."""
    try:
        # Check if user/org exists
        user = db.get(AppUser, subscription_data.user_id)
        org = db.get(AppOrg, subscription_data.org_id)
        plan = db.get(SubscriptionPlan, subscription_data.plan_id)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
        if not plan:
            raise HTTPException(status_code=404, detail="Subscription plan not found")
        
        # Check if active subscription already exists
        existing = get_user_subscription(db, subscription_data.user_id, subscription_data.org_id)
        if existing:
            raise HTTPException(status_code=400, detail="User already has an active subscription")
        
        # Create subscription
        now = datetime.utcnow()
        subscription = Subscription(
            user_id=subscription_data.user_id,
            org_id=subscription_data.org_id,
            plan_id=subscription_data.plan_id,
            status=SubscriptionStatus.ACTIVE,
            current_period_start=now,
            current_period_end=now + timedelta(days=30),  # 30-day period
            created_at=now
        )
        
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
        
        # Create initial usage quota
        create_usage_quota_for_period(db, subscription)
        
        logger.info(f"Created subscription {subscription.id} for user {user_id}")
        return subscription
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating subscription: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create subscription")


def get_current_usage_quota(db: Session, user_id: str, org_id: str) -> Optional[UsageQuota]:
    """Get current usage quota for user/org."""
    try:
        now = datetime.utcnow()
        statement = select(UsageQuota).where(
            UsageQuota.user_id == user_id,
            UsageQuota.org_id == org_id,
            UsageQuota.period_start <= now,
            UsageQuota.period_end >= now
        )
        return db.exec(statement).first()
    except Exception as e:
        logger.error(f"Error fetching usage quota for user {user_id}, org {org_id}: {e}")
        return None


def create_usage_quota_for_period(db: Session, subscription: Subscription, carryover: int = 0) -> UsageQuota:
    """Create a usage quota for a subscription period."""
    try:
        usage_quota = UsageQuota(
            subscription_id=subscription.id,
            user_id=subscription.user_id,
            org_id=subscription.org_id,
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
            quota_limit=subscription.plan.monthly_quota + carryover,
            quota_used=0,
            quota_remaining=subscription.plan.monthly_quota + carryover,
            carryover_from_previous=carryover,
            created_at=datetime.utcnow()
        )
        
        db.add(usage_quota)
        db.commit()
        db.refresh(usage_quota)
        
        logger.info(f"Created usage quota {usage_quota.id} for subscription {subscription.id}")
        return usage_quota
        
    except Exception as e:
        logger.error(f"Error creating usage quota: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create usage quota")


def use_quota(db: Session, user_id: str, org_id: str, amount: int = 1) -> bool:
    """Use quota for user/org. Returns True if successful, False if insufficient quota."""
    try:
        quota = get_current_usage_quota(db, user_id, org_id)
        
        if not quota:
            logger.warning(f"No quota found for user {user_id}, org {org_id}")
            return False
        
        if quota.quota_remaining < amount:
            logger.warning(f"Insufficient quota for user {user_id}, org {org_id}. Needed: {amount}, Available: {quota.quota_remaining}")
            return False
        
        # Update quota usage
        quota.quota_used += amount
        quota.quota_remaining = quota.quota_limit - quota.quota_used
        quota.updated_at = datetime.utcnow()
        
        db.add(quota)
        db.commit()
        
        logger.info(f"Used {amount} quota for user {user_id}, org {org_id}. Remaining: {quota.quota_remaining}")
        return True
        
    except Exception as e:
        logger.error(f"Error using quota: {e}")
        db.rollback()
        return False


def add_quota_from_payment(db: Session, user_id: str, org_id: str, additional_quota: int) -> bool:
    """Add quota from one-time payment."""
    try:
        quota = get_current_usage_quota(db, user_id, org_id)
        
        if not quota:
            logger.warning(f"No quota found for user {user_id}, org {org_id}")
            return False
        
        # Add to quota limit and remaining
        quota.quota_limit += additional_quota
        quota.quota_remaining += additional_quota
        quota.updated_at = datetime.utcnow()
        
        db.add(quota)
        db.commit()
        
        logger.info(f"Added {additional_quota} quota for user {user_id}, org {org_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error adding quota: {e}")
        db.rollback()
        return False


def create_one_time_payment(db: Session, payment_data: dict) -> OneTimePayment:
    """Create a one-time payment record."""
    try:
        payment = OneTimePayment(**payment_data)
        
        db.add(payment)
        db.commit()
        db.refresh(payment)
        
        # Add the purchased quota
        add_quota_from_payment(
            db, 
            payment.user_id, 
            payment.org_id, 
            payment.quota_purchased
        )
        
        logger.info(f"Created one-time payment {payment.id} for user {payment.user_id}")
        return payment
        
    except Exception as e:
        logger.error(f"Error creating one-time payment: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create payment")


def renew_subscription_period(db: Session, subscription: Subscription) -> Subscription:
    """Renew subscription for next period with carryover."""
    try:
        # Get current quota to calculate carryover
        current_quota = get_current_usage_quota(db, subscription.user_id, subscription.org_id)
        carryover = current_quota.quota_remaining if current_quota else 0
        
        # Update subscription period
        now = datetime.utcnow()
        subscription.current_period_start = now
        subscription.current_period_end = now + timedelta(days=30)
        subscription.updated_at = now
        
        db.add(subscription)
        db.commit()
        
        # Create new usage quota with carryover
        create_usage_quota_for_period(db, subscription, carryover)
        
        logger.info(f"Renewed subscription {subscription.id} with carryover {carryover}")
        return subscription
        
    except Exception as e:
        logger.error(f"Error renewing subscription: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to renew subscription")


def initialize_default_plans(db: Session):
    """Initialize default subscription plans if they don't exist."""
    try:
        existing_plans = get_subscription_plans(db)
        if existing_plans:
            logger.info("Subscription plans already exist, skipping initialization")
            return
        
        # Define default plans
        default_plans = [
            SubscriptionPlan(
                name="Free",
                price_cents=0,
                monthly_quota=20,
                is_active=True
            ),
            SubscriptionPlan(
                name="Basic",
                price_cents=999,  # $9.99
                monthly_quota=150,
                is_active=True
            ),
            SubscriptionPlan(
                name="Professional",
                price_cents=2999,  # $29.99
                monthly_quota=500,
                is_active=True
            ),
            SubscriptionPlan(
                name="Enterprise",
                price_cents=9999,  # $99.99
                monthly_quota=2000,  # Assuming this should be higher than 200
                is_active=True
            )
        ]
        
        for plan in default_plans:
            db.add(plan)
        
        db.commit()
        logger.info("Initialized default subscription plans")
        
    except Exception as e:
        logger.error(f"Error initializing default plans: {e}")
        db.rollback()
        raise