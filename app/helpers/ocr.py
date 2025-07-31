import logging
import re
from google.cloud import vision
from google.cloud.vision import ImageAnnotatorClient
from fastapi import UploadFile, File
from app.models.ocr_results import OCRResult, OCRResultCreate
from datetime import datetime
# Set up a module-level logger
logger = logging.getLogger(__name__)

async def cloud_ocr_from_image_file(vision_client: ImageAnnotatorClient, 
                                    file: UploadFile = File(...)):
    """Perform OCR on an image file using Google Cloud Vision API."""
    # Read the image file
    contents = await file.read()
    image = vision.Image(content=contents)

    # Perform OCR
    logger.info("🔍 Performing OCR on the uploaded image.")
    response = vision_client.text_detection(image=image)

    # Check for errors
    if response.error.message:
        raise Exception(f"Google Vision API Error: {response.error.message}")

    if not response.text_annotations:
        logger.warning("⚠ No text detected in the image.")
    else:
        logger.info(f"✅ Text detected: {response.text_annotations[0].description}")
    # Extract text from response
    ocr_text = response.text_annotations[0].description if response.text_annotations else ""
    
    return ocr_text


def generate_dot_record(ocr_result: OCRResultCreate, from_text_input=False) -> OCRResult:
    """Extract DOT number from OCR text."""
    try:
        # Extract the 10-digit number following "DOT"
        if from_text_input:
            logger.info("🔍 Extracting DOT number from manual text input.")
            regex_pattern = r'^(\d{5,8})$'
        else:
            logger.info("🔍 Extracting DOT number from OCR result.")
            regex_pattern = r'\b(?:US\s*DOT|USDOT|DOT)[\s#-]*?(\d{5,8})\b'
        
        match = re.search(regex_pattern, ocr_result.extracted_text, re.IGNORECASE)
        dot_reading = match.group(1) if match else "00000000" # 00000000 is the orphan record so the foreign key is maintained

        if not dot_reading:
            logger.warning("❌ No DOT number found in OCR result.")
        else:
            logger.info(f"✅ DOT number extracted: {dot_reading}")

        # Validate and update the OCR result
        return OCRResult.model_validate(
            ocr_result, 
            update={
                "timestamp": datetime.now(),
                "dot_reading": dot_reading
            }
        )
    except Exception as e:
        logger.error(f"❌ Error processing OCR result: {e}")