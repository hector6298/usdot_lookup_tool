import logging
from io import BytesIO
from openpyxl import Workbook
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session
from app.database import get_db
from app.crud.crm_object_sync_status import get_crm_sync_data
from app.crud.carrier_data import get_carrier_data_by_dot
from app.crud.ocr_results import get_ocr_results
from app.routes.auth import verify_login, verify_login_json_response
from app.models.ocr_results import OCRResultResponse
from app.models.carrier_data import CarrierData
from app.models.crm_object_sync_status import CarrierWithCRMSyncStatusResponse

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Set up a module-level logger
logger = logging.getLogger(__name__)

@router.get("/data/fetch/carriers",
            response_model=list[CarrierWithCRMSyncStatusResponse],
            dependencies=[Depends(verify_login_json_response)])
async def fetch_carriers(request: Request,
                    offset: int = 0,
                    limit: int = 10,
                    crm_sync_status: str = None,
                    usdot_filter: str = None,
                    db: Session = Depends(get_db)):

    """Return carrier results as JSON for the dashboard."""

    user_id = request.session['userinfo']['sub']
    org_id = (request.session['userinfo']['org_id']
                if 'org_id' in request.session['userinfo'] else user_id)
    
    logger.info("🔍 Fetching carrier data...")
    carriers = get_crm_sync_data(db, 
                                org_id=org_id,
                                offset=offset,
                                crm_sync_status=crm_sync_status,
                                usdot_filter=usdot_filter,
                                limit=limit)
    
    results = [
        CarrierWithCRMSyncStatusResponse(
            usdot=carrier.usdot,
            legal_name=carrier.carrier_data.legal_name,
            phone=carrier.carrier_data.phone,
            mailing_address=carrier.carrier_data.mailing_address,
            created_at=carrier.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            updated_at=carrier.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
            # Add sync status information
            crm_sync_status=carrier.crm_sync_status,
            crm_object_id=carrier.crm_object_id,
            crm_synched_at=carrier.crm_synched_at.strftime("%Y-%m-%d %H:%M:%S") if carrier.crm_synched_at else None,
            crm_platform=carrier.crm_platform,
        )
        for carrier in carriers
    ]

    logger.info(f"🔍 Carrier data fetched successfully: {results}")
    return results

@router.get("/data/fetch/carriers/{dot_number}",
            response_model=CarrierData,
            dependencies=[Depends(verify_login)])
def fetch_carrier(request: Request, 
                dot_number: str, 
                db: Session = Depends(get_db)):
    """Fetch and display carrier details based on DOT number."""
    logger.info(f"🔍 Fetching carrier details for DOT number: {dot_number}")
    carrier = get_carrier_data_by_dot(db, dot_number)

    # If no carrier data is found, return a message
    if not carrier:
        logger.warning(f"⚠ No carrier found for DOT number: {dot_number}")
        # return empty json
        return JSONResponse(status_code=404,
                            content={"status": "error", 
                                    "message": f"No carrier found for DOT number: {dot_number}"})
    
    # Render the template with carrier data
    logger.info(f"✅ Carrier found (USDOT {carrier.usdot}): {carrier.legal_name}")
    logger.info(f"Carrier details: {carrier}")

    return carrier

@router.get("/data/fetch/lookup_history",
            response_model=list[OCRResultResponse],
            dependencies=[Depends(verify_login_json_response)])
async def fetch_lookup_history(request: Request, 
                    offset: int = 0,
                    limit: int = 10,
                    valid_dot_only: bool = False,
                    db: Session = Depends(get_db)):

    """Return carrier results as JSON for the dashboard."""
    user_id = request.session['userinfo']['sub']
    org_id = (request.session['userinfo']['org_id']
                if 'org_id' in request.session['userinfo'] else user_id)

    logger.info("🔍 Fetching lookup history data...")
    results = get_ocr_results(db, 
                            org_id=org_id,
                            offset=offset,
                            limit=limit,
                            valid_dot_only=valid_dot_only)
    
    results = [
        OCRResultResponse(dot_reading=result.dot_reading,
                          timestamp=result.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                          filename=result.filename,
                          lookup_success_flag=result.lookup_success_flag,
                          user_id=result.app_user.user_email,
                          org_id=result.app_org.org_name)
        for result in results
    ]
    logger.info(f"🔍 Lookup history data fetched successfully: {results}")    
    return results


@router.get("/data/export/carriers", dependencies=[Depends(verify_login)])
async def export_carriers(request: Request, db: Session = Depends(get_db)):
    """Export carrier data to an Excel file."""

    user_id = request.session['userinfo']['sub']
    org_id = (request.session['userinfo']['org_id']
                if 'org_id' in request.session['userinfo'] else user_id)
    logger.info(f"🔍 Fetching carrier data for org ID: {org_id} to export (Excel).")

    results = get_crm_sync_data(db, org_id=org_id)

    wb = Workbook()
    ws = wb.active
    ws.title = "Carriers"

    # Write header
    ws.append([
        "DOT Number", "Legal Name", "Phone Number", "Mailing Address", "Created At",
        "CRM Sync Status", "CRM Object ID", "CRM Synced At", "CRM Platform"
    ])

    # Write data rows
    for result in results:
        ws.append([
            result.usdot,
            result.carrier_data.legal_name,
            result.carrier_data.phone,
            result.carrier_data.mailing_address,
            result.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            result.crm_sync_status,
            result.crm_object_id,
            result.crm_synched_at.strftime("%Y-%m-%d %H:%M:%S"),
            result.crm_platform
        ])

    # Save to in-memory bytes buffer
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    response = StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response.headers["Content-Disposition"] = "attachment; filename=carrier_data.xlsx"
    return response


@router.get("/data/export/lookup_history", dependencies=[Depends(verify_login)])
async def export_lookup_history(request: Request, db: Session = Depends(get_db)):
    """Export lookup history to an Excel file."""

    user_id = request.session['userinfo']['sub']
    org_id = (request.session['userinfo']['org_id']
                if 'org_id' in request.session['userinfo'] else user_id)
    logger.info(f"🔍 Fetching lookup history for org ID: {org_id} to export (Excel).")

    results = get_ocr_results(db, org_id=org_id, valid_dot_only=False, eager_relations=True)

    wb = Workbook()
    ws = wb.active
    ws.title = "Lookup History"

    # Write header
    ws.append([
        "DOT Number", "Legal Name", "Phone Number", "Created At", "Filename", "Created By", "Organization"
    ])

    # Write data rows
    for result in results:
        ws.append([
            result.dot_reading,

            result.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            result.filename,
            result.app_user.user_email if hasattr(result.app_user, "user_email") else "",
            result.app_org.org_name if hasattr(result.app_org, "org_name") else ""
        ])

    # Save to in-memory bytes buffer
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    response = StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response.headers["Content-Disposition"] = "attachment; filename=lookup_history.xlsx"
    return response