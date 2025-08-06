import os
import logging
import stripe
from datetime import datetime
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = os.environ.get('STRIPE_SB_SK', 'sk_test_')


def find_user_subscription(user_id: str, org_id: str) -> Optional[stripe.Subscription]:
    """Find user's active subscription using Stripe search."""
    try:
        # Search for subscriptions with user metadata
        subscriptions = stripe.Subscription.search(
            query=f'metadata["user_id"]:"{user_id}" AND metadata["org_id"]:"{org_id}" AND status:"active"'
        )
        
        if subscriptions.data:
            return subscriptions.data[0]  # Return first active subscription
        
        return None
        
    except stripe.error.StripeError as e:
        logger.error(f"Error searching for user subscription: {e}")
        return None


def find_or_create_customer(user_id: str, org_id: str, email: str) -> Optional[stripe.Customer]:
    """Find existing customer or create new one with user metadata."""
    try:
        # Search for existing customer by email
        customers = stripe.Customer.list(
            email=email,
            limit=1
        )
        
        if customers.data:
            customer = customers.data[0]
            # Update metadata if needed
            if (customer.metadata.get('user_id') != user_id or 
                customer.metadata.get('org_id') != org_id):
                stripe.Customer.modify(
                    customer.id,
                    metadata={
                        'user_id': user_id,
                        'org_id': org_id
                    }
                )
            return customer
        
        # Create new customer
        customer = stripe.Customer.create(
            email=email,
            metadata={
                'user_id': user_id,
                'org_id': org_id
            }
        )
        
        return customer
        
    except stripe.error.StripeError as e:
        logger.error(f"Error finding/creating customer: {e}")
        return None


def get_subscription_plans() -> List[Dict[str, Any]]:
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


def create_subscription(user_id: str, org_id: str, email: str, price_id: str) -> Optional[stripe.Subscription]:
    """Create a new subscription with metered billing."""
    try:
        # Validate that the price exists and is for a subscription plan
        price = stripe.Price.retrieve(price_id, expand=['product'])
        if not price.product.metadata.get('is_subscription_plan') == 'true':
            logger.error(f"Price {price_id} is not a subscription plan")
            return None
        
        # Find or create customer
        customer = find_or_create_customer(user_id, org_id, email)
        if not customer:
            logger.error("Failed to find or create customer")
            return None
        
        # Check if user already has an active subscription
        existing_subscription = find_user_subscription(user_id, org_id)
        if existing_subscription:
            logger.error(f"User {user_id} already has an active subscription")
            return None
        
        # Create Stripe subscription with metered billing
        subscription = stripe.Subscription.create(
            customer=customer.id,
            items=[{
                'price': price_id,
            }],
            metadata={
                'user_id': user_id,
                'org_id': org_id,
                'product_id': price.product.id
            }
        )
        
        logger.info(f"Created subscription {subscription.id} for user {user_id}")
        return subscription
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating subscription: {e}")
        return None


def report_usage(user_id: str, org_id: str, usage_quantity: int = 1) -> bool:
    """Report usage to Stripe for metered billing."""
    try:
        # Find user's subscription
        subscription = find_user_subscription(user_id, org_id)
        if not subscription:
            logger.warning(f"No active subscription found for user {user_id}")
            return False
        
        if not subscription.items.data:
            logger.error(f"No subscription items found for {subscription.id}")
            return False
        
        # Get the subscription item (should be only one for metered billing)
        subscription_item = subscription.items.data[0]
        
        # Report usage to Stripe
        usage_record = stripe.UsageRecord.create(
            subscription_item=subscription_item.id,
            quantity=usage_quantity,
            timestamp=int(datetime.utcnow().timestamp()),
            action='increment'
        )
        
        logger.info(f"Reported {usage_quantity} usage to Stripe for user {user_id}")
        return True
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error reporting usage: {e}")
        return False


def get_user_usage(user_id: str, org_id: str) -> Optional[Dict[str, Any]]:
    """Get current usage data from Stripe."""
    try:
        # Find user's subscription
        subscription = find_user_subscription(user_id, org_id)
        if not subscription:
            return None
        
        # Expand to get product details
        subscription = stripe.Subscription.retrieve(
            subscription.id,
            expand=['items.data.price.product']
        )
        
        if not subscription.items.data:
            return None
        
        # Get the subscription item
        subscription_item = subscription.items.data[0]
        product = subscription_item.price.product
        
        # Get usage records summary for current period
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
            'period_start': datetime.fromtimestamp(subscription.current_period_start),
            'period_end': datetime.fromtimestamp(subscription.current_period_end),
            'usage_count': usage_count,
            'free_quota': free_quota
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error getting usage: {e}")
        return None


def get_subscription_details(user_id: str, org_id: str) -> Optional[Dict[str, Any]]:
    """Get full subscription details from Stripe."""
    try:
        subscription = find_user_subscription(user_id, org_id)
        if not subscription:
            return None
        
        # Expand to get product details
        subscription = stripe.Subscription.retrieve(
            subscription.id,
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
        logger.error(f"Error fetching subscription details: {e}")
        return None


def get_user_invoices(user_id: str, org_id: str) -> List[Any]:
    """Get user's Stripe invoices."""
    try:
        # Find user's subscription to get customer ID
        subscription = find_user_subscription(user_id, org_id)
        if not subscription:
            return []
        
        # Get invoices from Stripe
        invoices = stripe.Invoice.list(
            customer=subscription.customer,
            limit=10
        )
        
        return invoices.data
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error fetching invoices: {e}")
        return []


def cancel_subscription(user_id: str, org_id: str) -> Optional[stripe.Subscription]:
    """Cancel user's subscription at period end."""
    try:
        subscription = find_user_subscription(user_id, org_id)
        if not subscription:
            return None
        
        # Cancel at period end
        cancelled_subscription = stripe.Subscription.modify(
            subscription.id,
            cancel_at_period_end=True
        )
        
        logger.info(f"Cancelled subscription {subscription.id} for user {user_id}")
        return cancelled_subscription
        
    except stripe.error.StripeError as e:
        logger.error(f"Error canceling subscription: {e}")
        return None