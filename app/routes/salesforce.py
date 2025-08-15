from fastapi import APIRouter, Request,HTTPException, Depends, Form, Body
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from fastapi.responses import RedirectResponse, JSONResponse
from app.database import get_db
from app.crud.oauth import get_valid_salesforce_token, upsert_salesforce_token, delete_salesforce_token
from app.crud.crm_object_sync_history import create_sync_history_record
from app.crud.crm_object_sync_status import update_crm_sync_status
from app.crud.user_org_membership import get_sf_domain_by_org_id, save_sf_domain_for_org
from app.crud.salesforce_field_mapping import (
    get_field_mappings_by_org, 
    save_field_mapping, 
    delete_field_mapping, 
    get_field_mapping_dict,
    create_default_field_mappings
)

from app.models.carrier_data import CarrierData
from app.models.salesforce_field_mapping import SalesforceFieldMapping
from datetime import datetime
import urllib.parse
import httpx
import logging
import os
import time

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Set up a module-level logger
logger = logging.getLogger(__name__)

@router.get("/salesforce/setup")
async def salesforce_setup_page(request: Request):
    """Display Salesforce setup page for entering domain."""
    if 'userinfo' not in request.session:
        return RedirectResponse(url="/login")
    
    return templates.TemplateResponse("salesforce_setup.html", {"request": request})

