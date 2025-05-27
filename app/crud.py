import re
import logging
from sqlmodel import Session
from app.models import OCRResult, OCRResultCreate, CarrierData, CarrierChangeItem, CarrierEngagementStatus
from datetime import datetime
from flatten_dict import flatten
from fastapi import HTTPException
from sqlalchemy.orm import joinedload

# Set up a module-level logger
logger = logging.getLogger(__name__)

def save_ocr_results_bulk(db: Session, ocr_results: list[OCRResultCreate]) -> list[OCRResult]:
    """Saves multiple OCR results to the database."""
    logger.info("🔍 Saving multiple OCR results to the database.")
    ocr_records = []
    for ocr_result in ocr_results:
        try:
            # Extract the 10-digit number following "DOT"
            logger.info("🔍 Extracting DOT number from OCR result.")
            match = re.search(r'\b(?:USDOT|DOT)[- ]?(\d+)\b', ocr_result.extracted_text)
            dot_reading = match.group(1) if match else None

            if not dot_reading:
                logger.warning("❌ No DOT number found in OCR result.")
                continue
            else:
                logger.info(f"✅ DOT number extracted: {dot_reading}")

            # Validate and update the OCR result
            ocr_record = OCRResult.model_validate(
                ocr_result, 
                update={
                    "timestamp": datetime.now(),
                    "dot_reading": dot_reading
                }
            )

            ocr_records.append(ocr_record)

        except Exception as e:
            logger.error(f"❌ Error processing OCR result: {e}")
    
    if ocr_records:
        try:
            logger.info(f"🔍 Saving {len(ocr_records)} OCR results to the database in bulk.")
            db.add_all(ocr_records)
            db.commit()

            # Refresh all records to get the latest state
            for record in ocr_records:
                db.refresh(record)

            logger.info("✅ All OCR results saved successfully.")
            return ocr_records
        except Exception as e:
            logger.error(f"❌ Error saving OCR results in bulk: {e}")
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))
    else:
        logger.warning("⚠ No valid OCR results to save.")
    return []


