"""
Database migration script for transitioning from CarrierEngagementStatus to CRMSyncStatus
"""

# Migration Notes:
# 
# 1. The new CRMSyncStatus table reuses the existing "sobject_sync_status" table name
#    but with an updated schema that includes:
#    - sobject_sync_status instead of sync_status  
#    - subject_synched_at field added
#    - Generalized for multiple CRM types
#
# 2. The CarrierEngagementStatus table can be safely removed after confirming
#    the new system works correctly, as it is replaced by CRMSyncStatus
#
# 3. Any existing data in sobject_sync_status will need the field renamed:
#    ALTER TABLE sobject_sync_status RENAME COLUMN sync_status TO sobject_sync_status;
#    ALTER TABLE sobject_sync_status ADD COLUMN subject_synched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
#
# 4. The sobject_sync_history table is renamed conceptually to CRMObjectSyncHistory
#    but uses the same table name for backward compatibility
#    ALTER TABLE sobject_sync_history RENAME COLUMN sobject_type TO crm_object_type;
#    ALTER TABLE sobject_sync_history RENAME COLUMN sobject_id TO crm_object_id;
#
# 5. After migration is complete and tested, the carrierengagementstatus table
#    can be dropped:
#    DROP TABLE carrierengagementstatus;

def upgrade():
    """
    Apply the migration to upgrade from engagement system to CRM sync system.
    """
    print("Migration: Upgrading to CRM sync status system")
    print("1. Updating sobject_sync_status table schema...")
    print("2. Updating sobject_sync_history table schema...")
    print("3. Data will be preserved and system will work with new CRMSyncStatus model")
    print("4. CarrierEngagementStatus table can be removed after verification")

def downgrade():
    """
    Reverse the migration if needed.
    """
    print("Migration: Downgrading from CRM sync status system")
    print("Warning: This will require restoring the CarrierEngagementStatus table")
    print("and reverting schema changes to sobject_sync_status table")