@router.post("/salesforce/setup")
async def save_salesforce_domain(
    request: Request,
    sf_domain: str = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """Save Salesforce domain for the organization."""
    if 'userinfo' not in request.session:
        return JSONResponse(status_code=401, content={"detail": "User not authenticated."})
    
    user_id = request.session["userinfo"]["sub"]
    org_id = request.session["userinfo"].get("org_id", user_id)
    
    # Validate the domain format
    if not sf_domain or not sf_domain.strip():
        return JSONResponse(status_code=400, content={"detail": "Salesforce domain is required."})
    
    # Clean up the domain (remove https://, trailing slashes, etc.)
    clean_domain = sf_domain.replace("https://", "").replace("http://", "").rstrip("/")
    
    # Basic validation - should end with .salesforce.com or similar
    if not any(clean_domain.endswith(suffix) for suffix in ['.salesforce.com', '.my.salesforce.com', '.lightning.force.com']):
        return JSONResponse(status_code=400, content={"detail": "Invalid Salesforce domain format. Please enter your full Salesforce URL."})
    
    try:
        # Save to your organization table
        save_sf_domain_for_org(db, org_id, clean_domain)
        
        logger.info(f"Saved Salesforce domain {clean_domain} for org {org_id}")
        return JSONResponse(content={"detail": "Salesforce domain saved successfully."})
        
    except Exception as e:
        logger.error(f"Failed to save Salesforce domain: {str(e)}")
        return JSONResponse(status_code=500, content={"detail": "Failed to save Salesforce domain."})

@router.get("/salesforce/connect")
async def connect_salesforce(request: Request, db: Session = Depends(get_db)):
    """Redirects the user to Salesforce OAuth authorization page."""
    if 'userinfo' not in request.session:
        logger.error("Cannot call SF authorization. User not authenticated.")
        return JSONResponse(status_code=401, content={"detail": "User not authenticated."})
    
    org_id = request.session['userinfo'].get('org_id', request.session['userinfo']['sub'])
    org_sf_domain = get_sf_domain_by_org_id(org_id, db)
    
    # If no domain is configured, redirect to setup page
    if not org_sf_domain:
        logger.info(f"No Salesforce domain configured for organization {org_id}. Redirecting to setup.")
        return RedirectResponse(url="/salesforce/setup")
    
    # Determine redirect URI
    if os.environ.get('ENVIRONMENT') == 'dev' and os.environ.get('NGROK_TUNNEL_URL', None):
        redirect_uri = os.environ.get('NGROK_TUNNEL_URL') + '/salesforce/callback'
    elif os.environ.get('BASE_URL'):
        redirect_uri = os.environ.get('BASE_URL') + '/salesforce/callback'
    else:
        redirect_uri = request.url_for("salesforce_callback")

    logger.info("Redirecting to Salesforce OAuth authorization page.")
    
    params = {
        "response_type": "code",
        "client_id": os.environ.get('SF_CONSUMER_KEY'),
        "redirect_uri": redirect_uri
    }
    sf_auth_url = f"https://{org_sf_domain}/services/oauth2/authorize?{urllib.parse.urlencode(params)}"
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


@router.get("/salesforce/field-mapping")
async def field_mapping_page(request: Request, db: Session = Depends(get_db)):
    """Display the field mapping configuration page."""
    if 'userinfo' not in request.session:
        return RedirectResponse(url="/login")
    
    org_id = request.session["userinfo"].get("org_id", request.session["userinfo"]["sub"])
    
    # Get existing mappings
    mappings = get_field_mappings_by_org(db, org_id)
    
    # If no mappings exist, create defaults
    if not mappings:
        mappings = create_default_field_mappings(db, org_id)
    
    context = {
        "request": request,
        "mappings": mappings,
        "available_carrier_fields": SalesforceFieldMapping.AVAILABLE_CARRIER_FIELDS,
        "standard_salesforce_fields": SalesforceFieldMapping.STANDARD_SALESFORCE_FIELDS
    }
    
    return templates.TemplateResponse("salesforce_field_mapping.html", context)


@router.post("/salesforce/field-mapping")
async def save_field_mappings(request: Request, db: Session = Depends(get_db)):
    """Save field mapping configurations."""
    if 'userinfo' not in request.session:
        return JSONResponse(status_code=401, content={"detail": "User not authenticated."})
    
    org_id = request.session["userinfo"].get("org_id", request.session["userinfo"]["sub"])
    
    try:
        form_data = await request.form()
        total_mappings = int(form_data.get("total_mappings", 0))
        
        # Clear existing mappings
        existing_mappings = get_field_mappings_by_org(db, org_id)
        for mapping in existing_mappings:
            mapping.is_active = False
        db.commit()
        
        # Save new mappings
        saved_count = 0
        for i in range(1, total_mappings + 1):
            carrier_field = form_data.get(f"carrier_field_{i}")
            salesforce_field = form_data.get(f"salesforce_field_{i}")
            custom_field = form_data.get(f"custom_salesforce_field_{i}")
            field_type = form_data.get(f"field_type_{i}", "text")
            
            # Use custom field if salesforce field is empty
            if not salesforce_field and custom_field:
                salesforce_field = custom_field
            
            if carrier_field and salesforce_field:
                save_field_mapping(
                    db=db,
                    org_id=org_id,
                    carrier_field=carrier_field,
                    salesforce_field=salesforce_field,
                    field_type=field_type
                )
                saved_count += 1
        
        logger.info(f"Saved {saved_count} field mappings for org {org_id}")
        return RedirectResponse(url="/salesforce/field-mapping?success=1", status_code=303)
        
    except Exception as e:
        logger.error(f"Error saving field mappings for org {org_id}: {e}")
        return RedirectResponse(url="/salesforce/field-mapping?error=1", status_code=303)


@router.post("/salesforce/field-mapping/reset")
async def reset_field_mappings(request: Request, db: Session = Depends(get_db)):
    """Reset field mappings to defaults."""
    if 'userinfo' not in request.session:
        return JSONResponse(status_code=401, content={"detail": "User not authenticated."})
    
    org_id = request.session["userinfo"].get("org_id", request.session["userinfo"]["sub"])
    
    try:
        # Clear existing mappings
        existing_mappings = get_field_mappings_by_org(db, org_id)
        for mapping in existing_mappings:
            mapping.is_active = False
        db.commit()
        
        # Create default mappings
        create_default_field_mappings(db, org_id)
        
        return JSONResponse(content={"detail": "Default mappings created successfully."})
        
    except Exception as e:
        logger.error(f"Error resetting field mappings for org {org_id}: {e}")
        return JSONResponse(status_code=500, content={"detail": "Error resetting field mappings."})


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

        # 3. Get field mappings for this organization
        field_mappings = get_field_mapping_dict(db, org_id)
        if not field_mappings:
            logger.warning(f"No field mappings configured for org {org_id}. Creating defaults.")
            create_default_field_mappings(db, org_id)
            field_mappings = get_field_mapping_dict(db, org_id)

        # 4. Use Salesforce Composite API to insert accounts
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
            record = {
                "attributes": {"type": "Account", "referenceId": f"carrier_{carrier.usdot}"}
            }
            
            # Map fields using the configured mappings
            for carrier_field, salesforce_field in field_mappings.items():
                carrier_value = getattr(carrier, carrier_field, None)
                if carrier_value is not None:
                    # Convert values based on field type if needed
                    if isinstance(carrier_value, (int, float)) and salesforce_field in ["Phone"]:
                        # Convert numeric phone to string
                        carrier_value = str(carrier_value)
                    elif carrier_field in ["dba_name", "legal_name"] and salesforce_field == "Name":
                        # Use legal_name preferentially, fallback to dba_name
                        if carrier_field == "legal_name" and carrier_value:
                            record[salesforce_field] = carrier_value
                        elif carrier_field == "dba_name" and carrier_value and "Name" not in record:
                            record[salesforce_field] = carrier_value
                        continue
                    
                    record[salesforce_field] = carrier_value
            
            # Ensure we have a Name field (required for Account)
            if "Name" not in record:
                record["Name"] = carrier.legal_name or carrier.dba_name or f"Carrier {carrier.usdot}"
            
            records.append(record)

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
