import logging
from sqlmodel import Session
from app.models.carrier_data import CarrierData, CarrierDataCreate
from app.crud.ocr_results import get_ocr_results
from app.crud.engagement import generate_engagement_records
from fastapi import HTTPException

# Set up a module-level logger
logger = logging.getLogger(__name__)

def get_carrier_data(db: Session, 
                     org_id: str = None,
                     offset: int = None, 
                     limit: int = None
                     ) -> dict:
    """Retrieves carrier data from the database."""

    if org_id:
        logger.info(f"🔍 Filtering carrier data by org ID: {org_id}")
        user_ocr_results = get_ocr_results(db, 
                                           org_id=org_id,
                                           valid_dot_only=True)
        dot_numbers = [result.dot_reading for result in user_ocr_results]
        carriers = db.query(CarrierData).filter(CarrierData.usdot.in_(dot_numbers))
    else:
        logger.info("🔍 Fetching all carrier data without user filtering.")
        carriers = db.query(CarrierData)

    if offset is not None and limit is not None:
        logger.info(f"🔍 Applying offset: offset={offset}, limit={limit}")
        carriers = carriers.offset(offset).limit(limit)
    else:
        logger.info("🔍 Offset is disabled.")

    carriers = carriers.all()
    logger.info(f"✅ Found {len(carriers)} carrier records.")

    return carriers


# Carrier CRUD operations
def get_carrier_data_by_dot(db: Session, dot_number: str) -> CarrierData:
    """Retrieves carrier data by DOT number."""
    logger.info(f"🔍 Searching for carrier with USDOT: {dot_number}")
    carrier = db.query(CarrierData).filter(CarrierData.usdot == dot_number).first()

    if carrier:
        logger.info(f"✅ Carrier found: {carrier.legal_name}")
    else:
        logger.warning(f"⚠ Carrier with USDOT {dot_number} not found.")

    return carrier

def save_carrier_data(db: Session, carrier_data: CarrierDataCreate) -> CarrierData:
    """Saves carrier data to the database, performing upsert based on DOT number."""
    logger.info("🔍 Saving carrier data to the database.")
    try:
        carrier_record = CarrierData.model_validate(carrier_data)

        # Check if the carrier with the same USDOT number already exists
        existing_carrier = db.query(CarrierData).filter(CarrierData.usdot == carrier_data.usdot).first()
        if existing_carrier:
            logger.info(f"🔍 Carrier with USDOT {carrier_data.usdot} exists. Updating record.")
            for key, value in carrier_record.dict().items():
                setattr(existing_carrier, key, value)
            db.commit()
            db.refresh(existing_carrier)
            logger.info(f"✅ Carrier data updated: {existing_carrier.legal_name}")
            return existing_carrier
        else:
            logger.info(f"🔍 Carrier with USDOT {carrier_data.usdot} does not exist. Inserting new record.")
            db.add(carrier_record)
            db.commit()
            db.refresh(carrier_record)
            logger.info(f"✅ Carrier data saved: {carrier_record.legal_name}")
            return carrier_record

    except Exception as e:
        logger.exception(f"❌ Error saving carrier data: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    

def generate_carrier_records(db: Session, 
                             carrier_data: list[CarrierDataCreate]) -> list[CarrierData]:
    """Saves multiple carrier data records to the database, performing upserts."""
    logger.info("🔍 Saving multiple carrier data records to the database.")
    carrier_records = []
    
    for data in carrier_data:
        try:
            logger.info("🔍 Validating carrier data.")
            carrier_record = CarrierData.model_validate(data)

            # Check if the carrier with the same USDOT number already exists
            existing_carrier = db.query(CarrierData).filter(CarrierData.usdot == data.usdot).first()
            
            if existing_carrier:
                logger.info(f"🔍 Carrier with USDOT {data.usdot} exists. Updating record.")
                for key, value in carrier_record.dict().items():
                    setattr(existing_carrier, key, value)
                carrier_records.append(existing_carrier)
            else:
                logger.info(f"🔍 Carrier with USDOT {data.usdot} does not exist. Inserting new record.")
                carrier_records.append(carrier_record)

        except Exception as e:
            logger.error(f"❌ Error processing carrier data: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    return carrier_records


def save_carrier_data_bulk(db: Session, 
                           carrier_data: list[CarrierDataCreate],
                           user_id: str,
                           org_id: str) -> list[CarrierData]:
    """Saves multiple carrier data records to the database, performing upserts."""
    usdot_numbers = [data.usdot for data in carrier_data if data.lookup_success_flag]
    carrier_records = generate_carrier_records(db, carrier_data)
    engagement_records = generate_engagement_records(db,
                                                    usdot_numbers,
                                                    user_id=user_id,
                                                    org_id=org_id)
    if carrier_records and engagement_records and len(carrier_records) == len(engagement_records):
        try:
            logger.info(f"🔍 Saving {len(carrier_records)} carrier records to the database in bulk.")
            db.add_all(carrier_records)
            db.add_all(engagement_records)
            db.commit()
            
            
            # Refresh all records to get the latest state
            for carrier_record, engagement_record in zip(carrier_records, engagement_records):
                db.refresh(carrier_record)
                db.refresh(engagement_record)

            logger.info("✅ All carrier records saved successfully.")
            return carrier_records
        except Exception as e:
            logger.error(f"❌ Error saving carrier records in bulk: {e}")
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))
    else:
        logger.warning("⚠ No valid carrier records to save.")
    return []