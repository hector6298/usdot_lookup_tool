import httpx
import os
import logging
from datetime import timedelta, datetime
from app.models.oauth import OAuthToken
from fastapi import HTTPException
# Set up a module-level logger
logger = logging.getLogger(__name__)

async def refresh_salesforce_token(refresh_token: str, user_id: str, org_id: str):
    """Refreshes the Salesforce OAuth token using the provided refresh token."""
    logger.info(f"Refreshing Salesforce token for user {user_id} in org {org_id}.")
    sf_token_url = f"https://{os.environ['SF_DOMAIN']}/services/oauth2/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": os.environ['SF_CONSUMER_KEY'],
        "client_secret": os.environ['SF_CONSUMER_SECRET'],
        "refresh_token": refresh_token,
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(sf_token_url, data=data)
            resp.raise_for_status()
            token_data = resp.json()
            issued_at = datetime.fromtimestamp(int(token_data.get('issued_at', 0)) / 1000)
            valid_until = issued_at + timedelta(seconds=7200)
            token_record = OAuthToken(
                user_id=user_id,  # Assuming user_id is part of the token data
                org_id=org_id,    # Assuming org_id is part of the token data
                provider='salesforce',
                access_token=token_data.get('access_token'),
                refresh_token=token_data.get('refresh_token'),
                token_type=token_data.get('token_type'),
                issued_at=issued_at,
                valid_until=valid_until,  # Set this based on your logic, e.g., 2 hours from issued_at
                token_data=token_data
            )
            logger.info(f"Token refreshed successfully for user {user_id}.")
            return token_record  # Contains new access_token (and possibly a new refresh_token)
    
    except HTTPException as e:
        logger.error(f"Failed to refresh Salesforce token: {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail="Failed to refresh Salesforce token.")