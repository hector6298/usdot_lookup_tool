from fastapi import APIRouter, Request,HTTPException, Depends, Body
from sqlmodel import Session, select
from fastapi.responses import RedirectResponse, JSONResponse
from app.database import get_db
from app.crud.oauth import get_valid_salesforce_token, upsert_salesforce_token, delete_salesforce_token
from app.models.carrier_data import CarrierData
from datetime import datetime
import urllib.parse
import httpx
import logging
import os
import time

router = APIRouter()

# Set up a module-level logger
logger = logging.getLogger(__name__)

@router.get("/salesforce/connect")
async def connect_salesforce(request: Request):
    """Redirects the user to Salesforce OAuth authorization page."""
    if 'userinfo' not in request.session:
        logger.error("Cannot call SF authorization. User not authenticated.")
        return JSONResponse(status_code=401, content={"detail": "User not authenticated."})
    
    if os.environ.get('ENVIRONMENT') == 'dev' and os.environ.get('NGROK_TUNNEL_URL', None):
        redirect_uri = os.environ.get('NGROK_TUNNEL_URL') + '/salesforce/callback'
    else:
        redirect_uri = request.url_for("salesforce_callback")

    logger.info("Redirecting to Salesforce OAuth authorization page.")
    # Prepare the OAuth authorization URL
    params = {
        "response_type": "code",
        "client_id": os.environ.get('SF_CONSUMER_KEY'),
        "redirect_uri": redirect_uri
    }
    sf_auth_url = f"https://{os.environ.get('SF_DOMAIN')}/services/oauth2/authorize?{urllib.parse.urlencode(params)}"
    return RedirectResponse(sf_auth_url)


@router.get("/salesforce/callback")
async def salesforce_callback(request: Request, code: str = None, state: str = None,
                              db: Session = Depends(get_db)):
    if not code:
        logger.error("Missing code from Salesforce OAuth callback.")
        raise HTTPException(status_code=400, detail="Missing code from Salesforce.")

    if os.environ.get('ENVIRONMENT') == 'dev' and os.environ.get('NGROK_TUNNEL_URL', None):
        redirect_uri = os.environ.get('NGROK_TUNNEL_URL') + '/salesforce/callback'
        dashboard_uri = os.environ.get('NGROK_TUNNEL_URL') + '/dashboards/carriers'
    else:
        redirect_uri = request.url_for("salesforce_callback")
        dashboard_uri = request.url_for("dashboard", dashboard_type="carriers")

    logger.info(f"Received Salesforce OAuth code.")
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": os.environ.get('SF_CONSUMER_KEY'),
        "client_secret": os.environ.get('SF_CONSUMER_SECRET'),
        "redirect_uri": redirect_uri,
    }
    # Make a POST request to Salesforce token endpoint
    logger.info("Requesting Salesforce access token.")

    sf_token_url = f"https://{os.environ.get('SF_DOMAIN')}/services/oauth2/token"
    async with httpx.AsyncClient() as client:
        resp = await client.post(sf_token_url, data=data)
        resp.raise_for_status()
        tokens = resp.json()
        # Store tokens associated with the current user
    
    # --- Upsert the token in the database ---
    user_id = request.session["userinfo"]["sub"]
    org_id = request.session["userinfo"].get("org_id", "default")  # Adjust as needed
    upsert_salesforce_token(db, user_id, org_id, tokens)

    request.session["sf_connected"] = True
    #print sessions id
    logger.info(tokens)
    time.sleep(1)
    logger.info("Salesforce access token received and stored in session.")
    return RedirectResponse(dashboard_uri)


@router.post("/salesforce/disconnect")
async def disconnect_salesforce(request: Request,
                                db: Session = Depends(get_db)):
    # Remove token from DB
    user_id = request.session["userinfo"]["sub"]
    org_id = request.session["userinfo"].get("org_id", "default")  

    if delete_salesforce_token(db, user_id, org_id, 'salesforce'):
        logger.info(f"Salesforce token deleted for user {user_id} and org {org_id}.")
    else:
        logger.warning(f"No Salesforce token found for user {user_id} and org {org_id}.")
    
    request.session["sf_connected"] = False
    logger.info("Salesforce connection disconnected.")
    return {"detail": "Disconnected from Salesforce"}


