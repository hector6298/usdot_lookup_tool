import re
import logging
from sqlmodel import Session
from sqlalchemy import asc, desc
from app.models.carrier_data import CarrierData
from app.models.engagement import CarrierChangeItem, CarrierEngagementStatus
from app.models.sobject_sync_status import SObjectSyncStatus
from datetime import datetime
from fastapi import HTTPException

# Set up a module-level logger
logger = logging.getLogger(__name__)

def get_engagement_data(db: Session, 
                        org_id: str = None,
                        offset: int = None, 
                        limit: int = None,
                        carrier_interested: bool = None,
                        carrier_contacted: bool = None,
                        usdot: str = None,
                        legal_name: str = None,
                        sf_sync_status: str = None,
                        sort_by: str = None,
                        sort_order: str = "desc") -> list[CarrierEngagementStatus]:
    """Retrieves carrier engagement statuses from the database."""

    # Start with base query and join with carrier_data for filtering and sorting
    query = db.query(CarrierEngagementStatus).join(CarrierData, CarrierEngagementStatus.usdot == CarrierData.usdot)
    
    # Left join with sync status for filtering and sorting
    query = query.outerjoin(SObjectSyncStatus, 
                           (CarrierEngagementStatus.usdot == SObjectSyncStatus.usdot) & 
                           (CarrierEngagementStatus.org_id == SObjectSyncStatus.org_id))

    if org_id:
        query = query.filter(CarrierEngagementStatus.org_id == org_id)
    else:
        logger.info("🔍 Fetching all carrier engagement status without group filtering.")

    # Apply filters
    if carrier_interested is not None:
        logger.info("🔍 Filtering carrier data for interested carriers.")
        query = query.filter(CarrierEngagementStatus.carrier_interested == carrier_interested)

    if carrier_contacted is not None:
        logger.info("🔍 Filtering carrier data for contacted carriers.")
        query = query.filter(CarrierEngagementStatus.carrier_contacted == carrier_contacted)
        
    if usdot:
        logger.info(f"🔍 Filtering carrier data for USDOT: {usdot}")
        query = query.filter(CarrierEngagementStatus.usdot.ilike(f"%{usdot}%"))
        
    if legal_name:
        logger.info(f"🔍 Filtering carrier data for legal name: {legal_name}")
        query = query.filter(CarrierData.legal_name.ilike(f"%{legal_name}%"))
        
    if sf_sync_status:
        logger.info(f"🔍 Filtering carrier data for sync status: {sf_sync_status}")
        if sf_sync_status.lower() == "not_synced":
            query = query.filter(SObjectSyncStatus.sync_status.is_(None))
        else:
            query = query.filter(SObjectSyncStatus.sync_status == sf_sync_status.upper())

    # Apply sorting
    sort_order_func = desc if sort_order.lower() == "desc" else asc
    
    if sort_by:
        if sort_by == "usdot":
            query = query.order_by(sort_order_func(CarrierEngagementStatus.usdot))
        elif sort_by == "legal_name":
            query = query.order_by(sort_order_func(CarrierData.legal_name))
        elif sort_by == "phone":
            query = query.order_by(sort_order_func(CarrierData.phone))
        elif sort_by == "created_at":
            query = query.order_by(sort_order_func(CarrierEngagementStatus.created_at))
        elif sort_by == "sf_sync_status":
            query = query.order_by(sort_order_func(SObjectSyncStatus.sync_status))
        else:
            # Default to created_at desc
            query = query.order_by(CarrierEngagementStatus.created_at.desc())
    else:
        # Default sorting by created_at descending (newest first)
        query = query.order_by(CarrierEngagementStatus.created_at.desc())

    if offset is not None and limit is not None:
        logger.info(f"🔍 Applying offset: offset={offset}, limit={limit}")
        query = query.offset(offset).limit(limit)
    else:
        logger.info("🔍 Offset is disabled.")

    carriers = query.all()

    logger.info(f"✅ Found {len(carriers)} carrier engagement records.")

    return carriers


def generate_engagement_records(db: Session, 
                                usdot_numbers: list[int], 
                                user_id: str, 
                                org_id:str) -> list[CarrierData]:
    """Generates engagement records for the given USDOT numbers."""
    logger.info("🔍 Generating engagement records for carriers."
                f"USDOT numbers: {usdot_numbers}, User ID: {user_id}, Org ID: {org_id}")
    engagement_records = []
    for usdot in usdot_numbers:
        try:

            # Check if the engagement record already exists
            existing_engagement = db.query(CarrierEngagementStatus)\
                                     .filter(CarrierEngagementStatus.usdot == usdot,
                                             CarrierEngagementStatus.org_id == org_id)\
                                     .first()
            if existing_engagement:
                logger.info(f"🔍 Engagement record already exists for USDOT: {usdot} and ORG {org_id}. Skipping.")
                continue

            # Create a new engagement record
            engagement_record = CarrierEngagementStatus(
                usdot=usdot,
                org_id=org_id,
                user_id=user_id,
            )
            engagement_records.append(engagement_record)

        except Exception as e:
            logger.error(f"❌ Error generating engagement record for USDOT {usdot}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        
    return engagement_records
    
def save_engagement_records_bulk(db: Session,
                                 usdot_numbers: list[int], 
                                 user_id: str, 
                                 org_id:str) -> None:
    """Saves multiple engagement records to the database."""
    engagement_records = generate_engagement_records(db, usdot_numbers, user_id, org_id)
    try:
        logger.info(f"🔍 Saving {len(engagement_records)} engagement records to the database.")
        db.add_all(engagement_records)
        db.commit()

        # Refresh all records to get the latest state
        for record in engagement_records:
            db.refresh(record)

        logger.info("✅ All engagement records saved successfully.")
        return engagement_records
    except Exception as e:
        logger.error(f"❌ Error saving engagement records: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))



def update_carrier_engagement(db: Session, carrier_change_item: dict) -> CarrierEngagementStatus:
    """Updates carrier interests based on user input."""

    carrier_change_item = CarrierChangeItem.model_validate(carrier_change_item)
    dot_number = carrier_change_item.usdot
    field = carrier_change_item.field
    value = carrier_change_item.value

    try:
        logger.info(f"Updating carrier interest for DOT number: {dot_number}, field: {field}, value: {value}, type: {type(value)}")

        # Check if the carrier exists
        carrier = db.query(CarrierEngagementStatus)\
                    .filter(CarrierEngagementStatus.usdot == dot_number)\
                    .first()
        if not carrier:
            logger.warning(f"⚠ No carrier found for DOT number: {dot_number}")
            return None

        # Update the specified fields
        if field in ["carrier_interested", "carrier_contacted", "carrier_followed_up", "carrier_emailed"]:

            setattr(carrier, field, value)
            setattr(carrier, field + "_timestamp", datetime.now())
            setattr(carrier, field + "_by_user_id", carrier_change_item.user_id)
        elif field in CarrierEngagementStatus.__table__.columns and type(value) == str:
            setattr(carrier, field, value)
        else:
            logger.error(f"❌ Invalid field or value type for field: {field}, value: {value}")
            raise HTTPException(status_code=400, detail="Invalid field or value type")
        
        db.commit()
        db.refresh(carrier)
        logger.info(f"✅ Carrier interests updated for DOT number: {dot_number}")
    except Exception as e:
        logger.error(f"❌ Error updating carrier interests for DOT {dot_number}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    return carrier