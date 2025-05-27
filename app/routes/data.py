import logging
import csv
from enum import Enum
from io import StringIO
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session
from app.database import get_db
from app import crud
from app.routes.verify_login import verify_login, verify_login_json_response
from app.models import OCRResultResponse, CarrierData, CarrierWithEngagementResponse

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
    carriers = crud.get_engagement_data(db, 
                                       org_id=org_id,
                                       offset=offset,
                                       carrier_contacted=client_contacted,
                                       carrier_interested=carrier_interested,
                                       limit=limit)
    
    results = [
        CarrierWithEngagementResponse(usdot=carrier.usdot,
                                      legal_name=carrier.carrier_data.legal_name,
                                      phone=carrier.carrier_data.phone,
                                      mailing_address=carrier.carrier_data.mailing_address,
                                      created_at=carrier.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                                      carrier_interested=carrier.carrier_interested,
                                      carrier_contacted=carrier.carrier_contacted,
                                      carrier_followed_up=carrier.carrier_followed_up,
                                      carrier_follow_up_by_date=carrier.carrier_follow_up_by_date.strftime("%Y-%m-%d") 
                                        if carrier.carrier_follow_up_by_date else None)
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
    carrier = crud.get_carrier_data_by_dot(db, dot_number)

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
    results = crud.get_ocr_results(db, 
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
                          user_id=result.user_id,
                          org_id=result.org_id)
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

            crud.update_carrier_engagement(db, change_item)
            
        return JSONResponse(status_code=200, 
                            content={"status": "ok", "message": "Changes updated successfully"})
    except Exception as e:
        logger.error(f"Error updating carrier interests: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    

@router.get("/data/export/carriers",
            dependencies=[Depends(verify_login)])
async def export_csv(request: Request,
                     db: Session = Depends(get_db)):
    """Export carrier data to a CSV file."""

    user_id = request.session['userinfo']['sub']
    org_id = (request.session['userinfo']['org_id']
                if 'org_id' in request.session['userinfo'] else user_id)
    logger.info(f"🔍 Fetching carrier data for org ID: {org_id} to export.")

    # Create a CSV in memory
    output = StringIO()
    writer = csv.writer(output)

    logger.info("🔍 Fetching carrier data...")
    results = crud.get_engagement_data(db, 
                                       org_id=org_id)
    
    writer.writerow(["DOT Number", "Legal Name", "Phone Number", 
                     "Mailing Address", "Created At", 
                     "Client Contacted?", "Carrier Followed Up?",
                     "Carrier Follow Up by Date", "Carrier Interested"])
    for result in results:

        writer.writerow([
            result.usdot,
            result.carrier_data.legal_name,
            result.carrier_data.phone,
            result.carrier_data.mailing_address,
            result.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            result.carrier_contacted,
            result.carrier_followed_up,
            result.carrier_follow_up_by_date.strftime("%Y-%m-%d") 
                if result.carrier_follow_up_by_date else None,
            result.carrier_interested,
        ])

    logger.info(f"📥 Exporting {len(results)} carriers to CSV...")
    output.seek(0)
    logger.info("📥 CSV export completed successfully.")
    
    # Return the CSV as a streaming response
    response = StreamingResponse(output, media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=carrier_data.csv"
    return response

@router.get("/data/export/lookup_history",
            dependencies=[Depends(verify_login)])
async def export_csv(request: Request, 
                     db: Session = Depends(get_db)):
    """Export carrier data to a CSV file."""

    user_id = request.session['userinfo']['sub']
    org_id = (request.session['userinfo']['org_id']
                if 'org_id' in request.session['userinfo'] else user_id)
    logger.info(f"🔍 Fetching lookup data for org ID: {org_id} to export.")

    # Create a CSV in memory
    output = StringIO()
    writer = csv.writer(output)

    logger.info("🔍 Fetching lookup history data...")
    results = crud.get_ocr_results(db, 
                                   org_id=org_id,
                                   valid_dot_only=False)
    
    writer.writerow(["DOT Number", "Legal Name", "Phone Number", "Mailing Address", "Created At", "Carrier Interested", "Client Contacted"])
    for result in results:

        writer.writerow([
            result.dot_reading,
            result.carrier_data.legal_name if result.carrier_data else "",
            result.carrier_data.phone if result.carrier_data else "",
            result.carrier_data.mailing_address if result.carrier_data else "",
            result.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            result.filename
        ])
    
    logger.info(f"📥 Exporting {len(results)} carriers to CSV...")
    output.seek(0)
    logger.info("📥 CSV export completed successfully.")
    
    # Return the CSV as a streaming response
    response = StreamingResponse(output, media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=carrier_data.csv"
    return response