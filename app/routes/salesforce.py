from fastapi import APIRouter, Request, HTTPException, Depends, Body, Query
from sqlmodel import Session, select
from fastapi.responses import RedirectResponse, JSONResponse
from app.database import get_db
from app.crud.oauth import get_valid_salesforce_token, upsert_salesforce_token, delete_salesforce_token
from app.crud.crm_object_sync_history import create_sync_history_record
from app.crud.crm_object_sync_status import update_crm_sync_status
from app.models.carrier_data import CarrierData
from datetime import datetime
import urllib.parse
import httpx
import requests
import logging
import os
import time

router = APIRouter()

SALESFORCE_METADATA_API_VERSION = "57.0"  # Use a recent version for Metadata API
# Utility to get all custom fields for an object
def get_salesforce_custom_fields(instance_url, access_token, object_name="Account"):
    url = f"{instance_url}/services/data/v{SALESFORCE_METADATA_API_VERSION}/sobjects/{object_name}/describe"
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    describe = resp.json()
    return {f['name'] for f in describe.get('fields', [])}

# Utility to create a custom field using the Metadata API
def create_salesforce_custom_field(instance_url, access_token, object_name, field_def):
    url = f"{instance_url}/services/data/v{SALESFORCE_METADATA_API_VERSION}/tooling/sobjects/CustomField"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    resp = requests.post(url, headers=headers, json=field_def)
    return resp

# Map your CarrierData columns to Salesforce field definitions
def get_field_definitions(columns=None):
    # Map: python_attr -> (label, type, length, ...)
    # Only a subset shown; expand as needed
    field_map = {
        "mc_mx_ff_numbers": {"label": "MC MX FF Numbers", "type": "Text", "length": 255},
        "state_carrier_id": {"label": "State Carrier ID", "type": "Text", "length": 255},
        "duns_number": {"label": "DUNS Number", "type": "Text", "length": 255},
        "power_units": {"label": "Power Units", "type": "Number", "precision": 18, "scale": 0},
        "drivers": {"label": "Drivers", "type": "Number", "precision": 18, "scale": 0},
        "mcs_150_form_date": {"label": "MCS-150 Form Date", "type": "Date"},
        "mcs_150_mileage_year_mileage": {"label": "MCS-150 Mileage Year Mileage", "type": "Number", "precision": 18, "scale": 0},
        "mcs_150_mileage_year_year": {"label": "MCS-150 Mileage Year Year", "type": "Number", "precision": 18, "scale": 0},
        "out_of_service_date": {"label": "Out Of Service Date", "type": "Date"},
        "operating_authority_status": {"label": "Operating Authority Status", "type": "Text", "length": 255},
        "operation_classification": {"label": "Operation Classification", "type": "Text", "length": 255},
        "carrier_operation": {"label": "Carrier Operation", "type": "Text", "length": 255},
        "hm_shipper_operation": {"label": "HM Shipper Operation", "type": "Text", "length": 255},
        "cargo_carried": {"label": "Cargo Carried", "type": "Text", "length": 255},
        # Add more mappings as needed
    }
    if columns is None:
        columns = list(field_map.keys())
    return {k: v for k, v in field_map.items() if k in columns}

