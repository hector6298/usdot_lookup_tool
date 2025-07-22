from sqlmodel import Session, select
from app.models.sobject_sync_history import CRMObjectSyncHistory, SObjectSyncHistory
from datetime import datetime
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


def create_sync_history_record(
    db: Session,
    usdot: str,
    sync_status: str,
    crm_object_type: str,
    user_id: str,
    org_id: str,
    crm_object_id: Optional[str] = None,
    detail: Optional[str] = None,
    sync_timestamp: Optional[datetime] = None
) -> CRMObjectSyncHistory:
    """Create a new sync history record."""
    try:
        sync_record = CRMObjectSyncHistory(
            usdot=usdot,
            sync_status=sync_status,
            crm_object_type=crm_object_type,
            user_id=user_id,
            org_id=org_id,
            crm_object_id=crm_object_id,
            detail=detail,
            sync_timestamp=sync_timestamp or datetime.utcnow()
        )
        
        db.add(sync_record)
        db.commit()
        db.refresh(sync_record)
        
        logger.info(f"Created sync history record for USDOT {usdot} with status {sync_status}")
        return sync_record
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create sync history record for USDOT {usdot}: {str(e)}")
        raise


def get_sync_history_by_usdot(
    db: Session,
    usdot: str,
    org_id: Optional[str] = None,
    limit: int = 100
) -> List[CRMObjectSyncHistory]:
    """Get sync history records for a specific USDOT number."""
    try:
        query = select(CRMObjectSyncHistory).where(CRMObjectSyncHistory.usdot == usdot)
        
        if org_id:
            query = query.where(CRMObjectSyncHistory.org_id == org_id)
            
        query = query.order_by(CRMObjectSyncHistory.sync_timestamp.desc()).limit(limit)
        
        result = db.exec(query).all()
        logger.info(f"Retrieved {len(result)} sync history records for USDOT {usdot}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to get sync history for USDOT {usdot}: {str(e)}")
        raise


def get_sync_history_by_org(
    db: Session,
    org_id: str,
    user_id: Optional[str] = None,
    limit: int = 1000
) -> List[CRMObjectSyncHistory]:
    """Get sync history records for a specific org."""
    try:
        query = select(CRMObjectSyncHistory).where(CRMObjectSyncHistory.org_id == org_id)
        
        if user_id:
            query = query.where(CRMObjectSyncHistory.user_id == user_id)
            
        query = query.order_by(CRMObjectSyncHistory.sync_timestamp.desc()).limit(limit)
        
        result = db.exec(query).all()
        logger.info(f"Retrieved {len(result)} sync history records for org {org_id}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to get sync history for org {org_id}: {str(e)}")
        raise