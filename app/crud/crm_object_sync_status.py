from sqlmodel import Session, select
from app.models.crm_object_sync_status import CRMObjectSyncStatus
from datetime import datetime
from typing import List, Optional, Dict
import logging
from fastapi import HTTPException

logger = logging.getLogger(__name__)

def get_crm_sync_data(
    db: Session,
    org_id: str = None,
    offset: int = None,
    limit: int = None,
    crm_sync_status: Optional[str] = None,
    usdot_filter: Optional[str] = None
) -> List[CRMObjectSyncStatus]:
    """Get all sync status records for an org, optionally filtered by status and USDOT."""
    try:
        query = select(CRMObjectSyncStatus)

        if org_id:
            query = query.where(CRMObjectSyncStatus.org_id == org_id)
            logger.info(f"🔍 Filtering CRM sync data by org ID: {org_id}")
        
        if crm_sync_status:
            query = query.where(CRMObjectSyncStatus.crm_sync_status == crm_sync_status)
            logger.info(f"🔍 Filtering CRM sync data by sync status: {crm_sync_status}")

        if usdot_filter:
            # usdot_filter can be a partial match or a full match
            query = query.where(CRMObjectSyncStatus.usdot.like(f"%{usdot_filter}%"))
            logger.info(f"🔍 Filtering CRM sync data by USDOT filter: {usdot_filter}")
        
        # Order by timestamp descending (newest first)
        query = query.order_by(CRMObjectSyncStatus.created_at.desc())

        if offset is not None and limit is not None:
            logger.info(f"🔍 Applying offset: offset={offset}, limit={limit}")
            query = query.offset(offset).limit(limit)
        else:
            logger.info("🔍 Offset is disabled.")

        result = db.exec(query).all()
        logger.info(f"Retrieved {len(result)} sync status records for org {org_id}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to get sync status for org {org_id}: {str(e)}")
        raise

def generate_crm_sync_records(db: Session, 
                                usdot_numbers: list[int], 
                                user_id: str, 
                                org_id:str) -> list[CRMObjectSyncStatus]:
    """Generates CRM Sync records for the given USDOT numbers."""

    sync_records = []
    for usdot in usdot_numbers:
        try:

            # Check if the engagement record already exists
            existing_engagement = db.query(CRMObjectSyncStatus)\
                                     .filter(CRMObjectSyncStatus.usdot == usdot,
                                             CRMObjectSyncStatus.org_id == org_id)\
                                     .first()
            if existing_engagement:
                logger.info(f"🔍 Updating USDOT: {usdot} and ORG {org_id}.")
                # Update existing record
                existing_engagement.user_id = user_id
                existing_engagement.updated_at = datetime.utcnow()
                sync_records.append(existing_engagement)
            else:
                logger.info(f"🔍 Creating new sync record for USDOT: {usdot} and ORG {org_id}.")
            
                # Create a new engagement record
                engagement_record = CRMObjectSyncStatus(
                    usdot=usdot,
                    org_id=org_id,
                    user_id=user_id,
                    crm_sync_status="NOT_SYNCED",
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    crm_object_id=None,  # Initially set to None
                    crm_synched_at=None,
                    crm_platform=None
                )
                sync_records.append(engagement_record)

        except Exception as e:
            logger.error(f"❌ Error generating CRM sync record for USDOT {usdot}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        
    return sync_records

def save_crm_sync_status_bulk(
    db: Session,
    usdot_numbers: list[int],
    user_id: str,
    org_id: str
) -> None:
    """Saves multiple CRM sync status records to the database."""
    sync_records = generate_crm_sync_records(db, usdot_numbers, user_id, org_id)
    try:
        logger.info(f"🔍 Saving {len(sync_records)} CRM sync status records to the database.")
        db.add_all(sync_records)
        db.commit()

        # Refresh all records to get the latest state
        for record in sync_records:
            db.refresh(record)

        logger.info("✅ All CRM sync status records saved successfully.")
    except Exception as e:
        logger.error(f"❌ Error saving CRM sync status records in bulk: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    

def update_crm_sync_status(
    db: Session,
    usdot: str,
    org_id: str,
    user_id: str,
    crm_sync_status: str,
    crm_object_id: Optional[str] = None,
    crm_synched_at: Optional[datetime] = None,
    crm_platform: Optional[str] = None
) -> CRMObjectSyncStatus:
    """Create or update sync status record (SCD Type 1)."""
    try:
        # Try to get existing record
        existing_record = db.exec(
            select(CRMObjectSyncStatus).where(
                CRMObjectSyncStatus.usdot == usdot,
                CRMObjectSyncStatus.org_id == org_id
            )
        ).first()
        
        if existing_record:
            # Update existing record
            existing_record.user_id = user_id
            existing_record.updated_at = datetime.utcnow()
            existing_record.crm_sync_status = crm_sync_status
            existing_record.crm_object_id = crm_object_id
            existing_record.crm_synched_at = crm_synched_at
            existing_record.crm_platform = crm_platform
            
            db.add(existing_record)
            db.commit()
            db.refresh(existing_record)
            
            logger.info(f"Updated sync status for USDOT {usdot}, org {org_id} to {crm_sync_status}")
            return existing_record
        else:
            # Create new record
            new_record = CRMObjectSyncStatus(
                usdot=usdot,
                org_id=org_id,
                user_id=user_id,
                crm_sync_status=crm_sync_status,
                crm_object_id=crm_object_id,
                crm_synched_at=crm_synched_at,
                crm_platform=crm_platform,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.add(new_record)
            db.commit()
            db.refresh(new_record)
            
            logger.info(f"Created sync status for USDOT {usdot}, org {org_id} with status {crm_sync_status}")
            return new_record
            
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to upsert sync status for USDOT {usdot}, org {org_id}: {str(e)}")
        raise


def get_sync_status_by_usdot(
    db: Session,
    usdot: str,
    org_id: str
) -> Optional[CRMObjectSyncStatus]:
    """Get sync status for a specific USDOT and org."""
    try:
        result = db.exec(
            select(CRMObjectSyncStatus).where(
                CRMObjectSyncStatus.usdot == usdot,
                CRMObjectSyncStatus.org_id == org_id
            )
        ).first()
        
        if result:
            logger.info(f"Found sync status for USDOT {usdot}, org {org_id}: {result.crm_sync_status}")
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get sync status for USDOT {usdot}, org {org_id}: {str(e)}")
        raise


def delete_sync_status(
    db: Session,
    usdot: str,
    org_id: str
) -> bool:
    """Delete sync status record."""
    try:
        record = db.exec(
            select(CRMObjectSyncStatus).where(
                CRMObjectSyncStatus.usdot == usdot,
                CRMObjectSyncStatus.org_id == org_id
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