import os
import logging
import stripe
from fastapi import APIRouter, Request, HTTPException

# Set up logging
logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = os.environ.get('STRIPE_SB_SK', 'sk_test_')
webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET', '')

# Initialize APIRouter
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events."""
    try:
        payload = await request.body()
        sig_header = request.headers.get('stripe-signature')
        
        # Verify webhook signature
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
        except ValueError as e:
            logger.error(f"Invalid payload: {e}")
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid signature: {e}")
            raise HTTPException(status_code=400, detail="Invalid signature")
        
        # Handle the event
        if event['type'] == 'invoice.payment_succeeded':
            await handle_invoice_payment_succeeded(event['data']['object'])
        elif event['type'] == 'customer.subscription.updated':
            await handle_subscription_updated(event['data']['object'])
        elif event['type'] == 'customer.subscription.deleted':
            await handle_subscription_deleted(event['data']['object'])
        else:
            logger.info(f"Unhandled event type: {event['type']}")
        
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")


async def handle_invoice_payment_succeeded(invoice):
    """Handle successful subscription payment - just log since Stripe manages everything."""
    try:
        subscription_id = invoice.get('subscription')
        if not subscription_id:
            return
            
        # Get Stripe subscription for logging
        stripe_subscription = stripe.Subscription.retrieve(subscription_id)
        metadata = stripe_subscription.get('metadata', {})
        
        user_id = metadata.get('user_id')
        org_id = metadata.get('org_id')
        
        if user_id and org_id:
            logger.info(f"Invoice payment succeeded for user {user_id}, subscription {subscription_id}")
            # Stripe handles everything automatically for metered billing
            
    except Exception as e:
        logger.error(f"Error handling invoice payment: {e}")


async def handle_subscription_updated(stripe_subscription):
    """Handle subscription updates - just log since Stripe manages state."""
    try:
        metadata = stripe_subscription.get('metadata', {})
        user_id = metadata.get('user_id')
        org_id = metadata.get('org_id')
        
        if user_id and org_id:
            stripe_status = stripe_subscription.get('status')
            logger.info(f"Subscription updated for user {user_id}: {stripe_status}")
            # No local state to manage - Stripe handles everything
                
    except Exception as e:
        logger.error(f"Error handling subscription update: {e}")


async def handle_subscription_deleted(stripe_subscription):
    """Handle subscription cancellation - just log since no local state to clean up."""
    try:
        metadata = stripe_subscription.get('metadata', {})
        user_id = metadata.get('user_id')
        org_id = metadata.get('org_id')
        
        if user_id and org_id:
            logger.info(f"Subscription deleted for user {user_id}")
            # No local state to clean up - Stripe manages everything
                
    except Exception as e:
        logger.error(f"Error handling subscription deletion: {e}")