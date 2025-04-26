import os
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import RedirectResponse
from sqlmodel import Session
from PIL import Image
from app.database import get_db
from app.models import OCRResultCreate, CarrierData
from app.crud import save_ocr_results_bulk, save_carrier_data_bulk
from app.info_extraction import cloud_ocr_from_image_file, safer_web_lookup_from_dot
from app.config import config
from app.routes.verify_login import verify_login
from google.cloud import vision
from safer import CompanySnapshot

# Set up a module-level logger
logger = logging.getLogger(__name__)

# Initialize Google Cloud Vision client
vision_client = vision.ImageAnnotatorClient(
    client_options={"api_key": config["GCP"]["OCR_API_KEY"]}
)

# Initialize SAFER web crawler
safer_client = CompanySnapshot()

# Initialize APIRouter
router = APIRouter()


@router.post("/upload",
             dependencies=[Depends(verify_login)])
async def upload_file(files: list[UploadFile] = File(...), db: Session = Depends(get_db)):
    ocr_records = []  # Store OCR results before batch insert
    valid_files = []
    invalid_files = []

    for file in files:
        try:
            # Validate file type
            if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                logger.error("❌ Invalid file type. Only image files ('.png', '.jpg', '.jpeg', '.bmp') are allowed.")
                invalid_files.append(file.filename)
                continue            
            # perform OCR on image
            
            ocr_text = await cloud_ocr_from_image_file(vision_client, file)
            ocr_record = OCRResultCreate(extracted_text=ocr_text, filename=file.filename)
            ocr_records.append(ocr_record)
            valid_files.append(file.filename)
        except Exception as e:
            logger.exception(f"❌ Error processing file: {e}")

    if not ocr_records:
        raise HTTPException(status_code=400, detail="No valid files were processed.")
    
    # Save to database using schema
    ocr_results = save_ocr_results_bulk(db, ocr_records)

    if ocr_results:
        logger.info("✅ All OCR results saved successfully.")
        safer_lookups = []
        for result in ocr_results:
            
            # Perform SAFER web lookup
            safer_data = safer_web_lookup_from_dot(safer_client, int(result.dot_reading))
            if safer_data:
                safer_lookups.append(safer_data)
           
        # Save carrier data to database
        if safer_lookups:
            _ = save_carrier_data_bulk(db, safer_lookups)
            logger.info(f"✅ Processed {len(ocr_results)} OCR results, {safer_lookups} carrier records saved.")


    # Collect all OCR result IDs
    ocr_result_ids = [result.id for result in ocr_results]

    # Redirect to home with all OCR result IDs
    return RedirectResponse(url=f"dashboard/?result_ids={','.join(map(str, ocr_result_ids))}", status_code=303)