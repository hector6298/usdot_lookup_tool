"""Add engagement columns to CarrierData

Revision ID: 278bf10b8f59
Revises: 
Create Date: 2025-04-14 02:07:21.883695

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'ce9e30d33c2a'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add engagement columns to carrierdata
    op.add_column('carrierdata', sa.Column('carrier_interested', sa.BOOLEAN(), nullable=False, server_default=sa.text('false')))
    op.add_column('carrierdata', sa.Column('carrier_contacted', sa.BOOLEAN(), nullable=False, server_default=sa.text('false')))
    op.add_column('carrierdata', sa.Column('carrier_emailed', sa.BOOLEAN(), nullable=False, server_default=sa.text('false')))
    op.add_column('carrierdata', sa.Column('rental_notes', sa.VARCHAR(length=360), nullable=True))
    op.add_column('carrierdata', sa.Column('carrier_interested_timestamp', postgresql.TIMESTAMP(), nullable=True))
    op.add_column('carrierdata', sa.Column('carrier_contacted_timestamp', postgresql.TIMESTAMP(), nullable=True))
    op.add_column('carrierdata', sa.Column('carrier_emailed_timestamp', postgresql.TIMESTAMP(), nullable=True))

    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    
    # Remove engagement columns from carrierdata
    op.drop_column('carrierdata', 'carrier_interested')
    op.drop_column('carrierdata', 'carrier_contacted')
    op.drop_column('carrierdata', 'carrier_emailed')
    op.drop_column('carrierdata', 'rental_notes')
    op.drop_column('carrierdata', 'carrier_interested_timestamp')
    op.drop_column('carrierdata', 'carrier_contacted_timestamp')
    op.drop_column('carrierdata', 'carrier_emailed_timestamp')

    # ### end Alembic commands ###