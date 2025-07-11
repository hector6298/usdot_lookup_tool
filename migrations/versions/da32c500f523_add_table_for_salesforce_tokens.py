"""Add table for Salesforce tokens

Revision ID: da32c500f523
Revises: c5f39d26b074
Create Date: 2025-07-10 03:32:53.083384

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from datetime import datetime

# revision identifiers, used by Alembic.
revision: str = 'da32c500f523'
down_revision: Union[str, None] = 'c5f39d26b074'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'oauthtoken',
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('org_id', sa.String(), nullable=False),
        sa.Column('provider', sa.String(), nullable=False, index=True),
        sa.Column('access_token', sa.String(), nullable=False),
        sa.Column('refresh_token', sa.String(), nullable=True),
        sa.Column('token_type', sa.String(), nullable=True),
        sa.Column('issued_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('valid_until', sa.DateTime(), nullable=True),
        sa.Column('token_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint('user_id', 'org_id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('oauthtoken')
    # ### end Alembic commands ###
