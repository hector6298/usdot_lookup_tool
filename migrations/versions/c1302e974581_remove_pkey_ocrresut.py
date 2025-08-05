"""Remove pkey ocrresut

Revision ID: c1302e974581
Revises: e2c222aced9a
Create Date: 2025-08-05 01:44:13.300037

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c1302e974581'
down_revision: Union[str, None] = 'e2c222aced9a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Remove foreign key constraint from OCRResult
    op.drop_constraint('ocrresult_dot_reading_fkey', 'ocrresult', type_='foreignkey')


def downgrade() -> None:
    """Downgrade schema."""
    op.create_foreign_key('ocrresult_dot_reading_fkey', 'ocrresult', 'dot_reading', ['dot_reading_id'], ['id'], ondelete='CASCADE')
