import logging
from sqlmodel import Session, select
from app.models.carrier_data import CarrierData, CarrierDataCreate
from app.models.sobject_sync_status import CRMSyncStatus
from app.crud.sobject_sync_status import upsert_crm_sync_status
from fastapi import HTTPException
from datetime import datetime, timezone

# Set up a module-level logger
logger = logging.getLogger(__name__)

def get_carrier_data(db: Session, 
                     org_id: str = None,
                     offset: int = None, 
                     limit: int = None
                     ) -> dict:
    """Retrieves carrier data from the database using CRM sync status."""

    if org_id:
        logger.info(f"🔍 Filtering carrier data by org ID: {org_id}")
        # Get USDOTs from CRM sync status instead of OCR results
        
        query = select(CRMSyncStatus).where(CRMSyncStatus.org_id == org_id)
        if offset is not None and limit is not None:
            logger.info(f"🔍 Applying offset: offset={offset}, limit={limit}")
            query = query.offset(offset).limit(limit)
        
        sync_records = db.exec(query).all()
        dot_numbers = [record.usdot for record in sync_records]
        
        if dot_numbers:
            carriers = db.exec(
                select(CarrierData).where(CarrierData.usdot.in_(dot_numbers))
            ).all()
        else:
            carriers = []
    else:
        logger.info("🔍 Fetching all carrier data without user filtering.")
        query = select(CarrierData)
        if offset is not None and limit is not None:
            logger.info(f"🔍 Applying offset: offset={offset}, limit={limit}")
            query = query.offset(offset).limit(limit)
        
        carriers = db.exec(query).all()

    logger.info(f"✅ Found {len(carriers)} carrier records.")

    return carriers


# Carrier CRUD operations
def get_carrier_data_by_dot(db: Session, dot_number: str) -> CarrierData:
    """Retrieves carrier data by DOT number."""
    logger.info(f"🔍 Searching for carrier with USDOT: {dot_number}")
    carrier = db.exec(
        select(CarrierData).where(CarrierData.usdot == dot_number)
    ).first()

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
        existing_carrier = db.exec(
            select(CarrierData).where(CarrierData.usdot == carrier_data.usdot)
        ).first()
        if existing_carrier:
            logger.info(f"🔍 Carrier with USDOT {carrier_data.usdot} exists. Updating record.")
            for key, value in carrier_record.model_dump().items():
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
            existing_carrier = db.exec(
                select(CarrierData).where(CarrierData.usdot == data.usdot)
            ).first()
            
            if existing_carrier:
                logger.info(f"🔍 Carrier with USDOT {data.usdot} exists. Updating record.")
                for key, value in carrier_record.model_dump().items():
                    setattr(existing_carrier, key, value)
                carrier_records.append(existing_carrier)
            else:
                logger.info(f"🔍 Carrier with USDOT {data.usdot} does not exist. Inserting new record.")
                carrier_records.append(carrier_record)

        except Exception as e:
            logger.error(f"❌ Error processing carrier data: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    return carrier_records


def generate_crm_sync_records(db: Session, 
                              usdot_numbers: list[int], 
                              user_id: str, 
                              org_id: str) -> list:
    """Generates CRM sync status records for the given USDOT numbers."""
    logger.info("🔍 Generating CRM sync status records for carriers."
                f"USDOT numbers: {usdot_numbers}, User ID: {user_id}, Org ID: {org_id}")
    
    sync_records = []
    
    for usdot in usdot_numbers:
        try:
            # Check if the CRM sync record already exists
            existing_sync = db.exec(
                select(CRMSyncStatus).where(
                    CRMSyncStatus.usdot == usdot,
                    CRMSyncStatus.org_id == org_id
                )
            ).first()
            
            if existing_sync:
                logger.info(f"🔍 CRM sync record already exists for USDOT: {usdot} and ORG {org_id}. Updating.")
                existing_sync.user_id = user_id
                existing_sync.updated_at = datetime.now(timezone.utc)
                sync_records.append(existing_sync)
            else:
                # Create a new CRM sync record
                sync_record = CRMSyncStatus(
                    usdot=usdot,
                    org_id=org_id,
                    user_id=user_id,
                    sobject_sync_status="PENDING"  # Default status for new carriers
                )
                sync_records.append(sync_record)

        except Exception as e:
            logger.error(f"❌ Error generating CRM sync record for USDOT {usdot}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        
    return sync_records


def save_carrier_data_bulk(db: Session, 
                           carrier_data: list[CarrierDataCreate],
                           user_id: str,
                           org_id: str) -> list[CarrierData]:
    """Saves multiple carrier data records to the database, performing upserts with CRM sync status in single transaction."""
    usdot_numbers = [data.usdot for data in carrier_data if data.lookup_success_flag]
    carrier_records = generate_carrier_records(db, carrier_data)
    sync_records = generate_crm_sync_records(db, usdot_numbers, user_id=user_id, org_id=org_id)
    
    if carrier_records and sync_records and len(carrier_records) == len(sync_records):
        try:
            logger.info(f"🔍 Saving {len(carrier_records)} carrier records and {len(sync_records)} CRM sync records to the database in bulk.")
            
            # Single transaction for both carrier data and CRM sync status
            db.add_all(carrier_records)
            db.add_all(sync_records)
            db.commit()
            
            # Refresh all records to get the latest state
            for carrier_record, sync_record in zip(carrier_records, sync_records):
                db.refresh(carrier_record)
                db.refresh(sync_record)

            logger.info("✅ All carrier records and CRM sync records saved successfully.")
            return carrier_records
        except Exception as e:
            logger.error(f"❌ Error saving carrier records in bulk: {e}")
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))
    else:
        logger.warning("⚠ No valid carrier records to save.")
    return []