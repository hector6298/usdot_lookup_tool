"""Add lookup_success_flag to ocrresult

Revision ID: bb527a942f17
Revises: c1302e974581
Create Date: 2025-08-05 13:59:10.071152

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'bb527a942f17'
down_revision: Union[str, None] = 'c1302e974581'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add lookup_success_flag to OCRResult
    op.add_column('ocrresult', sa.Column('lookup_success_flag', sa.Boolean(), nullable=False, server_default='false'))
    op.execute("UPDATE ocrresult SET lookup_success_flag = false WHERE dot_reading = '00000000'")
    op.execute("UPDATE ocrresult SET lookup_success_flag = true WHERE dot_reading != '00000000'")  # Set default


def downgrade() -> None:
    """Downgrade schema."""
    # Remove lookup_success_flag from OCRResult
    op.drop_column('ocrresult', 'lookup_success_flag')