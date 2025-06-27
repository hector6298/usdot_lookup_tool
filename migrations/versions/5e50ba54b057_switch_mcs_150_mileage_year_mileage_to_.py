"""Switch mcs_150_mileage_year_mileage to BigInt

Revision ID: 5e50ba54b057
Revises: 3e69d7a9d560
Create Date: 2025-06-27 21:19:40.451989

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '5e50ba54b057'
down_revision: Union[str, None] = '3e69d7a9d560'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.alter_column(
        'carrierdata',  # your table name, check your DB for the exact name
        'mcs_150_mileage_year_mileage',
        existing_type=sa.INTEGER(),
        type_=sa.BigInteger(),
        existing_nullable=True
    )

def downgrade():
    op.alter_column(
        'carrierdata',
        'mcs_150_mileage_year_mileage',
        existing_type=sa.BigInteger(),
        type_=sa.INTEGER(),
        existing_nullable=True
    )
