import os
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.routes.auth import verify_login
from app.helpers import stripe as stripe_helper

# Set up logging
logger = logging.getLogger(__name__)

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
        plans = stripe_helper.get_subscription_plans()
        return {"plans": plans}
    except Exception as e:
        logger.error(f"Error fetching plans: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch subscription plans")


@router.get("/subscription")
async def get_current_subscription(
    request: Request,
    _: dict = Depends(verify_login)
):
    """Get current user's subscription from Stripe."""
    try:
        user_id = request.session['userinfo']['sub']
        org_id = request.session['userinfo'].get('org_id', user_id)
        
        # Get subscription details directly from Stripe
        subscription_details = stripe_helper.get_subscription_details(user_id, org_id)
        return subscription_details
        
    except Exception as e:
        logger.error(f"Error fetching subscription: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch subscription")


@router.get("/usage")
async def get_current_usage(
    request: Request,
    _: dict = Depends(verify_login)
):
    """Get current usage from Stripe."""
    try:
        user_id = request.session['userinfo']['sub']
        org_id = request.session['userinfo'].get('org_id', user_id)
        
        # Get usage data directly from Stripe
        usage_data = stripe_helper.get_user_usage(user_id, org_id)
        return usage_data
        
    except Exception as e:
        logger.error(f"Error fetching usage: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch usage")


@router.post("/subscribe/{price_id}")
async def subscribe_to_plan(
    price_id: str,
    request: Request,
    _: dict = Depends(verify_login)
):
    """Subscribe user to a metered billing plan using Stripe price ID."""
    try:
        user_id = request.session['userinfo']['sub']
        org_id = request.session['userinfo'].get('org_id', user_id)
        user_email = request.session['userinfo'].get('email', f'{user_id}@example.com')
        
        # Create subscription directly through Stripe
        subscription = stripe_helper.create_subscription(user_id, org_id, user_email, price_id)
        
        if not subscription:
            raise HTTPException(status_code=400, detail="Failed to create subscription")
        
        return {
            "stripe_subscription_id": subscription.id,
            "status": subscription.status,
            "customer_id": subscription.customer
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating subscription: {e}")
        raise HTTPException(status_code=500, detail="Failed to create subscription")


@router.get("/invoices")
async def get_user_invoices(
    request: Request,
    _: dict = Depends(verify_login)
):
    """Get user's Stripe invoices."""
    try:
        user_id = request.session['userinfo']['sub']
        org_id = request.session['userinfo'].get('org_id', user_id)
        
        # Get invoices directly from Stripe
        invoices = stripe_helper.get_user_invoices(user_id, org_id)
        return {"invoices": invoices}
        
    except Exception as e:
        logger.error(f"Error fetching invoices: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch invoices")


@router.post("/cancel-subscription")
async def cancel_subscription(
    request: Request,
    _: dict = Depends(verify_login)
):
    """Cancel user's subscription."""
    try:
        user_id = request.session['userinfo']['sub']
        org_id = request.session['userinfo'].get('org_id', user_id)
        
        # Cancel subscription directly through Stripe
        cancelled_subscription = stripe_helper.cancel_subscription(user_id, org_id)
        
        if not cancelled_subscription:
            raise HTTPException(status_code=404, detail="No active subscription found")
        
        return {
            "message": "Subscription will be cancelled at the end of the current period",
            "cancel_at": cancelled_subscription.cancel_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error canceling subscription: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel subscription")