import os
import logging
import re
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request, Form
from sqlmodel import Session
from app.database import get_db
from app.models.ocr_results import OCRResultCreate, OCRResult
from app.crud.ocr_results import save_ocr_results_bulk
from app.crud.carrier_data import save_carrier_data_bulk
from app.helpers.ocr import cloud_ocr_from_image_file, generate_dot_record
from app.helpers.safer_web import safer_web_lookup_from_dot
from app.routes.auth import verify_login
from google.cloud import vision
from safer import CompanySnapshot
from fastapi.responses import JSONResponse

# Set up a module-level logger
logger = logging.getLogger(__name__)

# Initialize Google Cloud Vision client
vision_client = vision.ImageAnnotatorClient(
    client_options={"api_key": os.environ.get("GCP_OCR_API_KEY")}
)

# Initialize SAFER web crawler
safer_client = CompanySnapshot()

# Initialize APIRouter
router = APIRouter()


@router.post("/upload",
             dependencies=[Depends(verify_login)])
async def upload_file(files: list[UploadFile] = File(...), 
                      request: Request = None,
                      db: Session = Depends(get_db)):
    ocr_records = []  # Store OCR results before batch insert
    valid_files = []
    invalid_files = []
    user_id = request.session['userinfo']['sub']
    org_id = (request.session['userinfo']['org_id'] 
                if 'org_id' in request.session['userinfo'] else user_id)
    
    for file in files:
        try:
            # Validate file type
            supported_types = ('.png', '.jpg', '.jpeg', '.bmp', '.heic', '.heif')
            if not file.filename.lower().endswith(supported_types):
                logger.error(f"❌ Invalid file type. Only image files {supported_types} are allowed.")
                invalid_files.append(file.filename)
                continue         
               
            # perform OCR on image
            ocr_text = await cloud_ocr_from_image_file(vision_client, file)
            ocr_record = OCRResultCreate(extracted_text=ocr_text, 
                                         filename=file.filename,
                                         user_id=user_id,
                                         org_id=org_id)
            ocr_record = generate_dot_record(ocr_record)
            ocr_records.append(ocr_record)
            valid_files.append(file.filename)
        except Exception as e:
            logger.exception(f"❌ Error processing file: {e}")
    
    if not ocr_records:
        raise HTTPException(status_code=400, detail="No valid files were processed.")
    

    if ocr_records:
        logger.info("✅ All OCR results saved successfully.")
        safer_lookups = []
        for result in ocr_records:
            
            # Perform SAFER web lookup for valid DOT readings (00000000 is the orphan record)
            if result.dot_reading and result.dot_reading != "0000000":
                safer_data = safer_web_lookup_from_dot(safer_client, result.dot_reading)
                if safer_data.lookup_success_flag:
                    safer_lookups.append(safer_data)

        # Save carrier data to database
        if safer_lookups:
            _ = save_carrier_data_bulk(db, safer_lookups, 
                                       user_id=user_id,
                                       org_id=org_id)
                                       
        # Save to database using schema
        ocr_results = save_ocr_results_bulk(db, ocr_records)       

        logger.info(f"✅ Processed {len(ocr_results)} OCR results, {safer_lookups} carrier records saved.")

    # Collect all OCR result IDs
    ocr_result_ids = [
        {"id": result.id, "dot_reading": result.dot_reading}
        for result in ocr_results
    ]
    
    # Redirect to home with all OCR result IDs
    return JSONResponse(
        content={
            "message": "Processing complete",
            "result_ids": ocr_result_ids,
            "valid_files": valid_files,
            "invalid_files": invalid_files
        },
        status_code=200
    )


@router.post("/upload/manual",
             dependencies=[Depends(verify_login)])
async def upload_manual_usdots(usdot_numbers: str = Form(...),
                              request: Request = None,
                              db: Session = Depends(get_db)):
    """Process manually entered USDOT numbers."""
    
    user_id = request.session['userinfo']['sub']
    org_id = (request.session['userinfo']['org_id'] 
                if 'org_id' in request.session['userinfo'] else user_id)
    
    # Parse and validate USDOT numbers
    if not usdot_numbers or not usdot_numbers.strip():
        raise HTTPException(status_code=400, detail="No USDOT numbers provided.")
    
    # Split by commas and clean up
    raw_usdots = [usdot.strip() for usdot in usdot_numbers.split(',')]
    valid_usdots = []
    invalid_usdots = []
    
    # Validate each USDOT number (should be numeric, typically 6-8 digits)
    usdot_pattern = re.compile(r'^\d{6,8}$')
    
    for usdot in raw_usdots:
        if usdot and usdot_pattern.match(usdot):
            valid_usdots.append(usdot)
        elif usdot:  # Not empty but invalid format
            invalid_usdots.append(usdot)
    
    if not valid_usdots:
        raise HTTPException(status_code=400, detail="No valid USDOT numbers found.")
    
    # Create OCR records for manual input (similar to image processing but with manual source)
    ocr_create_records = []
    for usdot in valid_usdots:
        ocr_record = OCRResultCreate(
            extracted_text=f"Manual input: {usdot}",
            filename=f"manual_input_{usdot}",
            user_id=user_id,
            org_id=org_id
        )
        ocr_create_records.append(ocr_record)
    
    # Convert to OCRResult objects with dot_reading (similar to image processing pipeline)
    ocr_records = []
    for ocr_create in ocr_create_records:
        # For manual input, we already know the DOT number, so we set it directly
        ocr_result = OCRResult.model_validate(
            ocr_create,
            update={
                "timestamp": datetime.now(),
                "dot_reading": ocr_create.extracted_text.split(": ")[1]  # Extract USDOT from "Manual input: 123456"
            }
        )
        ocr_records.append(ocr_result)
    
    logger.info(f"📝 Processing {len(valid_usdots)} manually entered USDOT numbers")
    
    # Perform SAFER web lookup for each valid USDOT
    safer_lookups = []
    for result in ocr_records:
        if result.dot_reading and result.dot_reading != "0000000":
            safer_data = safer_web_lookup_from_dot(safer_client, result.dot_reading)
            if safer_data.lookup_success_flag:
                safer_lookups.append(safer_data)
    
    # Save carrier data to database
    if safer_lookups:
        _ = save_carrier_data_bulk(db, safer_lookups, 
                                   user_id=user_id,
                                   org_id=org_id)
    
    # Save OCR results to database
    ocr_results_saved = save_ocr_results_bulk(db, ocr_records)
    
    logger.info(f"✅ Processed {len(ocr_results_saved)} manual USDOT entries, {len(safer_lookups)} carrier records saved.")
    
    # Collect all OCR result IDs
    ocr_result_ids = [
        {"id": result.id, "dot_reading": result.dot_reading}
        for result in ocr_results_saved
    ]
    
    return JSONResponse(
        content={
            "message": "Manual USDOT processing complete",
            "result_ids": ocr_result_ids,
            "valid_usdots": valid_usdots,
            "invalid_usdots": invalid_usdots,
            "successful_lookups": len(safer_lookups)
        },
        status_code=200
    )