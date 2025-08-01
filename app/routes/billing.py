import os
import logging
import stripe
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session
from app.database import get_db
from app.routes.auth import verify_login
from app.models.subscription import (
    SubscriptionPlan, Subscription, UsageQuota,
    SubscriptionCreate, SubscriptionResponse, UsageQuotaResponse
)
from app.crud.subscription import (
    get_subscription_plans, get_user_subscription, create_subscription,
    get_current_usage_quota, initialize_default_plans
)

# Set up logging
logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = os.environ.get('STRIPE_SB_SK', 'sk_test_')

# Initialize templates
templates = Jinja2Templates(directory="app/templates")

# Initialize APIRouter
router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/", response_class=HTMLResponse)
async def subscription_page(
    request: Request,
    _: dict = Depends(verify_login)
):
    """Render subscription management page."""
    stripe_public_key = os.environ.get('STRIPE_SB_PK', 'pk_test_')
    return templates.TemplateResponse(
        "subscription.html",
        {
            "request": request,
            "stripe_public_key": stripe_public_key
        }
    )


@router.get("/plans", response_model=list[SubscriptionPlan])
async def get_plans(db: Session = Depends(get_db)):
    """Get all available subscription plans."""
    try:
        # Initialize default plans if none exist
        plans = get_subscription_plans(db)
        if not plans:
            initialize_default_plans(db)
            plans = get_subscription_plans(db)
        
        return plans
    except Exception as e:
        logger.error(f"Error fetching plans: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch subscription plans")


@router.get("/subscription", response_model=SubscriptionResponse | None)
async def get_current_subscription(
    request: Request,
    db: Session = Depends(get_db),
    _: dict = Depends(verify_login)
):
    """Get current user's subscription."""
    try:
        user_id = request.session['userinfo']['sub']
        org_id = request.session['userinfo'].get('org_id', user_id)
        
        subscription = get_user_subscription(db, user_id, org_id)
        return subscription
    except Exception as e:
        logger.error(f"Error fetching subscription: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch subscription")


@router.get("/usage", response_model=UsageQuotaResponse | None)
async def get_current_usage(
    request: Request,
    db: Session = Depends(get_db),
    _: dict = Depends(verify_login)
):
    """Get current usage quota."""
    try:
        user_id = request.session['userinfo']['sub']
        org_id = request.session['userinfo'].get('org_id', user_id)
        
        usage = get_current_usage_quota(db, user_id, org_id)
        return usage
    except Exception as e:
        logger.error(f"Error fetching usage: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch usage")


