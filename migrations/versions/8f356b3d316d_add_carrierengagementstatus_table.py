"""Add CarrierEngagementStatus table

Revision ID: 8f356b3d316d
Revises: ce9e30d33c2a
Create Date: 2025-05-21 02:02:45.726985

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '8f356b3d316d'
down_revision: Union[str, None] = 'ce9e30d33c2a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
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

    # for every record in carrierdata, create a record in carrierengagementstatus
    op.execute(
        """
        INSERT INTO carrierengagementstatus (
            usdot, 
            org_id, 
            created_at,
            carrier_interested, 
            carrier_contacted, 
            carrier_followed_up, 
            carrier_emailed
        )
        SELECT 
            usdot, 
            'org_MeXxTWYD3BvxXZ7L',
            now(),
            false,
            false,
            false,
            false
        FROM carrierdata
        ON CONFLICT (usdot, org_id) DO NOTHING
        """
    )

    # Add org_id to OCRResult table
    op.add_column('ocrresult', sa.Column('org_id', sa.String(length=255), nullable=True))

    op.execute(
        "UPDATE ocrresult SET org_id = 'org_MeXxTWYD3BvxXZ7L'"  # Replace with actual default user ID
    )
    # Alter the user_id column to be non-nullable
    op.alter_column('ocrresult', 'org_id', nullable=False)


    # Remove CarruerData old engagement columns
    op.drop_column('carrierdata', 'carrier_interested')
    op.drop_column('carrierdata', 'carrier_contacted')
    op.drop_column('carrierdata', 'carrier_emailed')
    op.drop_column('carrierdata', 'rental_notes')
    op.drop_column('carrierdata', 'carrier_interested_timestamp')
    op.drop_column('carrierdata', 'carrier_contacted_timestamp')
    op.drop_column('carrierdata', 'carrier_emailed_timestamp')


def downgrade() -> None:
    """Downgrade schema."""
    # Recreate the dropped columns in the carrierdata table
    op.add_column('carrierdata', sa.Column('carrier_interested', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('carrierdata', sa.Column('carrier_contacted', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('carrierdata', sa.Column('carrier_emailed', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('carrierdata', sa.Column('rental_notes', sa.String(length=360), nullable=True))
    op.add_column('carrierdata', sa.Column('carrier_interested_timestamp', sa.DateTime(), nullable=True))
    op.add_column('carrierdata', sa.Column('carrier_contacted_timestamp', sa.DateTime(), nullable=True))
    op.add_column('carrierdata', sa.Column('carrier_emailed_timestamp', sa.DateTime(), nullable=True))

    # Remove org_id from OCRResult table
    op.drop_column('ocrresult', 'org_id')
    
    # Drop the carrierengagementstatus table
    op.drop_table('carrierengagementstatus')