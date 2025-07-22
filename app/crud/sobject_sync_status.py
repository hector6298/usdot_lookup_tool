from sqlmodel import Session, select
from app.models.sobject_sync_status import CRMSyncStatus, SObjectSyncStatus
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
) -> CRMSyncStatus:
    """Create or update sync status record (SCD Type 1)."""
    try:
        # Try to get existing record
        existing_record = db.exec(
            select(CRMSyncStatus).where(
                CRMSyncStatus.usdot == usdot,
                CRMSyncStatus.org_id == org_id
            )
        ).first()
        
        if existing_record:
            # Update existing record
            existing_record.user_id = user_id
            existing_record.updated_at = datetime.utcnow()
            existing_record.sobject_sync_status = sync_status
            existing_record.sobject_id = sobject_id
            if sync_status == "SUCCESS":
                existing_record.sobject_synced_at = datetime.utcnow()
            
            db.add(existing_record)
            db.commit()
            db.refresh(existing_record)
            
            logger.info(f"Updated sync status for USDOT {usdot}, org {org_id} to {sync_status}")
            return existing_record
        else:
            # Create new record
            new_record = CRMSyncStatus(
                usdot=usdot,
                org_id=org_id,
                user_id=user_id,
                sobject_sync_status=sync_status,
                sobject_id=sobject_id,
                sobject_synced_at=datetime.utcnow() if sync_status == "SUCCESS" else None
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


def upsert_carrier_org_status(
    db: Session,
    usdot: str,
    org_id: str,
    user_id: str
) -> CRMSyncStatus:
    """Create or update carrier org status record - this replaces engagement record functionality."""
    try:
        # Try to get existing record
        existing_record = db.exec(
            select(CRMSyncStatus).where(
                CRMSyncStatus.usdot == usdot,
                CRMSyncStatus.org_id == org_id
            )
        ).first()
        
        if existing_record:
            # Update existing record with current user and timestamp
            existing_record.user_id = user_id
            existing_record.updated_at = datetime.utcnow()
            
            db.add(existing_record)
            db.commit()
            db.refresh(existing_record)
            
            logger.info(f"Updated carrier org status for USDOT {usdot}, org {org_id}")
            return existing_record
        else:
            # Create new record with default "PENDING" sync status
            new_record = CRMSyncStatus(
                usdot=usdot,
                org_id=org_id,
                user_id=user_id,
                sobject_sync_status="PENDING"  # Default status for new carrier registrations
            )
            
            db.add(new_record)
            db.commit()
            db.refresh(new_record)
            
            logger.info(f"Created carrier org status for USDOT {usdot}, org {org_id}")
            return new_record
            
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to upsert carrier org status for USDOT {usdot}, org {org_id}: {str(e)}")
        raise


def get_sync_status_by_usdot(
    db: Session,
    usdot: str,
    org_id: str
) -> Optional[CRMSyncStatus]:
    """Get sync status for a specific USDOT and org."""
    try:
        result = db.exec(
            select(CRMSyncStatus).where(
                CRMSyncStatus.usdot == usdot,
                CRMSyncStatus.org_id == org_id
            )
        ).first()
        
        if result:
            logger.info(f"Found sync status for USDOT {usdot}, org {org_id}: {result.sobject_sync_status}")
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get sync status for USDOT {usdot}, org {org_id}: {str(e)}")
        raise


def get_sync_status_by_org(
    db: Session,
    org_id: str,
    sync_status: Optional[str] = None
) -> List[CRMSyncStatus]:
    """Get all sync status records for an org, optionally filtered by status."""
    try:
        query = select(CRMSyncStatus).where(CRMSyncStatus.org_id == org_id)
        
        if sync_status:
            query = query.where(CRMSyncStatus.sobject_sync_status == sync_status)
            
        result = db.exec(query).all()
        logger.info(f"Retrieved {len(result)} sync status records for org {org_id}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to get sync status for org {org_id}: {str(e)}")
        raise


def get_usdots_by_org(
    db: Session,
    org_id: str
) -> List[str]:
    """Get all USDOT numbers that have been registered by an org."""
    try:
        query = select(CRMSyncStatus.usdot).where(CRMSyncStatus.org_id == org_id)
        result = db.exec(query).all()
        logger.info(f"Retrieved {len(result)} USDOT numbers for org {org_id}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to get USDOT numbers for org {org_id}: {str(e)}")
        raise


def get_sync_status_for_usdots(
    db: Session,
    usdots: List[str],
    org_id: str
) -> Dict[str, CRMSyncStatus]:
    """Get sync status for multiple USDOTs in a single query."""
    try:
        query = select(CRMSyncStatus).where(
            CRMSyncStatus.usdot.in_(usdots),
            CRMSyncStatus.org_id == org_id
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
            select(CRMSyncStatus).where(
                CRMSyncStatus.usdot == usdot,
                CRMSyncStatus.org_id == org_id
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