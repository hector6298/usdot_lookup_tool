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
    SubscriptionCreate, SubscriptionResponse, UsageResponse
)
from app.crud.subscription import (
    get_active_subscription_plans, get_user_subscription_mapping,
    create_subscription_mapping, get_current_usage_from_stripe,
    get_subscription_details_from_stripe
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


@router.get("/plans")
async def get_plans():
    """Get all available subscription plans from Stripe."""
    try:
        plans = get_active_subscription_plans()
        return {"plans": plans}
    except Exception as e:
        logger.error(f"Error fetching plans: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch subscription plans")


@router.get("/subscription", response_model=SubscriptionResponse | None)
async def get_current_subscription(
    request: Request,
    db: Session = Depends(get_db),
    _: dict = Depends(verify_login)
):
    """Get current user's subscription from Stripe."""
    try:
        user_id = request.session['userinfo']['sub']
        org_id = request.session['userinfo'].get('org_id', user_id)
        
        # Get subscription mapping
        mapping = get_user_subscription_mapping(db, user_id, org_id)
        if not mapping:
            return None
        
        # Get subscription details from Stripe
        subscription_details = get_subscription_details_from_stripe(mapping)
        if not subscription_details:
            return None
        
        return SubscriptionResponse(**subscription_details)
        
    except Exception as e:
        logger.error(f"Error fetching subscription: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch subscription")


@router.get("/usage", response_model=UsageResponse | None)
async def get_current_usage(
    request: Request,
    db: Session = Depends(get_db),
    _: dict = Depends(verify_login)
):
    """Get current usage from Stripe."""
    try:
        user_id = request.session['userinfo']['sub']
        org_id = request.session['userinfo'].get('org_id', user_id)
        
        # Get subscription mapping
        mapping = get_user_subscription_mapping(db, user_id, org_id)
        if not mapping:
            return None
        
        # Get usage data from Stripe
        usage_data = get_current_usage_from_stripe(mapping)
        if not usage_data:
            return None
        
        return UsageResponse(**usage_data)
        
    except Exception as e:
        logger.error(f"Error fetching usage: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch usage")


@router.post("/subscribe/{price_id}")
async def subscribe_to_plan(
    price_id: str,
    request: Request,
    db: Session = Depends(get_db),
    _: dict = Depends(verify_login)
):
    """Subscribe user to a metered billing plan using Stripe price ID."""
    try:
        user_id = request.session['userinfo']['sub']
        org_id = request.session['userinfo'].get('org_id', user_id)
        
        # Check if user already has a subscription
        existing = get_user_subscription_mapping(db, user_id, org_id)
        if existing:
            # Verify with Stripe if subscription is actually active
            stripe_sub = stripe.Subscription.retrieve(existing.stripe_subscription_id)
            if stripe_sub.status in ['active', 'trialing', 'past_due']:
                raise HTTPException(status_code=400, detail="User already has an active subscription")
        
        # Validate that the price exists and is for a subscription plan
        try:
            price = stripe.Price.retrieve(price_id, expand=['product'])
            if not price.product.metadata.get('is_subscription_plan') == 'true':
                raise HTTPException(status_code=400, detail="Invalid subscription plan")
        except stripe.error.StripeError:
            raise HTTPException(status_code=404, detail="Subscription plan not found")
        
        # Create or get Stripe customer
        user_email = request.session['userinfo'].get('email', f'{user_id}@example.com')
        
        try:
            # Check if customer already exists
            customers = stripe.Customer.list(
                email=user_email,
                limit=1
            )
            
            if customers.data:
                customer = customers.data[0]
            else:
                customer = stripe.Customer.create(
                    email=user_email,
                    metadata={
                        'user_id': user_id,
                        'org_id': org_id
                    }
                )
            
            # Create Stripe subscription with metered billing
            stripe_subscription = stripe.Subscription.create(
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
            
            # Create subscription mapping in our database
            subscription_data = SubscriptionCreate(
                user_id=user_id,
                org_id=org_id,
                stripe_price_id=price_id
            )
            mapping = create_subscription_mapping(
                db, subscription_data, 
                stripe_subscription.id, 
                customer.id
            )
            
            return {
                "mapping_id": mapping.id,
                "stripe_subscription_id": stripe_subscription.id,
                "status": stripe_subscription.status,
                "plan_name": price.product.name
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {e}")
            raise HTTPException(status_code=400, detail=f"Payment error: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating subscription: {e}")
        raise HTTPException(status_code=500, detail="Failed to create subscription")


@router.get("/invoices")
async def get_user_invoices(
    request: Request,
    db: Session = Depends(get_db),
    _: dict = Depends(verify_login)
):
    """Get user's Stripe invoices."""
    try:
        user_id = request.session['userinfo']['sub']
        org_id = request.session['userinfo'].get('org_id', user_id)
        
        # Get subscription mapping to get customer ID
        mapping = get_user_subscription_mapping(db, user_id, org_id)
        if not mapping:
            return {"invoices": []}
        
        # Get invoices from Stripe
        invoices = stripe.Invoice.list(
            customer=mapping.stripe_customer_id,
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
        
        # Get current subscription mapping
        mapping = get_user_subscription_mapping(db, user_id, org_id)
        if not mapping:
            raise HTTPException(status_code=404, detail="No active subscription found")
        
        # Cancel Stripe subscription
        try:
            cancelled_subscription = stripe.Subscription.modify(
                mapping.stripe_subscription_id,
                cancel_at_period_end=True
            )
            
            return {
                "message": "Subscription will be cancelled at the end of the current period",
                "cancel_at": cancelled_subscription.cancel_at
            }
        except stripe.error.StripeError as e:
            logger.error(f"Error canceling Stripe subscription: {e}")
            raise HTTPException(status_code=400, detail=f"Error canceling subscription: {str(e)}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error canceling subscription: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel subscription")