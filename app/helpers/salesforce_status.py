"""Helper functions for getting real-time Salesforce connection and sync status."""

from sqlmodel import Session, select, func
from typing import Dict, Tuple, Optional
from app.models.oauth import OAuthToken
from app.models.sobject_sync_status import SObjectSyncStatus
from app.crud.oauth import get_valid_salesforce_token
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


async def get_salesforce_connection_status(
    db: Session, 
    user_id: str, 
    org_id: str
) -> bool:
    """
    Check if user has a valid Salesforce connection.
    Returns True if connected with valid token, False otherwise.
    """
    try:
        token_obj = await get_valid_salesforce_token(db, user_id, org_id)
        return token_obj is not None
    except Exception as e:
        logger.error(f"Error checking Salesforce connection status: {str(e)}")
        return False


def get_sync_statistics(
    db: Session, 
    org_id: str
) -> Dict[str, int]:
    """
    Get sync statistics for an organization.
    
    Returns:
        dict: {
            'synchronized': int,  # Count of successfully synced records
            'not_synchronized': int,  # Count of failed or unsynced records 
            'total': int  # Total records
        }
    """
    try:
        # Count successfully synchronized records
        synchronized_count = db.exec(
            select(func.count(SObjectSyncStatus.usdot))
            .where(
                SObjectSyncStatus.org_id == org_id,
                SObjectSyncStatus.sync_status == "SUCCESS"
            )
        ).one()
        
        # Count failed synchronizations
        failed_count = db.exec(
            select(func.count(SObjectSyncStatus.usdot))
            .where(
                SObjectSyncStatus.org_id == org_id,
                SObjectSyncStatus.sync_status == "FAILED"
            )
        ).one()
        
        total_count = synchronized_count + failed_count
        
        return {
            'synchronized': synchronized_count or 0,
            'not_synchronized': failed_count or 0,
            'total': total_count or 0
        }
        
    except Exception as e:
        logger.error(f"Error getting sync statistics for org {org_id}: {str(e)}")
        return {
            'synchronized': 0,
            'not_synchronized': 0,
            'total': 0
        }


async def get_salesforce_status_summary(
    db: Session,
    user_id: str,
    org_id: str
) -> Dict:
    """
    Get complete Salesforce status summary including connection and sync stats.
    
    Returns:
        dict: {
            'connected': bool,
            'sync_stats': {
                'synchronized': int,
                'not_synchronized': int,
                'total': int
            }
        }
    """
    try:
        # Check connection status
        is_connected = await get_salesforce_connection_status(db, user_id, org_id)
        
        # Get sync statistics
        sync_stats = get_sync_statistics(db, org_id)
        
        return {
            'connected': is_connected,
            'sync_stats': sync_stats
        }
        
    except Exception as e:
        logger.error(f"Error getting Salesforce status summary: {str(e)}")
        return {
            'connected': False,
            'sync_stats': {
                'synchronized': 0,
                'not_synchronized': 0,
                'total': 0
            }
        }