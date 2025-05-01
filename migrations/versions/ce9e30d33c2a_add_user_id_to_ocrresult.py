"""Add user_id to OCRResult

Revision ID: ce9e30d33c2a
Revises: 278bf10b8f59
Create Date: 2025-04-29 03:32:01.298349

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'ce9e30d33c2a'
down_revision: Union[str, None] = '278bf10b8f59'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add user_id column to ocrresult as nullable
    op.add_column('ocrresult', sa.Column('user_id', sa.VARCHAR(length=360), nullable=True))
    # Fill the user_id column with a default value
    op.execute(
        "UPDATE ocrresult SET user_id = <default_user_id>"  # Replace with actual default user ID
    )
    # Alter the user_id column to be non-nullable
    op.alter_column('ocrresult', 'user_id', nullable=False)

def downgrade() -> None:
    """Downgrade schema."""
    # Remove user_id column from ocrresult
    op.drop_column('ocrresult', 'user_id')