@router.post("/salesforce/create_custom_fields")
async def create_salesforce_custom_fields(
    request: Request,
    columns: list[str] = Query(None, description="CarrierData columns to add as custom fields. None = all."),
    object_name: str = Query("Account", description="Salesforce object to add fields to."),
    db: Session = Depends(get_db)
):
    """Create Salesforce custom fields for selected CarrierData columns using the Metadata API."""
    user_id = request.session["userinfo"]["sub"]
    org_id = request.session["userinfo"].get("org_id", user_id)
    token_obj = await get_valid_salesforce_token(db, user_id, org_id)
    if not token_obj:
        raise HTTPException(status_code=401, detail="No Salesforce token available. Please reconnect to Salesforce.")
    access_token = token_obj.access_token
    instance_url = token_obj.token_data.get("instance_url")
    if not instance_url:
        raise HTTPException(status_code=500, detail="Salesforce instance URL missing from token data.")

    # Get existing custom fields
    try:
        existing_fields = get_salesforce_custom_fields(instance_url, access_token, object_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch Salesforce fields: {e}")

    # Get field definitions
    field_defs = get_field_definitions(columns)
    results = []
    for attr, field in field_defs.items():
        api_name = f"{attr}__c"
        if api_name in existing_fields:
            results.append({"field": api_name, "status": "already_exists"})
            continue
        field_payload = {
            "Metadata": {
                "fullName": f"{object_name}.{api_name}",
                "label": field["label"],
                "type": field["type"]
            },
            "TableEnumOrId": object_name,
        }
        # Add type-specific properties
        if field["type"] == "Text":
            field_payload["Metadata"]["length"] = field["length"]
        if field["type"] == "Number":
            field_payload["Metadata"]["precision"] = field["precision"]
            field_payload["Metadata"]["scale"] = field["scale"]
        if field["type"] == "Date":
            pass  # No extra properties
        resp = create_salesforce_custom_field(instance_url, access_token, object_name, field_payload)
        if resp.status_code in (200, 201):
            results.append({"field": api_name, "status": "created"})
        else:
            try:
                error_detail = resp.json()
            except Exception:
                error_detail = resp.text
            results.append({"field": api_name, "status": "error", "detail": error_detail})
    return {"results": results}

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
    org_id = request.session["userinfo"].get("org_id", user_id)  # Adjust as needed
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
    org_id = request.session["userinfo"].get("org_id", user_id)  

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
    org_id = request.session["userinfo"].get("org_id", user_id)  # adjust as needed

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
                
                # Log failed sync attempts for all carriers
                for carrier in carriers:
                    try:
                        create_sync_history_record(
                            db=db,
                            usdot=carrier.usdot,
                            crm_sync_status="FAILED",
                            crm_object_type="account",
                            crm_object_id=None,  # No ID since it failed
                            crm_platform="salesforce",
                            crm_synched_at=datetime.utcnow(),
                            user_id=user_id,
                            org_id=org_id,
                            detail=f"HTTP {resp.status_code}: {resp.text}"
                        )
                        update_crm_sync_status(
                            db=db,
                            usdot=carrier.usdot,
                            org_id=org_id,
                            user_id=user_id,
                            crm_sync_status="FAILED",
                            crm_object_id=None,
                            crm_synched_at=datetime.utcnow(),
                            crm_platform="salesforce"
                        )
                    except Exception as e:
                        logger.error(f"Failed to log sync failure for USDOT {carrier.usdot}: {str(e)}")
                
                return JSONResponse(status_code=resp.status_code, content={"detail": f"Salesforce error: {resp.text}"})
        
        # Parse Salesforce response and log sync results
        sf_response = resp.json()
        crm_synched_at = datetime.utcnow()
        
        logger.info(f"Salesforce response: {sf_response}")
        
        # Create mapping from referenceId to carrier for result processing
        carrier_map = {f"carrier_{carrier.usdot}": carrier for carrier in carriers}
        
        if sf_response.get("hasErrors", False):
            # Handle response with errors
            results = sf_response.get("results", [])
            
            for result in results:
                reference_id = result.get("referenceId")
                carrier = carrier_map.get(reference_id)
                
                if not carrier:
                    logger.warning(f"Could not find carrier for referenceId: {reference_id}")
                    continue
                
                if "errors" in result:
                    # Failed sync
                    error_details = []
                    for error in result["errors"]:
                        error_details.append(f"{error.get('statusCode', 'UNKNOWN')}: {error.get('message', 'Unknown error')}")
                    detail = "; ".join(error_details)
                    
                    try:
                        create_sync_history_record(
                            db=db,
                            usdot=carrier.usdot,
                            crm_sync_status="FAILED",
                            crm_object_type="account",
                            crm_object_id=None,  # No ID since it failed
                            crm_platform="salesforce",
                            user_id=user_id,
                            org_id=org_id,
                            detail=detail,
                            crm_synched_at=crm_synched_at
                        )
                        update_crm_sync_status(
                            db=db,
                            usdot=carrier.usdot,
                            org_id=org_id,
                            user_id=user_id,
                            crm_sync_status="FAILED",
                            crm_object_id=None,
                            crm_synched_at=crm_synched_at,
                            crm_platform="salesforce"
                        )
                        logger.info(f"Logged failed sync for USDOT {carrier.usdot}: {detail}")
                    except Exception as e:
                        logger.error(f"Failed to log sync failure for USDOT {carrier.usdot}: {str(e)}")
                
                elif "id" in result:
                    # Successful sync
                    salesforce_id = result["id"]
                    
                    try:
                        create_sync_history_record(
                            db=db,
                            usdot=carrier.usdot,
                            crm_sync_status="SUCCESS",
                            crm_object_type="account",
                            crm_platform="salesforce",
                            crm_object_id=salesforce_id,
                            crm_synched_at=crm_synched_at,
                            user_id=user_id,
                            org_id=org_id,
                            detail=f"Successfully created Account with ID: {salesforce_id}",
                        )
                        update_crm_sync_status(
                            db=db,
                            usdot=carrier.usdot,
                            org_id=org_id,
                            user_id=user_id,
                            crm_sync_status="SUCCESS",
                            crm_object_id=salesforce_id,
                            crm_synched_at=crm_synched_at,
                            crm_platform="salesforce"
                        )
                        logger.info(f"Logged successful sync for USDOT {carrier.usdot} -> Salesforce ID: {salesforce_id}")
                    except Exception as e:
                        logger.error(f"Failed to log sync success for USDOT {carrier.usdot}: {str(e)}")
        else:
            # All successful - process results
            results = sf_response.get("results", [])
            
            for result in results:
                reference_id = result.get("referenceId")
                salesforce_id = result.get("id")
                carrier = carrier_map.get(reference_id)
                
                if not carrier:
                    logger.warning(f"Could not find carrier for referenceId: {reference_id}")
                    continue
                
                if salesforce_id:
                    try:
                        create_sync_history_record(
                            db=db,
                            usdot=carrier.usdot,
                            crm_sync_status="SUCCESS",
                            crm_object_type="account",
                            crm_platform="salesforce",
                            crm_object_id=salesforce_id,
                            crm_synched_at=crm_synched_at,
                            user_id=user_id,
                            org_id=org_id,
                            detail=f"Successfully created Account with ID: {salesforce_id}",
                        )
                        update_crm_sync_status(
                            db=db,
                            usdot=carrier.usdot,
                            org_id=org_id,
                            user_id=user_id,
                            crm_sync_status="SUCCESS",
                            crm_object_id=salesforce_id,
                            crm_synched_at=crm_synched_at,
                            crm_platform="salesforce"
                        )
                        logger.info(f"Logged successful sync for USDOT {carrier.usdot} -> Salesforce ID: {salesforce_id}")
                    except Exception as e:
                        logger.error(f"Failed to log sync success for USDOT {carrier.usdot}: {str(e)}")
        
        logger.info(f"Successfully processed Salesforce sync response for {len(carriers)} carriers.")
        return JSONResponse(content=sf_response)
    else:
        logger.error("Salesforce connection not established.")
        return JSONResponse(status_code=401, content={"detail": "Salesforce connection not established. Please connect first."})
