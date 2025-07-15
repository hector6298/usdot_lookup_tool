"""Add Salesforce sync tables

Revision ID: 62b8d32ff6de
Revises: da32c500f523
Create Date: 2025-01-15 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision: str = '62b8d32ff6de'
down_revision: Union[str, None] = 'da32c500f523'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create sobject_sync_history table (append-only audit log)
    op.create_table(
        'sobject_sync_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('usdot', sa.String(), nullable=False, index=True),
        sa.Column('sync_status', sa.String(), nullable=False),
        sa.Column('sync_timestamp', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('sobject_type', sa.String(), nullable=False, server_default=sa.text("'account'")),
        sa.Column('user_id', sa.String(), nullable=False, index=True),
        sa.Column('org_id', sa.String(), nullable=False, index=True),
        sa.Column('sobject_id', sa.String(), nullable=True),
        sa.Column('detail', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create sobject_sync_status table (current status per carrier/org)
    op.create_table(
        'sobject_sync_status',
        sa.Column('usdot', sa.String(), nullable=False),
        sa.Column('org_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('sync_status', sa.String(), nullable=False),
        sa.Column('sobject_id', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['usdot'], ['carrierdata.usdot'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('usdot', 'org_id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('sobject_sync_status')
    op.drop_table('sobject_sync_history')