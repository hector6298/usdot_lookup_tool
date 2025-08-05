import logging
from sqlmodel import Session
from app.models.ocr_results import OCRResult, OCRResultCreate
from fastapi import HTTPException
from sqlalchemy.orm import joinedload

# Set up a module-level logger
logger = logging.getLogger(__name__)


def save_ocr_results_bulk(db: Session, ocr_results: list[OCRResult]) -> list[OCRResult]:
    """Saves multiple OCR results to the database."""
    logger.info("🔍 Saving multiple OCR results to the database.")

    if ocr_results:
        try:
            logger.info(f"🔍 Saving {len(ocr_results)} OCR results to the database in bulk.")
            db.add_all(ocr_results)
            db.commit()

            # Refresh all records to get the latest state
            for record in ocr_results:
                db.refresh(record)

            logger.info("✅ All OCR results saved successfully.")
            return ocr_results
        except Exception as e:
            logger.error(f"❌ Error saving OCR results in bulk: {e}")
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))
    else:
        logger.warning("⚠ No valid OCR results to save.")
    return []

# OCR CRUD operations
def save_single_ocr_result(db: Session, ocr_result: OCRResult) -> OCRResult:
    """Saves OCR result to the database."""
    try:
        logger.info("🔍 Performing OCRResult data validation.")
        # Validate and update the OCR result

        logger.info("🔍 Saving OCR result to the database.")
        db.add(ocr_result)
        db.commit()
        db.refresh(ocr_result)

        logger.info(f"✅ OCR result saved with ID: {ocr_result.id}")
        return ocr_result

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
                    valid_dot_only: bool = True) -> dict:
    """Retrieves OCR results with a valid DOT number."""

    query = db.query(OCRResult)

    if org_id:
        logger.info(f"🔍 Filtering OCR results by org ID: {org_id}")
        query = query.filter(OCRResult.org_id == org_id)

    if valid_dot_only:
        logger.info("🔍 Filtering OCR results with a valid DOT number.")
        query = query.filter(OCRResult.dot_reading != None)

    # Order by timestamp descending (newest first)
    query = query.order_by(OCRResult.timestamp.desc())
    
    if offset is not None and limit is not None:
        logger.info(f"🔍 Applying range to OCR results: offset={offset}, limit={limit}")
        query = query.offset(offset).limit(limit)
    else:
        logger.info("🔍 Returning all OCR results")
    
    results = query.all()
        
    logger.info(f"✅ Found {len(results)} OCR results.")
    return results
