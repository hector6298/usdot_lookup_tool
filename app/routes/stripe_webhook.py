import os
import logging
import stripe
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException
from sqlmodel import Session
from app.database import get_db
from app.models.subscription import Subscription, SubscriptionStatus
from app.crud.subscription import create_one_time_payment, renew_subscription_period

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
        if event['type'] == 'payment_intent.succeeded':
            await handle_payment_intent_succeeded(event['data']['object'])
        elif event['type'] == 'invoice.payment_succeeded':
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


async def handle_payment_intent_succeeded(payment_intent):
    """Handle successful one-time payment."""
    try:
        metadata = payment_intent.get('metadata', {})
        
        if metadata.get('type') == 'quota_purchase':
            user_id = metadata.get('user_id')
            org_id = metadata.get('org_id') 
            quota_amount = int(metadata.get('quota_amount', 0))
            
            # Create payment record
            from app.database import get_db
            db = next(get_db())
            
            payment_data = {
                'user_id': user_id,
                'org_id': org_id,
                'stripe_payment_intent_id': payment_intent['id'],
                'amount_cents': payment_intent['amount'],
                'quota_purchased': quota_amount,
                'description': f'Additional quota purchase: {quota_amount} operations'
            }
            
            create_one_time_payment(db, payment_data)
            logger.info(f"Created one-time payment for user {user_id}: {quota_amount} quota")
            
    except Exception as e:
        logger.error(f"Error handling payment intent: {e}")


async def handle_invoice_payment_succeeded(invoice):
    """Handle successful subscription payment."""
    try:
        subscription_id = invoice.get('subscription')
        if not subscription_id:
            return
            
        # Get Stripe subscription
        stripe_subscription = stripe.Subscription.retrieve(subscription_id)
        metadata = stripe_subscription.get('metadata', {})
        
        user_id = metadata.get('user_id')
        org_id = metadata.get('org_id')
        
        if user_id and org_id:
            # Update subscription period in our database
            from app.database import get_db
            from app.crud.subscription import get_user_subscription
            
            db = next(get_db())
            subscription = get_user_subscription(db, user_id, org_id)
            
            if subscription:
                # Renew subscription period
                renew_subscription_period(db, subscription)
                logger.info(f"Renewed subscription for user {user_id}")
            
    except Exception as e:
        logger.error(f"Error handling invoice payment: {e}")


async def handle_subscription_updated(stripe_subscription):
    """Handle subscription updates."""
    try:
        metadata = stripe_subscription.get('metadata', {})
        user_id = metadata.get('user_id')
        org_id = metadata.get('org_id')
        
        if user_id and org_id:
            from app.database import get_db
            from app.crud.subscription import get_user_subscription
            
            db = next(get_db())
            subscription = get_user_subscription(db, user_id, org_id)
            
            if subscription:
                # Update subscription status based on Stripe status
                stripe_status = stripe_subscription.get('status')
                
                if stripe_status == 'active':
                    subscription.status = SubscriptionStatus.ACTIVE
                elif stripe_status == 'past_due':
                    subscription.status = SubscriptionStatus.PAST_DUE
                elif stripe_status == 'unpaid':
                    subscription.status = SubscriptionStatus.UNPAID
                elif stripe_status == 'canceled':
                    subscription.status = SubscriptionStatus.CANCELLED
                    
                subscription.updated_at = datetime.utcnow()
                db.add(subscription)
                db.commit()
                
                logger.info(f"Updated subscription status for user {user_id}: {stripe_status}")
                
    except Exception as e:
        logger.error(f"Error handling subscription update: {e}")


async def handle_subscription_deleted(stripe_subscription):
    """Handle subscription cancellation."""
    try:
        metadata = stripe_subscription.get('metadata', {})
        user_id = metadata.get('user_id')
        org_id = metadata.get('org_id')
        
        if user_id and org_id:
            from app.database import get_db
            from app.crud.subscription import get_user_subscription
            
            db = next(get_db())
            subscription = get_user_subscription(db, user_id, org_id)
            
            if subscription:
                subscription.status = SubscriptionStatus.CANCELLED
                subscription.updated_at = datetime.utcnow()
                db.add(subscription)
                db.commit()
                
                logger.info(f"Cancelled subscription for user {user_id}")
                
    except Exception as e:
        logger.error(f"Error handling subscription deletion: {e}")