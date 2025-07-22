"""
Replace CarrierEngagementStatus with CRMSyncStatus system

Revision ID: migration_crm_sync_status
Revises: 8f356b3d316d
Create Date: 2025-01-15 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'migration_crm_sync_status'
down_revision: Union[str, None] = '8f356b3d316d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Apply the migration to upgrade from engagement system to CRM sync system.
    """
    # Update sobject_sync_status table schema
    # Rename sync_status column to sobject_sync_status
    op.alter_column('sobject_sync_status', 'sync_status', new_column_name='sobject_sync_status')
    
    # Add subject_synched_at column
    op.add_column('sobject_sync_status', 
                  sa.Column('subject_synched_at', sa.DateTime(), 
                           nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')))
    
    # Update sobject_sync_history table schema  
    # Rename sobject_type to crm_object_type
    op.alter_column('sobject_sync_history', 'sobject_type', new_column_name='crm_object_type')
    
    # Rename sobject_id to crm_object_id
    op.alter_column('sobject_sync_history', 'sobject_id', new_column_name='crm_object_id')
    
    # Drop carrierengagementstatus table as it's replaced by CRM sync system
    op.drop_table('carrierengagementstatus')


def downgrade() -> None:
    """
    Reverse the migration if needed.
    """
    # Recreate carrierengagementstatus table
    op.create_table(
        'carrierengagementstatus',
        sa.Column('usdot', sa.String(length=32), nullable=False),
        sa.Column('org_id', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('carrier_interested', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('carrier_interested_timestamp', sa.DateTime(), nullable=True),
        sa.Column('carrier_interested_by_user_id', sa.String(length=255), nullable=True),
        sa.Column('carrier_contacted', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('carrier_contacted_timestamp', sa.DateTime(), nullable=True),
        sa.Column('carrier_contacted_by_user_id', sa.String(length=255), nullable=True),
        sa.Column('carrier_followed_up', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('carrier_followed_up_timestamp', sa.DateTime(), nullable=True),
        sa.Column('carrier_followed_up_by_user_id', sa.String(length=255), nullable=True),
        sa.Column('carrier_follow_up_by_date', sa.DateTime(), nullable=True),
        sa.Column('carrier_emailed', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('carrier_emailed_timestamp', sa.DateTime(), nullable=True),
        sa.Column('carrier_emailed_by_user_id', sa.String(length=255), nullable=True),
        sa.Column('rental_notes', sa.String(length=360), nullable=True),
        sa.ForeignKeyConstraint(['usdot'], ['carrierdata.usdot'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('usdot', 'org_id')
    )
    
    # Revert sobject_sync_history table changes
    op.alter_column('sobject_sync_history', 'crm_object_id', new_column_name='sobject_id')
    op.alter_column('sobject_sync_history', 'crm_object_type', new_column_name='sobject_type')
    
    # Revert sobject_sync_status table changes
    op.drop_column('sobject_sync_status', 'subject_synched_at')
    op.alter_column('sobject_sync_status', 'sobject_sync_status', new_column_name='sync_status')