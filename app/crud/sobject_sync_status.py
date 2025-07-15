from sqlmodel import Session, select
from app.models.sobject_sync_status import SObjectSyncStatus
from datetime import datetime
from typing import List, Optional, Dict
import logging

logger = logging.getLogger(__name__)


def upsert_sync_status(
    db: Session,
    usdot: str,
    org_id: str,
    user_id: str,
    sync_status: str,
    sobject_id: Optional[str] = None
) -> SObjectSyncStatus:
    """Create or update sync status record (SCD Type 1)."""
    try:
        # Try to get existing record
        existing_record = db.exec(
            select(SObjectSyncStatus).where(
                SObjectSyncStatus.usdot == usdot,
                SObjectSyncStatus.org_id == org_id
            )
        ).first()
        
        if existing_record:
            # Update existing record
            existing_record.user_id = user_id
            existing_record.updated_at = datetime.utcnow()
            existing_record.sync_status = sync_status
            existing_record.sobject_id = sobject_id
            
            db.add(existing_record)
            db.commit()
            db.refresh(existing_record)
            
            logger.info(f"Updated sync status for USDOT {usdot}, org {org_id} to {sync_status}")
            return existing_record
        else:
            # Create new record
            new_record = SObjectSyncStatus(
                usdot=usdot,
                org_id=org_id,
                user_id=user_id,
                sync_status=sync_status,
                sobject_id=sobject_id
            )
            
            db.add(new_record)
            db.commit()
            db.refresh(new_record)
            
            logger.info(f"Created sync status for USDOT {usdot}, org {org_id} with status {sync_status}")
            return new_record
            
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to upsert sync status for USDOT {usdot}, org {org_id}: {str(e)}")
        raise


def get_sync_status_by_usdot(
    db: Session,
    usdot: str,
    org_id: str
) -> Optional[SObjectSyncStatus]:
    """Get sync status for a specific USDOT and org."""
    try:
        result = db.exec(
            select(SObjectSyncStatus).where(
                SObjectSyncStatus.usdot == usdot,
                SObjectSyncStatus.org_id == org_id
            )
        ).first()
        
        if result:
            logger.info(f"Found sync status for USDOT {usdot}, org {org_id}: {result.sync_status}")
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get sync status for USDOT {usdot}, org {org_id}: {str(e)}")
        raise


def get_sync_status_by_org(
    db: Session,
    org_id: str,
    sync_status: Optional[str] = None
) -> List[SObjectSyncStatus]:
    """Get all sync status records for an org, optionally filtered by status."""
    try:
        query = select(SObjectSyncStatus).where(SObjectSyncStatus.org_id == org_id)
        
        if sync_status:
            query = query.where(SObjectSyncStatus.sync_status == sync_status)
            
        result = db.exec(query).all()
        logger.info(f"Retrieved {len(result)} sync status records for org {org_id}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to get sync status for org {org_id}: {str(e)}")
        raise


def get_sync_status_for_usdots(
    db: Session,
    usdots: List[str],
    org_id: str
) -> Dict[str, SObjectSyncStatus]:
    """Get sync status for multiple USDOTs in a single query."""
    try:
        query = select(SObjectSyncStatus).where(
            SObjectSyncStatus.usdot.in_(usdots),
            SObjectSyncStatus.org_id == org_id
        )
        
        results = db.exec(query).all()
        
        # Convert to dictionary for easy lookup
        status_dict = {record.usdot: record for record in results}
        
        logger.info(f"Retrieved sync status for {len(results)} of {len(usdots)} USDOTs for org {org_id}")
        return status_dict
        
    except Exception as e:
        logger.error(f"Failed to get sync status for USDOTs {usdots}, org {org_id}: {str(e)}")
        raise


def delete_sync_status(
    db: Session,
    usdot: str,
    org_id: str
) -> bool:
    """Delete sync status record."""
    try:
        record = db.exec(
            select(SObjectSyncStatus).where(
                SObjectSyncStatus.usdot == usdot,
                SObjectSyncStatus.org_id == org_id
            )
        ).first()
        
        if record:
            db.delete(record)
            db.commit()
            logger.info(f"Deleted sync status for USDOT {usdot}, org {org_id}")
            return True
        else:
            logger.warning(f"No sync status found to delete for USDOT {usdot}, org {org_id}")
            return False
            
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete sync status for USDOT {usdot}, org {org_id}: {str(e)}")
        raise