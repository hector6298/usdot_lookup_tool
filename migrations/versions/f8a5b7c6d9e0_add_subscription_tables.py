"""Add subscription tables

Revision ID: f8a5b7c6d9e0
Revises: e2c222aced9a
Create Date: 2025-01-01 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f8a5b7c6d9e0'
down_revision: Union[str, None] = 'e2c222aced9a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create SubscriptionPlan table
    op.create_table(
        'subscriptionplan',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('price_cents', sa.Integer(), nullable=False),
        sa.Column('monthly_quota', sa.Integer(), nullable=False),
        sa.Column('stripe_price_id', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create Subscription table
    op.create_table(
        'subscription',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('org_id', sa.String(), nullable=False),
        sa.Column('plan_id', sa.Integer(), nullable=False),
        sa.Column('stripe_subscription_id', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('current_period_start', sa.DateTime(), nullable=False),
        sa.Column('current_period_end', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['org_id'], ['apporg.org_id']),
        sa.ForeignKeyConstraint(['plan_id'], ['subscriptionplan.id']),
        sa.ForeignKeyConstraint(['user_id'], ['appuser.user_id']),
        sa.PrimaryKeyConstraint('id')
    )

    # Create UsageQuota table
    op.create_table(
        'usagequota',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('subscription_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('org_id', sa.String(), nullable=False),
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('period_end', sa.DateTime(), nullable=False),
        sa.Column('quota_limit', sa.Integer(), nullable=False),
        sa.Column('quota_used', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('quota_remaining', sa.Integer(), nullable=False),
        sa.Column('carryover_from_previous', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['org_id'], ['apporg.org_id']),
        sa.ForeignKeyConstraint(['subscription_id'], ['subscription.id']),
        sa.ForeignKeyConstraint(['user_id'], ['appuser.user_id']),
        sa.PrimaryKeyConstraint('id')
    )

    # Create OneTimePayment table
    op.create_table(
        'onetimepayment',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('org_id', sa.String(), nullable=False),
        sa.Column('stripe_payment_intent_id', sa.String(length=255), nullable=False),
        sa.Column('amount_cents', sa.Integer(), nullable=False),
        sa.Column('quota_purchased', sa.Integer(), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['org_id'], ['apporg.org_id']),
        sa.ForeignKeyConstraint(['user_id'], ['appuser.user_id']),
        sa.PrimaryKeyConstraint('id')
    )

    # Insert default subscription plans
    plans_table = sa.table('subscriptionplan',
        sa.column('name', sa.String),
        sa.column('price_cents', sa.Integer),
        sa.column('monthly_quota', sa.Integer),
        sa.column('is_active', sa.Boolean),
        sa.column('created_at', sa.DateTime)
    )
    
    op.bulk_insert(plans_table, [
        {
            'name': 'Free',
            'price_cents': 0,
            'monthly_quota': 20,
            'is_active': True,
            'created_at': sa.text('NOW()')
        },
        {
            'name': 'Basic',
            'price_cents': 999,
            'monthly_quota': 150,
            'is_active': True,
            'created_at': sa.text('NOW()')
        },
        {
            'name': 'Professional', 
            'price_cents': 2999,
            'monthly_quota': 500,
            'is_active': True,
            'created_at': sa.text('NOW()')
        },
        {
            'name': 'Enterprise',
            'price_cents': 9999,
            'monthly_quota': 2000,
            'is_active': True,
            'created_at': sa.text('NOW()')
        }
    ])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop tables in reverse order due to foreign key constraints
    op.drop_table('onetimepayment')
    op.drop_table('usagequota')
    op.drop_table('subscription')
    op.drop_table('subscriptionplan')