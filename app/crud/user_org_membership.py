import logging
from sqlmodel import Session
from app.models.user_org_membership import AppUser, AppOrg, UserOrgMembership, UserRole
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
        
        # Determine role: if it's the first user in the organization, make them a manager
        existing_org = db.query(AppOrg).filter(AppOrg.org_id == org_record.org_id).first()
        existing_membership_count = 0
        if existing_org:
            existing_membership_count = db.query(UserOrgMembership).filter(
                UserOrgMembership.org_id == org_record.org_id,
                UserOrgMembership.is_active == True
            ).count()
        
        # First user in the organization becomes a manager, others are regular users
        user_role = UserRole.MANAGER if existing_membership_count == 0 else UserRole.USER
        
        membership_record = UserOrgMembership(
            user_id=user_record.user_id, 
            org_id=org_record.org_id,
            role=user_role
        )
        
        # Check if records already exist
        existing_user = db.query(AppUser).filter(AppUser.user_id == user_record.user_id).first()
        if not existing_org:  # We already checked this above
            existing_org = db.query(AppOrg).filter(AppOrg.org_id == org_record.org_id).first()
        existing_membership = db.query(UserOrgMembership).filter(
            UserOrgMembership.user_id == user_record.user_id,
            UserOrgMembership.org_id == org_record.org_id
        ).first()
        
        if existing_user:
            logger.info(f"🔍 User with ID {user_record.user_id} already exists. Updating fields.")
            # Update specific fields manually to avoid enum conversion issues
            existing_user.user_email = user_record.user_email
            existing_user.name = user_record.name
            existing_user.first_name = user_record.first_name
            existing_user.last_name = user_record.last_name
            user_record = existing_user
        else:
            db.add(user_record)
            
        if existing_org:
            logger.info(f"🔍 Org with ID {org_record.org_id} already exists. Updating fields.")
            # Update specific fields manually
            existing_org.org_name = org_record.org_name
            org_record = existing_org
        else:
            db.add(org_record)
            
        if existing_membership:
            logger.info(f"🔍 Membership for user {user_record.user_id} and org {org_record.org_id} already exists. Updating role if needed.")
            # Only update role if the user should be a manager and isn't already
            if user_role == UserRole.MANAGER and existing_membership.role != UserRole.MANAGER:
                existing_membership.role = UserRole.MANAGER
            membership_record = existing_membership
        else:
            db.add(membership_record)

        # Commit User, Org and Membership records in a single transaction
        logger.info("🔍 Saving App, Org, and membership to the database.")
        
        db.commit()

        db.refresh(user_record)
        db.refresh(org_record)
        db.refresh(membership_record)

        logger.info(f"✅ User {user_record.user_id}, Org {org_record.org_id}, and memberships saved.")
        
        return user_record
        
    except Exception as e:
        logger.error(f"❌ Error saving User, Org, Membership: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))