import re
import logging
from sqlmodel import Session
from app.models import OCRResult, OCRResultCreate, CarrierData, CarrierChangeItem
from datetime import datetime
from flatten_dict import flatten
from fastapi import HTTPException

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
                    user_id: str = None, 
                    page: int = 1, 
                    page_size: int = 10, 
                    do_pagination: bool = True,
                    valid_dot_only: bool = True) -> dict:
    """Retrieves paginated OCR results with a valid DOT number."""

    logger.info(f"🔍 Fetching paginated OCR results (Page: {page}, Page Size: {page_size}).")
    offset = (page - 1) * page_size

    query = db.query(OCRResult)
    
    if user_id:
        logger.info(f"🔍 Filtering OCR results by user ID: {user_id}")
        query = query.filter(OCRResult.user_id == user_id)
    
    if valid_dot_only:
        logger.info("🔍 Filtering OCR results with a valid DOT number.")
        query = query.filter(OCRResult.dot_reading != None)
    
    if do_pagination:
        logger.info(f"🔍 Applying pagination: offset={offset}, limit={page_size}")
        query = query.offset(offset).limit(page_size)
    else:
        logger.info("🔍 Pagination is disabled.")
    
    results = query.all()
    total_count = query.count()
        
    if results:
        logger.info(f"✅ Found {len(results)} OCR records. Total records: {total_count}.")
    else:
        logger.warning("⚠ No OCR results found with a valid DOT number on this page.")

    return {
        "results": results,
        "total_count": total_count,
        "total_pages": ((total_count + page_size - 1) // page_size) if do_pagination else 1
    }

def get_carrier_data(db: Session, 
                     user_id: str = None, 
                     page: int = 1, 
                     page_size: int = 10,
                     do_pagination: bool = True) -> dict:
    """Retrieves paginated carrier data from the database."""
    logger.info(f"🔍 Fetching paginated carrier data (Page: {page}, Page Size: {page_size}).")
    offset = (page - 1) * page_size

    if user_id:
        logger.info(f"🔍 Filtering carrier data by user ID: {user_id}")
        user_ocr_results = get_ocr_results(db, 
                                           user_id=user_id, 
                                           do_pagination=False, 
                                           valid_dot_only=True)
        dot_numbers = [result.dot_reading for result in user_ocr_results["results"]]
        carriers = db.query(CarrierData).filter(CarrierData.usdot.in_(dot_numbers))
        total_count = len(dot_numbers)
    else:
        logger.info("🔍 Fetching all carrier data without user filtering.")
        carriers = db.query(CarrierData)
        total_count = db.query(CarrierData).count()

    if do_pagination:
        logger.info(f"🔍 Applying pagination: offset={offset}, limit={page_size}")
        carriers = carriers.offset(offset).limit(page_size)
    else:
        logger.info("🔍 Pagination is disabled.")

    carriers = carriers.all()

    if carriers:
        logger.info(f"✅ Found {len(carriers)} carrier records on page {page}. Total records: {total_count}.")
    else:
        logger.warning("⚠ No carrier data found on this page.")

    return {
        "results": carriers,
        "total_count": total_count,
        "total_pages": (total_count + page_size - 1) // page_size
    }

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

def save_carrier_data_bulk(db: Session, carrier_data: list[dict]) -> list[CarrierData]:
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
            continue

    if carrier_records:
        try:
            logger.info(f"🔍 Saving {len(carrier_records)} carrier records to the database in bulk.")
            db.add_all(carrier_records)
            db.commit()

            # Refresh all records to get the latest state
            for record in carrier_records:
                db.refresh(record)

            logger.info("✅ All carrier records saved successfully.")
            return carrier_records
        except Exception as e:
            logger.error(f"❌ Error saving carrier records in bulk: {e}")
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))
    else:
        logger.warning("⚠ No valid carrier records to save.")
    return []

def update_carrier_engagement(db: Session, carrier_change_item: dict) -> CarrierData:
    """Updates carrier interests based on user input."""

    carrier_change_item = CarrierChangeItem.model_validate(carrier_change_item)
    dot_number = carrier_change_item.usdot
    field = carrier_change_item.field
    value = carrier_change_item.value

    try:
        logger.info(f"Updating carrier interest for DOT number: {dot_number}, field: {field}, value: {value}")

        # Check if the carrier exists
        carrier = db.query(CarrierData)\
                    .filter(CarrierData.usdot == dot_number)\
                    .first()
        if not carrier:
            logger.warning(f"⚠ No carrier found for DOT number: {dot_number}")
            return None

        # Update the specified fields
        setattr(carrier, field, value)
        setattr(carrier, field + "_timestamp", datetime.now())
        
        db.commit()
        db.refresh(carrier)
        logger.info(f"✅ Carrier interests updated for DOT number: {dot_number}")
    except Exception as e:
        logger.error(f"❌ Error updating carrier interests for DOT {dot_number}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    return carrier