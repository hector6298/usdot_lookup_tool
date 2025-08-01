import logging
import stripe
from datetime import datetime
from typing import Optional, List
from sqlmodel import Session, select
from app.models.subscription import (
    SubscriptionMapping, SubscriptionCreate
)
from app.models.user_org_membership import AppUser, AppOrg
from fastapi import HTTPException

logger = logging.getLogger(__name__)


def get_user_subscription_mapping(db: Session, user_id: str, org_id: str) -> Optional[SubscriptionMapping]:
    """Get subscription mapping for user and org."""
    try:
        statement = select(SubscriptionMapping).where(
            SubscriptionMapping.user_id == user_id,
            SubscriptionMapping.org_id == org_id
        )
        return db.exec(statement).first()
    except Exception as e:
        logger.error(f"Error fetching subscription mapping for user {user_id}, org {org_id}: {e}")
        return None


def get_stripe_subscription(mapping: SubscriptionMapping) -> Optional[stripe.Subscription]:
    """Get subscription data directly from Stripe."""
    try:
        subscription = stripe.Subscription.retrieve(
            mapping.stripe_subscription_id,
            expand=['items.data.price.product']
        )
        return subscription
    except stripe.error.StripeError as e:
        logger.error(f"Error fetching Stripe subscription {mapping.stripe_subscription_id}: {e}")
        return None


def get_active_subscription_plans() -> List[dict]:
    """Get available subscription plans from Stripe products."""
    try:
        # Get all products with metadata indicating they are subscription plans
        products = stripe.Product.list(
            active=True,
            type='service',
            limit=100
        )
        
        plans = []
        for product in products.data:
            # Only include products that have subscription plan metadata
            if product.metadata.get('is_subscription_plan') == 'true':
                # Get prices for this product
                prices = stripe.Price.list(
                    product=product.id,
                    active=True
                )
                
                for price in prices.data:
                    if price.billing_scheme == 'tiered' and price.usage_type == 'metered':
                        plans.append({
                            'product_id': product.id,
                            'product_name': product.name,
                            'price_id': price.id,
                            'free_quota': int(product.metadata.get('free_quota', 0)),
                            'description': product.description,
                            'tiers': price.tiers
                        })
        
        return plans
    except stripe.error.StripeError as e:
        logger.error(f"Error fetching subscription plans from Stripe: {e}")
        return []


def create_subscription_mapping(
    db: Session, 
    subscription_data: SubscriptionCreate, 
    stripe_subscription_id: str, 
    stripe_customer_id: str
) -> SubscriptionMapping:
    """Create a new subscription mapping."""
    try:
        # Check if user/org exists
        user = db.get(AppUser, subscription_data.user_id)
        org = db.get(AppOrg, subscription_data.org_id)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
        
        # Check if active subscription already exists
        existing = get_user_subscription_mapping(db, subscription_data.user_id, subscription_data.org_id)
        if existing:
            # Check if Stripe subscription is still active
            stripe_sub = get_stripe_subscription(existing)
            if stripe_sub and stripe_sub.status in ['active', 'trialing', 'past_due']:
                raise HTTPException(status_code=400, detail="User already has an active subscription")
            else:
                # Remove old mapping if Stripe subscription is cancelled/inactive
                db.delete(existing)
                db.commit()
        
        # Create subscription mapping
        mapping = SubscriptionMapping(
            user_id=subscription_data.user_id,
            org_id=subscription_data.org_id,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
            created_at=datetime.utcnow()
        )
        
        db.add(mapping)
        db.commit()
        db.refresh(mapping)
        
        logger.info(f"Created subscription mapping {mapping.id} for user {subscription_data.user_id}")
        return mapping
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating subscription mapping: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create subscription")


def report_usage_to_stripe(mapping: SubscriptionMapping, usage_quantity: int) -> bool:
    """Report usage to Stripe for metered billing."""
    try:
        # Get the subscription items from Stripe
        stripe_subscription = stripe.Subscription.retrieve(mapping.stripe_subscription_id)
        
        if not stripe_subscription.items.data:
            logger.error(f"No subscription items found for {mapping.stripe_subscription_id}")
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
        
        logger.info(f"Reported {usage_quantity} usage to Stripe for subscription {mapping.stripe_subscription_id}")
        return True
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error reporting usage: {e}")
        return False
    except Exception as e:
        logger.error(f"Error reporting usage to Stripe: {e}")
        return False


def get_current_usage_from_stripe(mapping: SubscriptionMapping) -> Optional[dict]:
    """Get current usage data from Stripe."""
    try:
        # Get the subscription from Stripe
        stripe_subscription = stripe.Subscription.retrieve(
            mapping.stripe_subscription_id,
            expand=['items.data.price.product']
        )
        
        if not stripe_subscription.items.data:
            logger.error(f"No subscription items found for {mapping.stripe_subscription_id}")
            return None
        
        # Get the subscription item
        subscription_item = stripe_subscription.items.data[0]
        product = subscription_item.price.product
        
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
        
        # Get free quota from product metadata
        free_quota = int(product.metadata.get('free_quota', 0))
        
        return {
            'period_start': datetime.fromtimestamp(current_period_start),
            'period_end': datetime.fromtimestamp(current_period_end),
            'usage_count': usage_count,
            'free_quota': free_quota
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error getting usage: {e}")
        return None
    except Exception as e:
        logger.error(f"Error getting usage from Stripe: {e}")
        return None


def get_subscription_details_from_stripe(mapping: SubscriptionMapping) -> Optional[dict]:
    """Get full subscription details from Stripe."""
    try:
        subscription = stripe.Subscription.retrieve(
            mapping.stripe_subscription_id,
            expand=['items.data.price.product']
        )
        
        if not subscription.items.data:
            return None
        
        item = subscription.items.data[0]
        product = item.price.product
        
        return {
            'id': subscription.id,
            'customer_id': subscription.customer,
            'status': subscription.status,
            'price_id': item.price.id,
            'product_id': product.id,
            'product_name': product.name,
            'current_period_start': datetime.fromtimestamp(subscription.current_period_start),
            'current_period_end': datetime.fromtimestamp(subscription.current_period_end)
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Error fetching subscription details from Stripe: {e}")
        return None


# Legacy functions to maintain compatibility (can be removed after migration)
def get_user_subscription(db: Session, user_id: str, org_id: str):
    """Legacy compatibility function - returns mapping instead of subscription."""
    return get_user_subscription_mapping(db, user_id, org_id)


def get_subscription_plans(db: Session):
    """Legacy compatibility function - returns Stripe plans."""
    return get_active_subscription_plans()


def get_plan_by_id(db: Session, plan_id: str):
    """Legacy compatibility function - gets plan from Stripe."""
    try:
        product = stripe.Product.retrieve(plan_id)
        if product.metadata.get('is_subscription_plan') == 'true':
            return {
                'id': product.id,
                'name': product.name,
                'free_quota': int(product.metadata.get('free_quota', 0))
            }
    except stripe.error.StripeError:
        pass
    return None