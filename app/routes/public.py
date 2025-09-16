from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
import os

router = APIRouter()

@router.get("/public/logo.png")
async def get_logo_png():
    """
    Serve the logo image as PNG publicly (no auth required)
    for use in Auth0 login screens
    """
    # Check if we already have a PNG version of the logo
    png_logo_path = Path("app/static/logo/app_logo2.png")
    jpg_logo_path = Path("app/static/logo/app_logo2.jpg")
    
    # Use the PNG if it exists, otherwise fall back to JPG
    if png_logo_path.exists():
        logo_path = png_logo_path
        media_type = "image/png"
    elif jpg_logo_path.exists():
        logo_path = jpg_logo_path
        media_type = "image/jpeg"
    else:
        raise HTTPException(status_code=404, detail="Logo not found")
        
    return FileResponse(
        logo_path,
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=604800"}
    )

# Keep original JPG endpoint for backward compatibility
@router.get("/public/logo")
async def get_logo():
    """
    Serve the logo image publicly (no auth required)
    for use in Auth0 login screens
    """
    return await get_logo_png()
