import logging
from flatten_dict import flatten
from google.cloud.vision_v1 import types
from google.cloud import vision
from google.cloud.vision import ImageAnnotatorClient
from fastapi import UploadFile, File
from safer import CompanySnapshot

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


def safer_web_lookup_from_dot(safer_client: CompanySnapshot,
                              dot_number: int):
    """Perform a safer web lookup using the dot reading."""
    try:
        logger.info(f"🔍 Performing SAFER web lookup for DOT number: {dot_number}")
        results = safer_client.get_by_usdot_number(dot_number)
        if results:
            logger.info(f"✅ SAFER web lookup results found: {results}")
        return results.to_dict()
    except Exception as e:
        logger.error(f"❌ SAFER web lookup failed: {e}")
        logger.warning("⚠ No data found for the provided DOT number.")
        return {'usdot': dot_number, 'value': 'Unknown'}
