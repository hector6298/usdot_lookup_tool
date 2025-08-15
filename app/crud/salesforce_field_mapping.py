import logging
from sqlmodel import Session, select
from app.models.salesforce_field_mapping import SalesforceFieldMapping
from fastapi import HTTPException
from typing import List, Dict, Any

# Set up a module-level logger
logger = logging.getLogger(__name__)

def get_field_mappings_by_org(db: Session, org_id: str) -> List[SalesforceFieldMapping]:
    """Get all active field mappings for an organization."""
    try:
        statement = select(SalesforceFieldMapping).where(
            SalesforceFieldMapping.org_id == org_id,
            SalesforceFieldMapping.is_active == True
        )
        mappings = db.exec(statement).all()
        logger.info(f"Found {len(mappings)} field mappings for org {org_id}")
        return mappings
    except Exception as e:
        logger.error(f"Error getting field mappings for org {org_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

def save_field_mapping(
    db: Session, 
    org_id: str, 
    carrier_field: str, 
    salesforce_field: str,
    field_type: str = "text"
) -> SalesforceFieldMapping:
    """Save or update a field mapping for an organization."""
    try:
        # Check if mapping already exists
        statement = select(SalesforceFieldMapping).where(
            SalesforceFieldMapping.org_id == org_id,
            SalesforceFieldMapping.carrier_field == carrier_field
        )
        existing_mapping = db.exec(statement).first()
        
        if existing_mapping:
            # Update existing mapping
            existing_mapping.salesforce_field = salesforce_field
            existing_mapping.field_type = field_type
            existing_mapping.is_active = True
            mapping = existing_mapping
        else:
            # Create new mapping
            mapping = SalesforceFieldMapping(
                org_id=org_id,
                carrier_field=carrier_field,
                salesforce_field=salesforce_field,
                field_type=field_type,
                is_active=True
            )
            db.add(mapping)
        
        db.commit()
        db.refresh(mapping)
        
        logger.info(f"Saved field mapping: {carrier_field} -> {salesforce_field} for org {org_id}")
        return mapping
        
    except Exception as e:
        logger.error(f"Error saving field mapping for org {org_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

def delete_field_mapping(db: Session, org_id: str, carrier_field: str) -> bool:
    """Delete a field mapping for an organization."""
    try:
        statement = select(SalesforceFieldMapping).where(
            SalesforceFieldMapping.org_id == org_id,
            SalesforceFieldMapping.carrier_field == carrier_field
        )
        mapping = db.exec(statement).first()
        
        if mapping:
            mapping.is_active = False
            db.commit()
            logger.info(f"Deleted field mapping: {carrier_field} for org {org_id}")
            return True
        else:
            logger.warning(f"Field mapping not found: {carrier_field} for org {org_id}")
            return False
            
    except Exception as e:
        logger.error(f"Error deleting field mapping for org {org_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

def get_field_mapping_dict(db: Session, org_id: str) -> Dict[str, str]:
    """Get field mappings as a dictionary for easy lookup during sync."""
    try:
        mappings = get_field_mappings_by_org(db, org_id)
        mapping_dict = {mapping.carrier_field: mapping.salesforce_field for mapping in mappings}
        logger.info(f"Retrieved {len(mapping_dict)} field mappings for org {org_id}")
        return mapping_dict
    except Exception as e:
        logger.error(f"Error getting field mapping dict for org {org_id}: {e}")
        return {}

def create_default_field_mappings(db: Session, org_id: str) -> List[SalesforceFieldMapping]:
    """Create default field mappings for a new organization."""
    default_mappings = [
        {"carrier_field": "legal_name", "salesforce_field": "Name", "field_type": "text"},
        {"carrier_field": "phone", "salesforce_field": "Phone", "field_type": "text"},
        {"carrier_field": "physical_address", "salesforce_field": "BillingStreet", "field_type": "text"},
        {"carrier_field": "mailing_address", "salesforce_field": "ShippingStreet", "field_type": "text"},
        {"carrier_field": "usdot", "salesforce_field": "AccountNumber", "field_type": "text"},
        {"carrier_field": "entity_type", "salesforce_field": "Type", "field_type": "text"},
        {"carrier_field": "usdot_status", "salesforce_field": "Description", "field_type": "text"},
        {"carrier_field": "url", "salesforce_field": "Website", "field_type": "text"},
    ]
    
    created_mappings = []
    try:
        for mapping_data in default_mappings:
            mapping = save_field_mapping(
                db=db,
                org_id=org_id,
                carrier_field=mapping_data["carrier_field"],
                salesforce_field=mapping_data["salesforce_field"],
                field_type=mapping_data["field_type"]
            )
            created_mappings.append(mapping)
        
        logger.info(f"Created {len(created_mappings)} default field mappings for org {org_id}")
        return created_mappings
        
    except Exception as e:
        logger.error(f"Error creating default field mappings for org {org_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