@router.post("/subscribe/{plan_id}")
async def subscribe_to_plan(
    plan_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _: dict = Depends(verify_login)
):
    """Subscribe user to a plan."""
    try:
        user_id = request.session['userinfo']['sub']
        org_id = request.session['userinfo'].get('org_id', user_id)
        
        # Check if user already has a subscription
        existing = get_user_subscription(db, user_id, org_id)
        if existing:
            raise HTTPException(status_code=400, detail="User already has an active subscription")
        
        # Get plan details
        plans = get_subscription_plans(db)
        plan = next((p for p in plans if p.id == plan_id), None)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        
        # For free plan, create subscription directly
        if plan.price_cents == 0:
            subscription_data = SubscriptionCreate(
                user_id=user_id,
                org_id=org_id,
                plan_id=plan_id
            )
            subscription = create_subscription(db, subscription_data)
            return {"subscription_id": subscription.id, "status": "active"}
        
        # For paid plans, create Stripe subscription
        try:
            # Create or get Stripe customer
            user_email = request.session['userinfo'].get('email', f'{user_id}@example.com')
            
            customer = stripe.Customer.create(
                email=user_email,
                metadata={
                    'user_id': user_id,
                    'org_id': org_id
                }
            )
            
            # Create Stripe subscription (this would need a payment method)
            # For now, we'll create a subscription without payment method for demo
            stripe_subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': plan.name,
                        },
                        'unit_amount': plan.price_cents,
                        'recurring': {
                            'interval': 'month',
                        },
                    },
                }],
                metadata={
                    'user_id': user_id,
                    'org_id': org_id,
                    'plan_id': str(plan_id)
                }
            )
            
            # Create subscription in our database
            subscription_data = SubscriptionCreate(
                user_id=user_id,
                org_id=org_id,
                plan_id=plan_id
            )
            subscription = create_subscription(db, subscription_data)
            
            # Update with Stripe subscription ID
            subscription.stripe_subscription_id = stripe_subscription.id
            db.add(subscription)
            db.commit()
            
            return {
                "subscription_id": subscription.id,
                "stripe_subscription_id": stripe_subscription.id,
                "status": "active",
                "client_secret": stripe_subscription.latest_invoice
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {e}")
            raise HTTPException(status_code=400, detail=f"Payment error: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating subscription: {e}")
        raise HTTPException(status_code=500, detail="Failed to create subscription")


@router.post("/purchase-quota")
async def purchase_additional_quota(
    quota_amount: int,
    request: Request,
    db: Session = Depends(get_db),
    _: dict = Depends(verify_login)
):
    """Purchase additional quota with one-time payment."""
    try:
        user_id = request.session['userinfo']['sub']
        org_id = request.session['userinfo'].get('org_id', user_id)
        
        # Calculate price (e.g., $0.10 per additional operation)
        price_per_operation = 10  # cents
        total_price = quota_amount * price_per_operation
        
        # Create Stripe payment intent
        payment_intent = stripe.PaymentIntent.create(
            amount=total_price,
            currency='usd',
            metadata={
                'user_id': user_id,
                'org_id': org_id,
                'quota_amount': str(quota_amount),
                'type': 'quota_purchase'
            }
        )
        
        return {
            "client_secret": payment_intent.client_secret,
            "amount": total_price,
            "quota_amount": quota_amount
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {e}")
        raise HTTPException(status_code=400, detail=f"Payment error: {str(e)}")
    except Exception as e:
        logger.error(f"Error creating payment intent: {e}")
        raise HTTPException(status_code=500, detail="Failed to create payment")


@router.get("/invoices")
async def get_user_invoices(
    request: Request,
    _: dict = Depends(verify_login)
):
    """Get user's Stripe invoices."""
    try:
        user_id = request.session['userinfo']['sub']
        
        # Get Stripe customer
        customers = stripe.Customer.list(
            metadata={'user_id': user_id}
        )
        
        if not customers.data:
            return {"invoices": []}
        
        customer = customers.data[0]
        
        # Get invoices
        invoices = stripe.Invoice.list(
            customer=customer.id,
            limit=10
        )
        
        return {"invoices": invoices.data}
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {e}")
        raise HTTPException(status_code=400, detail=f"Error fetching invoices: {str(e)}")
    except Exception as e:
        logger.error(f"Error fetching invoices: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch invoices")


@router.post("/cancel-subscription")
async def cancel_subscription(
    request: Request,
    db: Session = Depends(get_db),
    _: dict = Depends(verify_login)
):
    """Cancel user's subscription."""
    try:
        user_id = request.session['userinfo']['sub']
        org_id = request.session['userinfo'].get('org_id', user_id)
        
        # Get current subscription
        subscription = get_user_subscription(db, user_id, org_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="No active subscription found")
        
        # Cancel Stripe subscription if it exists
        if subscription.stripe_subscription_id:
            try:
                stripe.Subscription.modify(
                    subscription.stripe_subscription_id,
                    cancel_at_period_end=True
                )
            except stripe.error.StripeError as e:
                logger.error(f"Error canceling Stripe subscription: {e}")
        
        # Update subscription status
        subscription.status = "cancelled"
        subscription.updated_at = datetime.utcnow()
        db.add(subscription)
        db.commit()
        
        return {"message": "Subscription cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error canceling subscription: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel subscription")