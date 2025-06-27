import re
import logging
from sqlmodel import Session
from app.models.carrier_data import CarrierData
from app.models.engagement import CarrierChangeItem, CarrierEngagementStatus
from datetime import datetime
from fastapi import HTTPException

# Set up a module-level logger
logger = logging.getLogger(__name__)

def get_engagement_data(db: Session, 
                        org_id: str = None,
                        offset: int = None, 
                        limit: int = None,
                        carrier_interested: bool = None,
                        carrier_contacted: bool = None) -> list[CarrierEngagementStatus]:
    """Retrieves carrier engagement statuses from the database."""

    if org_id:
        carriers = db.query(CarrierEngagementStatus).filter(CarrierEngagementStatus.org_id == org_id)
    else:
        logger.info("🔍 Fetching all carrier engagement status without group filtering.")
        carriers = db.query(CarrierEngagementStatus)

    if carrier_interested is not None:
        logger.info("🔍 Filtering carrier data for interested carriers.")
        carriers = carriers.filter(CarrierEngagementStatus.carrier_interested == carrier_interested)

    if carrier_contacted is not None:
        logger.info("🔍 Filtering carrier data for contacted carriers.")
        carriers = carriers.filter(CarrierEngagementStatus.carrier_contacted == carrier_contacted)

    # Order by timestamp descending (newest first)
    carriers = carriers.order_by(CarrierEngagementStatus.created_at.desc())

    if offset is not None and limit is not None:
        logger.info(f"🔍 Applying offset: offset={offset}, limit={limit}")
        carriers = carriers.offset(offset).limit(limit)
    else:
        logger.info("🔍 Offset is disabled.")

    carriers = carriers.all()

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