"""Add role field to UserOrgMembership

Revision ID: 001_add_role
Revises: e2c222aced9a
Create Date: 2025-01-13 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001_add_role'
down_revision: Union[str, None] = 'e2c222aced9a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Add role column to userorgmembership table."""
    # Add role column with default value 'user'
    op.add_column('userorgmembership', sa.Column('role', sa.VARCHAR(), nullable=False, server_default='user'))

def downgrade() -> None:
    """Remove role column from userorgmembership table."""
    op.drop_column('userorgmembership', 'role')