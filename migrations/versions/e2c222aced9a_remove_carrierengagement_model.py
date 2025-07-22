"""Remove carrierengagement model

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
    op.drop_table('carrierengagementstatus')
    

def downgrade() -> None:
    """Downgrade schema."""
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