@router.post("/salesforce/upload_carriers")
async def upload_carriers_to_salesforce(
    request: Request,
    carriers_usdot: list[str] = Body(..., embed=True),  # expects {"carrier_ids": [1,2,3]}
    db: Session = Depends(get_db)
):
    user_id = request.session["userinfo"]["sub"]
    org_id = request.session["userinfo"].get("org_id", "default")  # adjust as needed

    if request.session.get("sf_connected", False):
        # 1. Get a valid Salesforce access token (refresh if needed)
        token_obj = await get_valid_salesforce_token(db, user_id, org_id)
        
        if not token_obj:
            logger.error(f"No valid Salesforce token available for user {user_id} and org {org_id}.")
            request.session["sf_connected"] = False
            return JSONResponse(status_code=401, content={"detail": "No Salesforce token available. Please reconnect to Salesforce."})
        else:
            logger.info(f"Using Salesforce token for user {user_id} and org {org_id}.")

        # 2. Prepare Salesforce Account data for each carrier
        carriers = db.exec(select(CarrierData).where(CarrierData.usdot.in_(carriers_usdot))).all()
        if not carriers:
            logger.error(f"No carriers found for the provided USDOTs: {carriers_usdot}.")
            return JSONResponse(status_code=404, content={"detail": "No carriers found."})
        else:
            logger.info(f"Found {len(carriers)} carriers to upload to Salesforce.")

        # 3. Use Salesforce Composite API to insert accounts
        sf_instance_url = token_obj.token_data.get("instance_url")
        if not sf_instance_url:
            return JSONResponse(status_code=500, content={"detail": "Salesforce instance URL missing from token data."})

        url = f"{sf_instance_url}/services/data/v58.0/composite/tree/Account/"
        headers = {
            "Authorization": f"Bearer {token_obj.access_token}",
            "Content-Type": "application/json"
        }

        # Salesforce composite API for bulk insert
        records = []
        for carrier in carriers:
            records.append({
                "attributes": {"type": "Account", "referenceId": f"carrier_{carrier.usdot}"},
                "Name": carrier.legal_name or carrier.dba_name or "Unknown Carrier",
                "Phone": carrier.phone,
                "BillingStreet": carrier.physical_address,
                "ShippingStreet": carrier.mailing_address,
                "BillingCity": None,  # Add if you have city info
                "BillingState": None,  # Add if you have state info
                "BillingPostalCode": None,  # Add if you have zip info
                "AccountNumber": carrier.usdot,
                "Type": carrier.entity_type,
                "Description": carrier.usdot_status,
                # Custom fields (adjust names to match your Salesforce org)
                #"MC_MX_FF_Numbers__c": carrier.mc_mx_ff_numbers,
                #"State_Carrier_ID__c": carrier.state_carrier_id,
                #"Power_Units__c": carrier.power_units,
                #"Drivers__c": carrier.drivers,
                #"MCS_150_Form_Date__c": carrier.mcs_150_form_date,
                #"MCS_150_Mileage_Year_Mileage__c": carrier.mcs_150_mileage_year_mileage,
                #"MCS_150_Mileage_Year_Year__c": carrier.mcs_150_mileage_year_year,
                #"Out_Of_Service_Date__c": carrier.out_of_service_date,
                #"Operating_Authority_Status__c": carrier.operating_authority_status,
                #"Operation_Classification__c": carrier.operation_classification,
                #"Carrier_Operation__c": carrier.carrier_operation,
                #"HM_Shipper_Operation__c": carrier.hm_shipper_operation,
                #"Cargo_Carried__c": carrier.cargo_carried,
                # US Inspection/Crash fields
                #"USA_Vehicle_Inspections__c": carrier.usa_vehicle_inspections,
                #"USA_Vehicle_Out_Of_Service__c": carrier.usa_vehicle_out_of_service,
                #"USA_Vehicle_Out_Of_Service_Percent__c": carrier.usa_vehicle_out_of_service_percent,
                #"USA_Vehicle_National_Average__c": carrier.usa_vehicle_national_average,
                #"USA_Driver_Inspections__c": carrier.usa_driver_inspections,
                #"USA_Driver_Out_Of_Service__c": carrier.usa_driver_out_of_service,
                #"USA_Driver_Out_Of_Service_Percent__c": carrier.usa_driver_out_of_service_percent,
                #"USA_Driver_National_Average__c": carrier.usa_driver_national_average,
                #"USA_Hazmat_Inspections__c": carrier.usa_hazmat_inspections,
                #"USA_Hazmat_Out_Of_Service__c": carrier.usa_hazmat_out_of_service,
                #"USA_Hazmat_Out_Of_Service_Percent__c": carrier.usa_hazmat_out_of_service_percent,
                #"USA_Hazmat_National_Average__c": carrier.usa_hazmat_national_average,
                #"USA_IEP_Inspections__c": carrier.usa_iep_inspections,
                #"USA_IEP_Out_Of_Service__c": carrier.usa_iep_out_of_service,
                #"USA_IEP_Out_Of_Service_Percent__c": carrier.usa_iep_out_of_service_percent,
                #"USA_IEP_National_Average__c": carrier.usa_iep_national_average,
                #"USA_Crashes_Tow__c": carrier.usa_crashes_tow,
                #"USA_Crashes_Fatal__c": carrier.usa_crashes_fatal,
                #"USA_Crashes_Injury__c": carrier.usa_crashes_injury,
                #"USA_Crashes_Total__c": carrier.usa_crashes_total,
                # Canada Inspection/Crash fields
                #"Canada_Driver_Out_Of_Service__c": carrier.canada_driver_out_of_service,
                #"Canada_Driver_Out_Of_Service_Percent__c": carrier.canada_driver_out_of_service_percent,
                #"Canada_Driver_Inspections__c": carrier.canada_driver_inspections,
                #"Canada_Vehicle_Out_Of_Service__c": carrier.canada_vehicle_out_of_service,
                #"Canada_Vehicle_Out_Of_Service_Percent__c": carrier.canada_vehicle_out_of_service_percent,
                #"Canada_Vehicle_Inspections__c": carrier.canada_vehicle_inspections,
                #"Canada_Crashes_Tow__c": carrier.canada_crashes_tow,
                #"Canada_Crashes_Fatal__c": carrier.canada_crashes_fatal,
                #"Canada_Crashes_Injury__c": carrier.canada_crashes_injury,
                #"Canada_Crashes_Total__c": carrier.canada_crashes_total,
                # Safety fields
                #"Safety_Rating_Date__c": carrier.safety_rating_date,
                #"Safety_Review_Date__c": carrier.safety_review_date,
                #"Safety_Rating__c": carrier.safety_rating,
                #"Safety_Type__c": carrier.safety_type,
                #"Latest_Update__c": carrier.latest_update,
                "URL__c": carrier.url,
            })

        payload = {
            "records": records
        }

        async with httpx.AsyncClient() as client:
            logger.info(f"Sending {len(records)} carrier records to Salesforce for upload.")
            resp = await client.post(url, json=payload, headers=headers)

            if resp.status_code not in (200, 201):
                logger.error(f"Salesforce upload failed with status {resp.status_code}: {resp.text}")
                request.session["sf_connected"] = False
                return JSONResponse(status_code=resp.status_code, content={"detail": f"Salesforce error: {resp.text}"})
        
        logger.info(f"Successfully uploaded {len(records)} carriers to Salesforce.")
        return JSONResponse(content=resp.json())
    else:
        logger.error("Salesforce connection not established.")
        return JSONResponse(status_code=401, content={"detail": "Salesforce connection not established. Please connect first."})
