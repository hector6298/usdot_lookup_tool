from sqlmodel import Session, select
from app.models.sobject_sync_status import CRMSyncStatus
from datetime import datetime, timezone
from typing import List, Optional, Dict
import logging

logger = logging.getLogger(__name__)


def upsert_crm_sync_status(
    db: Session,
    usdot: str,
    org_id: str,
    user_id: str,
    sync_status: str,
    sobject_id: Optional[str] = None
) -> CRMSyncStatus:
    """Create or update CRM sync status record (SCD Type 1)."""
    try:
        # Try to get existing record
        existing_record = db.exec(
            select(CRMSyncStatus).where(
                CRMSyncStatus.usdot == usdot,
                CRMSyncStatus.org_id == org_id
            )
        ).first()
        
        current_time = datetime.now(timezone.utc)
        
        if existing_record:
            # Update existing record
            existing_record.user_id = user_id
            existing_record.updated_at = current_time
            existing_record.sobject_sync_status = sync_status
            existing_record.subject_synched_at = current_time
            existing_record.sobject_id = sobject_id
            
            db.add(existing_record)
            db.commit()
            db.refresh(existing_record)
            
            logger.info(f"Updated CRM sync status for USDOT {usdot}, org {org_id} to {sync_status}")
            return existing_record
        else:
            # Create new record
            new_record = CRMSyncStatus(
                usdot=usdot,
                org_id=org_id,
                user_id=user_id,
                sobject_sync_status=sync_status,
                subject_synched_at=current_time,
                sobject_id=sobject_id
            )
            
            db.add(new_record)
            db.commit()
            db.refresh(new_record)
            
            logger.info(f"Created CRM sync status for USDOT {usdot}, org {org_id} with status {sync_status}")
            return new_record
            
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to upsert CRM sync status for USDOT {usdot}, org {org_id}: {str(e)}")
        raise


def get_crm_sync_status_by_usdot(
    db: Session,
    usdot: str,
    org_id: str
) -> Optional[CRMSyncStatus]:
    """Get CRM sync status for a specific USDOT and org."""
    try:
        result = db.exec(
            select(CRMSyncStatus).where(
                CRMSyncStatus.usdot == usdot,
                CRMSyncStatus.org_id == org_id
            )
        ).first()
        
        if result:
            logger.info(f"Found CRM sync status for USDOT {usdot}, org {org_id}: {result.sobject_sync_status}")
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get CRM sync status for USDOT {usdot}, org {org_id}: {str(e)}")
        raise


def get_crm_sync_status_by_org(
    db: Session,
    org_id: str,
    sync_status: Optional[str] = None
) -> List[CRMSyncStatus]:
    """Get all CRM sync status records for an org, optionally filtered by status."""
    try:
        query = select(CRMSyncStatus).where(CRMSyncStatus.org_id == org_id)
        
        if sync_status:
            query = query.where(CRMSyncStatus.sobject_sync_status == sync_status)
            
        result = db.exec(query).all()
        logger.info(f"Retrieved {len(result)} CRM sync status records for org {org_id}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to get CRM sync status for org {org_id}: {str(e)}")
        raise


def get_crm_sync_status_for_usdots(
    db: Session,
    usdots: List[str],
    org_id: str
) -> Dict[str, CRMSyncStatus]:
    """Get CRM sync status for multiple USDOTs in a single query."""
    try:
        query = select(CRMSyncStatus).where(
            CRMSyncStatus.usdot.in_(usdots),
            CRMSyncStatus.org_id == org_id
        )
        
        results = db.exec(query).all()
        
        # Convert to dictionary for easy lookup
        status_dict = {record.usdot: record for record in results}
        
        logger.info(f"Retrieved CRM sync status for {len(results)} of {len(usdots)} USDOTs for org {org_id}")
        return status_dict
        
    except Exception as e:
        logger.error(f"Failed to get CRM sync status for USDOTs {usdots}, org {org_id}: {str(e)}")
        raise


def delete_crm_sync_status(
    db: Session,
    usdot: str,
    org_id: str
) -> bool:
    """Delete CRM sync status record."""
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
            logger.info(f"Deleted CRM sync status for USDOT {usdot}, org {org_id}")
            return True
        else:
            logger.warning(f"No CRM sync status found to delete for USDOT {usdot}, org {org_id}")
            return False
            
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete CRM sync status for USDOT {usdot}, org {org_id}: {str(e)}")
        raise


# Keep old function names for backward compatibility during migration
upsert_sync_status = upsert_crm_sync_status
get_sync_status_by_usdot = get_crm_sync_status_by_usdot
get_sync_status_by_org = get_crm_sync_status_by_org
get_sync_status_for_usdots = get_crm_sync_status_for_usdots
delete_sync_status = delete_crm_sync_status