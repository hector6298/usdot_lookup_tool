import logging
import csv
from io import StringIO, BytesIO
from openpyxl import Workbook
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session
from app.database import get_db
from app.crud.engagement import get_engagement_data, update_carrier_engagement
from app.crud.carrier_data import get_carrier_data_by_dot
from app.crud.ocr_results import get_ocr_results
from app.crud.sobject_sync_status import get_sync_status_for_usdots
from app.routes.auth import verify_login, verify_login_json_response
from app.models.ocr_results import OCRResultResponse
from app.models.carrier_data import CarrierData
from app.models.engagement import CarrierWithEngagementResponse

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Set up a module-level logger
logger = logging.getLogger(__name__)

@router.get("/data/fetch/carriers",
            response_model=list[CarrierWithEngagementResponse],
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
    carriers = get_engagement_data(db, 
                                       org_id=org_id,
                                       offset=offset,
                                       carrier_contacted=client_contacted,
                                       carrier_interested=carrier_interested,
                                       limit=limit)
    
    # Get sync status for all carriers in batch
    usdots = [carrier.usdot for carrier in carriers]
    sync_status_dict = get_sync_status_for_usdots(db, usdots, org_id) if usdots else {}
    
    results = [
        CarrierWithEngagementResponse(
            usdot=carrier.usdot,
            legal_name=carrier.carrier_data.legal_name,
            phone=carrier.carrier_data.phone,
            mailing_address=carrier.carrier_data.mailing_address,
            created_at=carrier.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            carrier_interested=carrier.carrier_interested,
            carrier_contacted=carrier.carrier_contacted,
            carrier_followed_up=carrier.carrier_followed_up,
            carrier_follow_up_by_date=carrier.carrier_follow_up_by_date.strftime("%Y-%m-%d") 
                if carrier.carrier_follow_up_by_date else None,
            # Add sync status information
            sf_sync_status=sync_status_dict[carrier.usdot].sobject_sync_status if carrier.usdot in sync_status_dict else None,
            sf_sobject_id=sync_status_dict[carrier.usdot].sobject_id if carrier.usdot in sync_status_dict else None,
            sf_sync_timestamp=sync_status_dict[carrier.usdot].updated_at.strftime("%Y-%m-%d %H:%M:%S") 
                if carrier.usdot in sync_status_dict and sync_status_dict[carrier.usdot].updated_at else None
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

@router.post("/data/update/carrier_interests",
             dependencies=[Depends(verify_login_json_response)])
async def update_carrier_interests(request: Request,
                                    db: Session = Depends(get_db)):
    """Update carrier interests based on user input."""

    form_data = await request.json()
    logger.info("🔄 Updating carrier interests..."
                f"Changes received: {form_data}")
    
    try:
        for change_item in form_data.get("changes"):
            dot_number = change_item.get("usdot")
            field = change_item.get("field")
            value = change_item.get("value")

            if not dot_number or not field or value is None:
                raise HTTPException(status_code=400, detail="Invalid input data")

            update_carrier_engagement(db, change_item)
            
        return JSONResponse(status_code=200, 
                            content={"status": "ok", "message": "Changes updated successfully"})
    except Exception as e:
        logger.error(f"Error updating carrier interests: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    

@router.get("/data/export/carriers", dependencies=[Depends(verify_login)])
async def export_carriers(request: Request, db: Session = Depends(get_db)):
    """Export carrier data to an Excel file."""

    user_id = request.session['userinfo']['sub']
    org_id = (request.session['userinfo']['org_id']
                if 'org_id' in request.session['userinfo'] else user_id)
    logger.info(f"🔍 Fetching carrier data for org ID: {org_id} to export (Excel).")

    results = get_engagement_data(db, org_id=org_id)

    wb = Workbook()
    ws = wb.active
    ws.title = "Carriers"

    # Write header
    ws.append([
        "DOT Number", "Legal Name", "Phone Number", "Mailing Address", "Created At",
        "Client Contacted?", "Carrier Followed Up?", "Carrier Follow Up by Date", "Carrier Interested"
    ])

    # Write data rows
    for result in results:
        ws.append([
            result.usdot,
            result.carrier_data.legal_name,
            result.carrier_data.phone,
            result.carrier_data.mailing_address,
            result.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            result.carrier_contacted,
            result.carrier_followed_up,
            result.carrier_follow_up_by_date.strftime("%Y-%m-%d") if result.carrier_follow_up_by_date else None,
            result.carrier_interested,
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