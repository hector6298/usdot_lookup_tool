import logging
import stripe
from datetime import datetime
from typing import Optional, List
from sqlmodel import Session, select
from app.models.subscription import (
    Subscription, SubscriptionPlan,
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


def create_subscription(db: Session, subscription_data: SubscriptionCreate, stripe_subscription_id: str, stripe_customer_id: str) -> Subscription:
    """Create a new subscription with Stripe IDs."""
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
        subscription = Subscription(
            user_id=subscription_data.user_id,
            org_id=subscription_data.org_id,
            plan_id=subscription_data.plan_id,
            stripe_subscription_id=stripe_subscription_id,
            stripe_customer_id=stripe_customer_id,
            status=SubscriptionStatus.ACTIVE,
            created_at=datetime.utcnow()
        )
        
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
        
        logger.info(f"Created subscription {subscription.id} for user {subscription_data.user_id}")
        return subscription
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating subscription: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create subscription")


def report_usage_to_stripe(subscription: Subscription, usage_quantity: int) -> bool:
    """Report usage to Stripe for metered billing."""
    try:
        # Get the subscription items from Stripe
        stripe_subscription = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
        
        if not stripe_subscription.items.data:
            logger.error(f"No subscription items found for {subscription.stripe_subscription_id}")
            return False
        
        # Get the first (and should be only) subscription item
        subscription_item = stripe_subscription.items.data[0]
        
        # Report usage to Stripe
        usage_record = stripe.UsageRecord.create(
            subscription_item=subscription_item.id,
            quantity=usage_quantity,
            timestamp=int(datetime.utcnow().timestamp()),
            action='increment'  # Increment usage instead of setting absolute value
        )
        
        logger.info(f"Reported {usage_quantity} usage to Stripe for subscription {subscription.stripe_subscription_id}")
        return True
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error reporting usage: {e}")
        return False
    except Exception as e:
        logger.error(f"Error reporting usage to Stripe: {e}")
        return False


def get_current_usage_from_stripe(subscription: Subscription) -> Optional[dict]:
    """Get current usage data from Stripe."""
    try:
        # Get the subscription from Stripe
        stripe_subscription = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
        
        if not stripe_subscription.items.data:
            logger.error(f"No subscription items found for {subscription.stripe_subscription_id}")
            return None
        
        # Get the subscription item
        subscription_item = stripe_subscription.items.data[0]
        
        # Get usage records summary for current period
        current_period_start = stripe_subscription.current_period_start
        current_period_end = stripe_subscription.current_period_end
        
        # Get usage summary from Stripe
        usage_summary = stripe.UsageRecordSummary.list(
            subscription_item=subscription_item.id,
            limit=1
        )
        
        usage_count = 0
        if usage_summary.data:
            usage_count = usage_summary.data[0].total_usage
        
        return {
            'period_start': datetime.fromtimestamp(current_period_start),
            'period_end': datetime.fromtimestamp(current_period_end),
            'usage_count': usage_count,
            'plan_free_quota': subscription.plan.free_quota
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error getting usage: {e}")
        return None
    except Exception as e:
        logger.error(f"Error getting usage from Stripe: {e}")
        return None


def initialize_default_plans(db: Session):
    """Initialize default subscription plans for Stripe metered billing."""
    try:
        existing_plans = get_subscription_plans(db)
        if existing_plans:
            logger.info("Subscription plans already exist, skipping initialization")
            return
        
        # Note: These Stripe price IDs should be created in Stripe dashboard with metered billing
        # and quantity_transformation for tiered pricing structure
        default_plans = [
            SubscriptionPlan(
                name="Free",
                stripe_price_id="price_free_tier",  # This should be created in Stripe
                free_quota=20,  # First 20 operations free
                is_active=True
            ),
            SubscriptionPlan(
                name="Basic",
                stripe_price_id="price_basic_tier",  # Metered price with quantity transformation
                free_quota=20,  # First 20 operations free, then metered
                is_active=True
            ),
            SubscriptionPlan(
                name="Professional", 
                stripe_price_id="price_professional_tier",
                free_quota=20,  # First 20 operations free, then metered
                is_active=True
            ),
            SubscriptionPlan(
                name="Enterprise",
                stripe_price_id="price_enterprise_tier",
                free_quota=20,  # First 20 operations free, then metered
                is_active=True
            )
        ]
        
        for plan in default_plans:
            db.add(plan)
        
        db.commit()
        logger.info("Initialized default subscription plans for metered billing")
        
    except Exception as e:
        logger.error(f"Error initializing default plans: {e}")
        db.rollback()
        raise