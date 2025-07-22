import logging
from sqlmodel import Session, select
from app.models.crm_sync_status import CRMSyncStatus
from app.models.carrier_data import CarrierData
from datetime import datetime, timezone
from fastapi import HTTPException
from typing import List, Optional, Dict

# Set up a module-level logger
logger = logging.getLogger(__name__)

def get_crm_sync_data(db: Session, 
                      org_id: str = None,
                      offset: int = None, 
                      limit: int = None,
                      carrier_interested: bool = None,
                      carrier_contacted: bool = None) -> List[CRMSyncStatus]:
    """Retrieves CRM sync status records from the database with carrier data."""

    if org_id:
        query = select(CRMSyncStatus).where(
            CRMSyncStatus.org_id == org_id
        ).order_by(CRMSyncStatus.created_at.desc())
    else:
        logger.info("🔍 Fetching all CRM sync status without group filtering.")
        query = select(CRMSyncStatus).order_by(CRMSyncStatus.created_at.desc())

    # Note: carrier_interested and carrier_contacted filters are not applicable 
    # to CRM sync status as these are engagement-specific fields
    # They're kept for API compatibility but ignored

    if offset is not None and limit is not None:
        logger.info(f"🔍 Applying offset: offset={offset}, limit={limit}")
        query = query.offset(offset).limit(limit)
    else:
        logger.info("🔍 Offset is disabled.")

    sync_records = db.exec(query).all()

    # Manually load carrier data for each sync record
    for sync_record in sync_records:
        if not sync_record.carrier_data:
            carrier = db.exec(
                select(CarrierData).where(CarrierData.usdot == sync_record.usdot)
            ).first()
            sync_record.carrier_data = carrier

    logger.info(f"✅ Found {len(sync_records)} CRM sync status records.")

    return sync_records


def generate_crm_sync_records_bulk(db: Session, 
                                   usdot_numbers: list[int], 
                                   user_id: str, 
                                   org_id: str) -> List[CRMSyncStatus]:
    """Generates CRM sync records for the given USDOT numbers."""
    logger.info("🔍 Generating CRM sync records for carriers."
                f"USDOT numbers: {usdot_numbers}, User ID: {user_id}, Org ID: {org_id}")
    sync_records = []
    
    for usdot in usdot_numbers:
        try:
            # Check if the CRM sync record already exists
            existing_sync = db.exec(
                select(CRMSyncStatus).where(
                    CRMSyncStatus.usdot == usdot,
                    CRMSyncStatus.org_id == org_id
                )
            ).first()
            
            if existing_sync:
                logger.info(f"🔍 CRM sync record already exists for USDOT: {usdot} and ORG {org_id}. Updating.")
                existing_sync.user_id = user_id
                existing_sync.updated_at = datetime.now(timezone.utc)
                sync_records.append(existing_sync)
            else:
                # Create a new CRM sync record
                sync_record = CRMSyncStatus(
                    usdot=usdot,
                    org_id=org_id,
                    user_id=user_id,
                    sobject_sync_status="PENDING"  # Default status for new carriers
                )
                sync_records.append(sync_record)

        except Exception as e:
            logger.error(f"❌ Error generating CRM sync record for USDOT {usdot}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        
    return sync_records


def save_crm_sync_records_bulk(db: Session,
                               usdot_numbers: list[int], 
                               user_id: str, 
                               org_id: str) -> List[CRMSyncStatus]:
    """Saves multiple CRM sync records to the database."""
    sync_records = generate_crm_sync_records_bulk(db, usdot_numbers, user_id, org_id)
    try:
        logger.info(f"🔍 Saving {len(sync_records)} CRM sync records to the database.")
        db.add_all(sync_records)
        db.commit()

        # Refresh all records to get the latest state
        for record in sync_records:
            db.refresh(record)

        logger.info("✅ All CRM sync records saved successfully.")
        return sync_records
    except Exception as e:
        logger.error(f"❌ Error saving CRM sync records: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


def update_crm_sync_status(db: Session, 
                           usdot: str,
                           org_id: str,
                           user_id: str,
                           sync_status: str,
                           sobject_id: Optional[str] = None) -> CRMSyncStatus:
    """Updates CRM sync status for a specific carrier and org."""
    try:
        logger.info(f"Updating CRM sync status for DOT number: {usdot}, org: {org_id}, status: {sync_status}")

        # Check if the CRM sync record exists
        sync_record = db.exec(
            select(CRMSyncStatus).where(
                CRMSyncStatus.usdot == usdot,
                CRMSyncStatus.org_id == org_id
            )
        ).first()
        
        if not sync_record:
            logger.warning(f"⚠ No CRM sync record found for DOT number: {usdot}, org: {org_id}")
            return None

        # Update the sync status
        sync_record.user_id = user_id
        sync_record.updated_at = datetime.now(timezone.utc)
        sync_record.sobject_sync_status = sync_status
        sync_record.subject_synched_at = datetime.now(timezone.utc)
        if sobject_id:
            sync_record.sobject_id = sobject_id
        
        db.commit()
        db.refresh(sync_record)
        logger.info(f"✅ CRM sync status updated for DOT number: {usdot}")
        return sync_record
    except Exception as e:
        logger.error(f"❌ Error updating CRM sync status for DOT {usdot}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


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