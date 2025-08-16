"""add_salesforce_object_to_field_mapping

Revision ID: c435f7f35f69
Revises: eb01b8dd0869
Create Date: 2025-08-16 16:47:03.268188

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c435f7f35f69'
down_revision: Union[str, None] = 'eb01b8dd0869'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add salesforce_object column to the salesforcefieldmapping table
    op.add_column('salesforcefieldmapping', sa.Column('salesforce_object', sa.String(), nullable=False, server_default='Account'))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove the salesforce_object column from the salesforcefieldmapping table
    op.drop_column('salesforcefieldmapping', 'salesforce_object')
