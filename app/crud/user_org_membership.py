import logging
from sqlmodel import Session
from app.models.user_org_membership import AppUser, AppOrg, UserOrgMembership
from fastapi import HTTPException

# Set up a module-level logger
logger = logging.getLogger(__name__)

def save_user_org_membership(db: Session, login_info) -> AppUser:
    """Save a User record to the database."""
    try:

        user_id = login_info['userinfo']['sub']
        user_email = login_info['userinfo']['email']

        user_record = AppUser(
            user_id=user_id,
            user_email=user_email,
            name=login_info.get('name', None),
            first_name=login_info.get('given_name', None),
            last_name=login_info.get('family_name', None)
        )
        org_record = AppOrg(
            org_id=login_info.get('org_id', user_id),
            org_name=login_info.get('org_name', user_email)
        )
        membership_record = UserOrgMembership(
            user_id=user_record.user_id, 
            org_id=org_record.org_id
        )
        
        #check if records already exist
        existing_user = db.query(AppUser).filter(AppUser.user_id == user_record.user_id).first()
        existing_org = db.query(AppOrg).filter(AppOrg.org_id == org_record.org_id).first()
        existing_membership = db.query(UserOrgMembership).filter(UserOrgMembership.user_id == user_record.user_id,
                                                                 UserOrgMembership.org_id == org_record.org_id).first()
        if existing_user:
            logger.info(f"🔍 User with ID {user_record.user_id} already exists. Updating fields.")
            # update fields
            for key, value in user_record.dict().items():
                setattr(existing_user, key, value)
            user_record = existing_user
        if existing_org:
            logger.info(f"🔍 Org with ID {org_record.org_id} already exists. Updating fields.")
            # update fields
            for key, value in org_record.dict().items():
                setattr(existing_org, key, value)
            org_record = existing_org
        if existing_membership:
            logger.info(f"🔍 Membership for user {user_record.user_id} and org {org_record.org_id} already exists. Skipping.")
            membership_record = existing_membership
        
        # Commit User, Org and Membership records in a single transaction
        logger.info("🔍 Saving App, Org, and membership to the database.")
        db.add(user_record)
        db.add(org_record)
        db.add(membership_record)

        db.commit()

        db.refresh(user_record)
        db.refresh(org_record)
        db.refresh(membership_record)

        logger.info(f"✅ User {user_record.user_id}, Org {org_record.org_id}, and memberships saved.")
        
        # Create free subscription for new users
        try:
            from app.crud.subscription import get_user_subscription, create_subscription, get_subscription_plans
            from app.models.subscription import SubscriptionCreate
            
            # Check if user already has a subscription
            existing_subscription = get_user_subscription(db, user_record.user_id, org_record.org_id)
            if not existing_subscription:
                # Get free plan (assuming plan ID 1 is free)
                plans = get_subscription_plans(db)
                free_plan = next((p for p in plans if p.price_cents == 0), None)
                
                if free_plan:
                    subscription_data = SubscriptionCreate(
                        user_id=user_record.user_id,
                        org_id=org_record.org_id,
                        plan_id=free_plan.id
                    )
                    create_subscription(db, subscription_data)
                    logger.info(f"✅ Created free subscription for user {user_record.user_id}")
                else:
                    logger.warning("No free plan found to assign to new user")
        except Exception as e:
            logger.error(f"Warning: Failed to create free subscription for user {user_record.user_id}: {e}")
            # Don't fail the entire user creation process if subscription creation fails
        
        return user_record
    except Exception as e:
        logger.error(f"❌ Error saving User, Org, Membership: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    