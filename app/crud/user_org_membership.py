import logging
from sqlmodel import Session, select
from app.models.user_org_membership import AppUser, AppOrg, UserOrgMembership
from fastapi import HTTPException

# Set up a module-level logger
logger = logging.getLogger(__name__)

def save_user_org_membership(db: Session, login_info) -> AppUser:
    """Save a User record to the database."""
    try:

        user_id = login_info['sub']
        user_email = login_info['email']

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
    except Exception as e:
        logger.error(f"❌ Error saving User, Org, Membership: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    

def get_sf_domain_by_org_id(org_id: str, db: Session) -> str:
    """Get Salesforce domain for the organization."""
    try:
        statement = select(AppOrg).where(AppOrg.org_id == org_id)
        org = db.exec(statement).first()

        if org and org.sf_domain:
            logger.info(f"🔍 Found Salesforce domain for org {org_id}: {org.sf_domain}")
            return org.sf_domain
        
        logger.warning(f"No Salesforce domain configured for organization {org_id}")
        return None

    except Exception as e:
        logger.error(f"Error getting Salesforce domain for org {org_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


def save_sf_domain_for_org(db: Session, org_id: str, sf_domain: str) -> AppOrg:
    """Save Salesforce domain for an organization."""
    try:
        statement = select(AppOrg).where(AppOrg.org_id == org_id)
        org = db.exec(statement).first()
        
        if not org:
            logger.error(f"Organization {org_id} not found")
            raise HTTPException(status_code=404, detail="Organization not found")
        
        org.sf_domain = sf_domain
        db.add(org)
        db.commit()
        db.refresh(org)
        
        logger.info(f"✅ Salesforce domain {sf_domain} saved for org {org_id}")
        return org
        
    except Exception as e:
        logger.error(f"❌ Error saving Salesforce domain for org {org_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))