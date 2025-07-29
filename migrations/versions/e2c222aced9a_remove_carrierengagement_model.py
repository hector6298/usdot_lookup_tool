"""Rename sobject tables to crm tables and update columns/properties

Revision ID: e2c222aced9a
Revises: 62b8d32ff6de
Create Date: 2025-07-22 14:03:18.375100

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e2c222aced9a'
down_revision: Union[str, None] = '62b8d32ff6de'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop old engagement table
    op.drop_table('carrierengagementstatus')

    # Rename sobject_sync_history to crmobjectsynchistory and update columns
    op.rename_table('sobject_sync_history', 'crmobjectsynchistory')
    op.alter_column('crmobjectsynchistory', 'sync_status', new_column_name='crm_sync_status')
    op.alter_column('crmobjectsynchistory', 'sync_timestamp', new_column_name='crm_synched_at')
    op.alter_column('crmobjectsynchistory', 'sobject_type', new_column_name='crm_object_type')
    op.alter_column('crmobjectsynchistory', 'sobject_id', new_column_name='crm_object_id')

    # Add new columns if needed
    op.add_column('crmobjectsynchistory', sa.Column('crm_platform', sa.String(length=32), nullable=True))

    # Rename sobject_sync_status to crmobjectsyncstatus and update columns
    op.rename_table('sobject_sync_status', 'crmobjectsyncstatus')
    op.alter_column('crmobjectsyncstatus', 'sync_status', new_column_name='crm_sync_status')
    op.alter_column('crmobjectsyncstatus', 'sobject_id', new_column_name='crm_object_id')

    # Add new columns if needed
    op.add_column('crmobjectsyncstatus', sa.Column('crm_synched_at', postgresql.TIMESTAMP(), nullable=True))
    op.add_column('crmobjectsyncstatus', sa.Column('crm_platform', sa.String(length=32), nullable=True))
    # Add foreign keys for org_id and user_id
    op.create_foreign_key(
        'fk_crm_object_sync_status_org_id',
        'crmobjectsyncstatus',
        'apporg',
        ['org_id'],
        ['org_id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_crm_object_sync_status_user_id',
        'crmobjectsyncstatus',
        'appuser',
        ['user_id'],
        ['user_id'],
        ondelete='CASCADE'
    )

def downgrade() -> None:
    """Downgrade schema."""
    # Drop new columns
    op.drop_column('crmobjectsyncstatus', 'crm_platform')
    op.drop_column('crmobjectsyncstatus', 'crm_synched_at')
    op.drop_column('crmobjectsynchistory', 'crm_platform')
    op.alter_column('crmobjectsynchistory', 'crm_object_id', new_column_name='sobject_id')
    op.alter_column('crmobjectsynchistory', 'crm_object_type', new_column_name='sobject_type')
    op.alter_column('crmobjectsynchistory', 'crm_synched_at', new_column_name='sync_timestamp')
    op.alter_column('crmobjectsynchistory', 'crm_sync_status', new_column_name='sync_status')

    op.alter_column('crmobjectsyncstatus', 'crm_sync_status', new_column_name='sync_status')
    op.alter_column('crmobjectsyncstatus', 'crm_object_id', new_column_name='sobject_id')

    # Drop foreign keys
    op.drop_constraint('fk_crm_object_sync_status_org_id', 'crmobjectsyncstatus', type_='foreignkey')
    op.drop_constraint('fk_crm_object_sync_status_user_id', 'crmobjectsyncstatus', type_='foreignkey')

    op.rename_table('crmobjectsynchistory', 'sobject_sync_history')
    op.rename_table('crmobjectsyncstatus', 'sobject_sync_status')    

    # Restore engagement table
    op.create_table('carrierengagementstatus',
        sa.Column('usdot', sa.VARCHAR(length=32), autoincrement=False, nullable=False),
        sa.Column('org_id', sa.VARCHAR(length=255), autoincrement=False, nullable=False),
        sa.Column('created_at', postgresql.TIMESTAMP(), server_default=sa.text('now()'), autoincrement=False, nullable=False),
        sa.Column('carrier_interested', sa.BOOLEAN(), server_default=sa.text('false'), autoincrement=False, nullable=False),
        sa.Column('carrier_interested_timestamp', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column('carrier_interested_by_user_id', sa.VARCHAR(length=255), autoincrement=False, nullable=True),
        sa.Column('carrier_contacted', sa.BOOLEAN(), server_default=sa.text('false'), autoincrement=False, nullable=False),
        sa.Column('carrier_contacted_timestamp', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column('carrier_contacted_by_user_id', sa.VARCHAR(length=255), autoincrement=False, nullable=True),
        sa.Column('carrier_followed_up', sa.BOOLEAN(), server_default=sa.text('false'), autoincrement=False, nullable=False),
        sa.Column('carrier_followed_up_timestamp', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column('carrier_followed_up_by_user_id', sa.VARCHAR(length=255), autoincrement=False, nullable=True),
        sa.Column('carrier_follow_up_by_date', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column('carrier_emailed', sa.BOOLEAN(), server_default=sa.text('false'), autoincrement=False, nullable=False),
        sa.Column('carrier_emailed_timestamp', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column('carrier_emailed_by_user_id', sa.VARCHAR(length=255), autoincrement=False, nullable=True),
        sa.Column('rental_notes', sa.VARCHAR(length=360), autoincrement=False, nullable=True),
        sa.Column('user_id', sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.ForeignKeyConstraint(['org_id'], ['apporg.org_id'], name=op.f('carrierengagementstatus_org_id_fkey')),
        sa.ForeignKeyConstraint(['usdot'], ['carrierdata.usdot'], name=op.f('carrierengagementstatus_usdot_fkey'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['appuser.user_id'], name=op.f('carrierengagementstatus_user_id_fkey')),
        sa.PrimaryKeyConstraint('usdot', 'org_id', name=op.f('carrierengagementstatus_pkey'))
    )