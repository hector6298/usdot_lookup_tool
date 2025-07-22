import logging
import csv
from io import StringIO, BytesIO
from openpyxl import Workbook
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session
from app.database import get_db
from app.crud.crm_sync_status import get_crm_sync_data
from app.crud.carrier_data import get_carrier_data_by_dot
from app.crud.ocr_results import get_ocr_results
from app.crud.sobject_sync_status import get_crm_sync_status_for_usdots
from app.routes.auth import verify_login, verify_login_json_response
from app.models.ocr_results import OCRResultResponse
from app.models.carrier_data import CarrierData
from app.models.engagement import CarrierWithSyncStatusResponse

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Set up a module-level logger
logger = logging.getLogger(__name__)

@router.get("/data/fetch/carriers",
            response_model=list[CarrierWithSyncStatusResponse],
            dependencies=[Depends(verify_login_json_response)])
async def fetch_carriers(request: Request,
                    offset: int = 0,
                    limit: int = 10,
                    carrier_interested: bool = None,
                    client_contacted: bool = None,
                    db: Session = Depends(get_db)):

    """Return carrier results as JSON for the dashboard."""

    user_id = request.session['userinfo']['sub']
    org_id = (request.session['userinfo']['org_id']
                if 'org_id' in request.session['userinfo'] else user_id)
    
    logger.info("🔍 Fetching carrier data...")
    sync_records = get_crm_sync_data(db, 
                                     org_id=org_id,
                                     offset=offset,
                                     carrier_contacted=client_contacted,
                                     carrier_interested=carrier_interested,
                                     limit=limit)
    
    # Get sync status for all carriers in batch
    usdots = [sync_record.usdot for sync_record in sync_records]
    sync_status_dict = get_crm_sync_status_for_usdots(db, usdots, org_id) if usdots else {}
    
    results = [
        CarrierWithSyncStatusResponse(
            usdot=sync_record.usdot,
            legal_name=sync_record.carrier_data.legal_name if sync_record.carrier_data else "",
            phone=sync_record.carrier_data.phone if sync_record.carrier_data else "",
            mailing_address=sync_record.carrier_data.mailing_address if sync_record.carrier_data else "",
            created_at=sync_record.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            carrier_interested=False,  # Keep for backward compatibility
            # CRM sync status information
            sobject_sync_status=sync_record.sobject_sync_status,
            sobject_id=sync_record.sobject_id,
            subject_synched_at=sync_record.subject_synched_at.strftime("%Y-%m-%d %H:%M:%S") if sync_record.subject_synched_at else None
        )
        for sync_record in sync_records
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
                                    valid_dot_only=valid_dot_only,
                                    eager_relations=True)
    
    results = [
        OCRResultResponse(dot_reading=result.dot_reading,
                          legal_name=result.carrier_data.legal_name if result.carrier_data else "",
                          phone=result.carrier_data.phone if result.carrier_data else "",
                          mailing_address=result.carrier_data.mailing_address if result.carrier_data else "",
                          timestamp=result.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                          filename=result.filename,
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
        "CRM Sync Status", "CRM Object ID", "Last Synced At"
    ])

    # Write data rows
    for result in results:
        ws.append([
            result.usdot,
            result.carrier_data.legal_name if result.carrier_data else "",
            result.carrier_data.phone if result.carrier_data else "",
            result.carrier_data.mailing_address if result.carrier_data else "",
            result.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            result.sobject_sync_status,
            result.sobject_id,
            result.subject_synched_at.strftime("%Y-%m-%d %H:%M:%S") if result.subject_synched_at else None,
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
        "DOT Number", "Legal Name", "Phone Number", "Mailing Address",
        "Created At", "Filename", "Created By"
    ])

    # Write data rows
    for result in results:
        ws.append([
            result.dot_reading,
            result.carrier_data.legal_name if result.carrier_data else "",
            result.carrier_data.phone if result.carrier_data else "",
            result.carrier_data.mailing_address if result.carrier_data else "",
            result.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            result.filename,
            result.app_user.user_email if hasattr(result.app_user, "user_email") else "",
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