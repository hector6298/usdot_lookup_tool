from sqlmodel import Session, select
from datetime import datetime, timedelta
from typing import Optional
from app.models.oauth import OAuthToken
from app.helpers.salesforce_auth import refresh_salesforce_token
from fastapi import HTTPException

def upsert_salesforce_token(db: Session, user_id: str, org_id: str, token_data: dict) -> OAuthToken:
    """Upserts a Salesforce OAuth token for a user and organization.
    If a token already exists, it updates the existing record; otherwise, it creates a new one.
    """
    stmt = select(OAuthToken).where(
        OAuthToken.user_id == user_id,
        OAuthToken.org_id == org_id
    )
    token_obj = db.exec(stmt).first()
    token_issued_at = datetime.fromtimestamp(int(token_data.get('issued_at', 0)) / 1000)
    token_valid_until = token_issued_at + timedelta(seconds=7200)  # Assuming 2 hours validity
    if token_obj:
        token_obj.access_token = token_data.get('access_token')
        token_obj.refresh_token = token_data.get('refresh_token')
        token_obj.token_type = token_data.get('token_type')
        token_obj.issued_at = token_issued_at
        token_obj.valid_until = token_valid_until
        token_obj.provider = 'salesforce'
        token_obj.token_data = token_data
    else:
        token_obj = OAuthToken(
            user_id=user_id,
            org_id=org_id,
            provider='salesforce',
            access_token=token_data.get('access_token'),
            refresh_token=token_data.get('refresh_token'),
            token_type=token_data.get('token_type'),
            issued_at=token_issued_at,
            valid_until=token_valid_until,
            token_data=token_data
        )
        db.add(token_obj)
    db.commit()
    db.refresh(token_obj)
    return token_obj


async def get_valid_salesforce_token(db: Session, user_id: str, org_id:str) -> Optional[OAuthToken]:
    # 1. Get a valid Salesforce access token (refresh if needed)

    stmt = select(OAuthToken).where(
        OAuthToken.user_id == user_id,
        OAuthToken.org_id == org_id,
        OAuthToken.provider == "salesforce"
    )
    token_record: OAuthToken = db.exec(stmt).first()

    if token_record and token_record.access_token:
        # Check expiration
        if token_record.valid_until and token_record.valid_until < datetime.utcnow():
            if token_record.refresh_token:
                token_record = await refresh_salesforce_token(token_record.refresh_token,
                                                              user_id, org_id)
                token_record = upsert_salesforce_token(db, user_id, org_id, token_record.token_data)
            else:
                return None  # No refresh token available, cannot refresh
    else:
        return None
    return token_record
    

def delete_salesforce_token(db: Session, user_id: str, org_id: str, provider: str) -> bool:
    """Deletes a Salesforce OAuth token for a user and organization."""
    stmt = select(OAuthToken).where(
        OAuthToken.user_id == user_id,
        OAuthToken.org_id == org_id,
        OAuthToken.provider == provider
    )
    token_obj = db.exec(stmt).first()
    if token_obj:
        db.delete(token_obj)
        db.commit()
        return True
    return False

