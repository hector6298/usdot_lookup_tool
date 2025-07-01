"""Generate orphan records

Revision ID: c5f39d26b074
Revises: 5e50ba54b057
Create Date: 2025-06-30 21:48:43.249402

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c5f39d26b074'
down_revision: Union[str, None] = '5e50ba54b057'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # ... any schema changes ...
    op.execute(
        """
        INSERT INTO carrierdata (usdot)
        VALUES ('00000000')
        ON CONFLICT (usdot) DO NOTHING;
        """
    )

def downgrade():
    op.execute(
        """
        DELETE FROM carrierdata WHERE usdot = '00000000';
        """
    )