# OCR CRUD operations
def save_single_ocr_result(db: Session, ocr_result: OCRResultCreate) -> OCRResult:
    """Saves OCR result to the database."""
    # Extract the 10-digit number following "DOT"
    logger.info("🔍 Extracting DOT number from OCR result.")
    match = re.search(r'\b(?:USDOT|DOT)[- ](\d+)\b', ocr_result.extracted_text)
    dot_reading = match.group(1) if match else None

    if not dot_reading:
        logger.error("❌ No DOT number found in OCR result.")
    else:
        logger.info(f"✅ DOT number extracted: {dot_reading}")

    try:
        logger.info("🔍 Performing OCRResult data validation.")
        # Validate and update the OCR result
        ocr_record = OCRResult.model_validate(
            ocr_result, 
            update={
                "timestamp": datetime.now(),
                "dot_reading": dot_reading
            }
        )

        logger.info("🔍 Saving OCR result to the database.")
        db.add(ocr_record)
        db.commit()
        db.refresh(ocr_record)

        logger.info(f"✅ OCR result saved with ID: {ocr_record.id}")
        return ocr_record

    except Exception as e:
        logger.error(f"❌ Error saving OCR result: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

def get_ocr_result_by_id(db: Session, result_id: int) -> OCRResult:
    """Retrieves a single OCR result by ID."""
    logger.info(f"🔍 Fetching OCR result with ID: {result_id}")
    result = db.query(OCRResult).filter(OCRResult.id == result_id).first()

    if result:
        logger.info(f"✅ OCR result found: {result.extracted_text}")
    else:
        logger.warning(f"⚠ No OCR result found with ID: {result_id}")

    return result

def get_ocr_results(db: Session, 
                    org_id: str = None,
                    offset: int = None, 
                    limit: int = None, 
                    valid_dot_only: bool = True,
                    eager_relations:bool = False) -> dict:
    """Retrieves OCR results with a valid DOT number."""

    query = db.query(OCRResult)
    if eager_relations:
        logger.info("🔍 Eager loading carrier data for OCR results.")
        query = query.options(joinedload(OCRResult.carrier_data))
        
    if org_id:
        logger.info(f"🔍 Filtering OCR results by org ID: {org_id}")
        query = query.filter(OCRResult.org_id == org_id)

    if valid_dot_only:
        logger.info("🔍 Filtering OCR results with a valid DOT number.")
        query = query.filter(OCRResult.dot_reading != None)
    
    if offset is not None and limit is not None:
        logger.info(f"🔍 Applying range to OCR results: offset={offset}, limit={limit}")
        query = query.offset(offset).limit(limit)
    else:
        logger.info("🔍 Returning all OCR results")
    
    results = query.all()
        
    logger.info(f"✅ Found {len(results)} OCR results.")
    return results

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

    if offset is not None and limit is not None:
        logger.info(f"🔍 Applying offset: offset={offset}, limit={limit}")
        carriers = carriers.offset(offset).limit(limit)
    else:
        logger.info("🔍 Offset is disabled.")

    carriers = carriers.all()

    logger.info(f"✅ Found {len(carriers)} carrier engagement records.")

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

def save_carrier_data(db: Session, carrier_data: dict) -> CarrierData:
    """Saves carrier data to the database, performing upsert based on DOT number."""
    logger.info("🔍 Saving carrier data to the database.")

    # remove us_inspections key from carrier_data
    carrier_data.pop('us_inspections', None)
    carrier_data = flatten(carrier_data, reducer='underscore')

    try:
        logger.info("🔍 Validating carrier data.")
        carrier_record = CarrierData.model_validate(
            carrier_data,
            update={
                "operation_classification": ', '.join(carrier_data["operation_classification"]),
                "carrier_operation": ', '.join(carrier_data["carrier_operation"]),
                "cargo_carried": ', '.join(carrier_data["cargo_carried"])
            }
        )

        # Check if the carrier with the same USDOT number already exists
        existing_carrier = db.query(CarrierData).filter(CarrierData.usdot == carrier_data["usdot"]).first()
        if existing_carrier:
            logger.info(f"🔍 Carrier with USDOT {carrier_data['usdot']} exists. Updating record.")
            for key, value in carrier_record.dict().items():
                setattr(existing_carrier, key, value)
            db.commit()
            db.refresh(existing_carrier)
            logger.info(f"✅ Carrier data updated: {existing_carrier.legal_name}")
            return existing_carrier
        else:
            logger.info(f"🔍 Carrier with USDOT {carrier_data['usdot']} does not exist. Inserting new record.")
            db.add(carrier_record)
            db.commit()
            db.refresh(carrier_record)
            logger.info(f"✅ Carrier data saved: {carrier_record.legal_name}")
            return carrier_record

    except Exception as e:
        logger.exception(f"❌ Error saving carrier data: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

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
                org_id=org_id
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


def generate_carrier_records(db: Session, 
                             carrier_data: list[dict]) -> list[CarrierData]:
    """Saves multiple carrier data records to the database, performing upserts."""
    logger.info("🔍 Saving multiple carrier data records to the database.")
    carrier_records = []
    
    for data in carrier_data:
        try:
            # remove us_inspections key from carrier_data
            data.pop('us_inspections', None)
            data = flatten(data, reducer='underscore')

            logger.info("🔍 Validating carrier data.")
            carrier_record = CarrierData.model_validate(
                data,
                update={
                    "operation_classification": ', '.join(data["operation_classification"]),
                    "carrier_operation": ', '.join(data["carrier_operation"]),
                    "cargo_carried": ', '.join(data["cargo_carried"])
                }
            )

            # Check if the carrier with the same USDOT number already exists
            existing_carrier = db.query(CarrierData).filter(CarrierData.usdot == data["usdot"]).first()
            if existing_carrier:
                logger.info(f"🔍 Carrier with USDOT {data['usdot']} exists. Updating record.")
                for key, value in carrier_record.dict().items():
                    setattr(existing_carrier, key, value)
                carrier_records.append(existing_carrier)
            else:
                logger.info(f"🔍 Carrier with USDOT {data['usdot']} does not exist. Inserting new record.")
                carrier_records.append(carrier_record)

        except Exception as e:
            logger.error(f"❌ Error processing carrier data: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    return carrier_records


def save_carrier_data_bulk(db: Session, 
                           carrier_data: list[dict],
                           org_id: str) -> list[CarrierData]:
    """Saves multiple carrier data records to the database, performing upserts."""
    usdot_numbers = [data["usdot"] for data in carrier_data]
    carrier_records = generate_carrier_records(db, carrier_data)
    engagement_records = generate_engagement_records(db,
                                                    usdot_numbers,
                                                    user_id=org_id,
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