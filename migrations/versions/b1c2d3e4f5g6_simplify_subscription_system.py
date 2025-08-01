"""Simplify subscription system to use Stripe infrastructure

Revision ID: b1c2d3e4f5g6
Revises: a1b2c3d4e5f6
Create Date: 2025-01-01 20:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b1c2d3e4f5g6'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to simplified subscription system."""
    
    # Create new subscription_mapping table
    op.create_table(
        'subscription_mapping',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('org_id', sa.String(), nullable=False),
        sa.Column('stripe_customer_id', sa.String(length=255), nullable=False),
        sa.Column('stripe_subscription_id', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['org_id'], ['apporg.org_id']),
        sa.ForeignKeyConstraint(['user_id'], ['appuser.user_id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'org_id', name='unique_user_org_mapping')
    )
    
    # Migrate existing subscription data to new table
    # Only migrate subscriptions that have valid Stripe IDs
    op.execute("""
        INSERT INTO subscription_mapping (user_id, org_id, stripe_customer_id, stripe_subscription_id, created_at)
        SELECT user_id, org_id, stripe_customer_id, stripe_subscription_id, created_at
        FROM subscription 
        WHERE stripe_customer_id IS NOT NULL 
        AND stripe_customer_id != ''
        AND stripe_subscription_id IS NOT NULL 
        AND stripe_subscription_id != ''
        AND status = 'active'
    """)
    
    # Drop old subscription tables
    # Note: The foreign key constraints will be dropped automatically
    op.drop_table('subscription')
    op.drop_table('subscriptionplan')


def downgrade() -> None:
    """Downgrade schema back to original subscription system."""
    
    # Recreate SubscriptionPlan table
    op.create_table(
        'subscriptionplan',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('stripe_price_id', sa.String(length=255), nullable=False),
        sa.Column('free_quota', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Recreate Subscription table
    op.create_table(
        'subscription',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('org_id', sa.String(), nullable=False),
        sa.Column('plan_id', sa.Integer(), nullable=False),
        sa.Column('stripe_subscription_id', sa.String(length=255), nullable=False),
        sa.Column('stripe_customer_id', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['org_id'], ['apporg.org_id']),
        sa.ForeignKeyConstraint(['plan_id'], ['subscriptionplan.id']),
        sa.ForeignKeyConstraint(['user_id'], ['appuser.user_id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Restore default plans
    plans_table = sa.table('subscriptionplan',
        sa.column('name', sa.String),
        sa.column('stripe_price_id', sa.String),
        sa.column('free_quota', sa.Integer),
        sa.column('is_active', sa.Boolean),
        sa.column('created_at', sa.DateTime)
    )
    
    op.bulk_insert(plans_table, [
        {
            'name': 'Free',
            'stripe_price_id': 'price_free_tier',
            'free_quota': 20,
            'is_active': True,
            'created_at': sa.text('NOW()')
        },
        {
            'name': 'Basic',
            'stripe_price_id': 'price_basic_tier',
            'free_quota': 20,
            'is_active': True,
            'created_at': sa.text('NOW()')
        },
        {
            'name': 'Professional',
            'stripe_price_id': 'price_professional_tier',
            'free_quota': 20,
            'is_active': True,
            'created_at': sa.text('NOW()')
        },
        {
            'name': 'Enterprise',
            'stripe_price_id': 'price_enterprise_tier',
            'free_quota': 20,
            'is_active': True,
            'created_at': sa.text('NOW()')
        }
    ])
    
    # Migrate data back from subscription_mapping to subscription table
    # This requires creating fake plan mappings
    op.execute("""
        INSERT INTO subscription (user_id, org_id, plan_id, stripe_subscription_id, stripe_customer_id, status, created_at)
        SELECT sm.user_id, sm.org_id, 1, sm.stripe_subscription_id, sm.stripe_customer_id, 'active', sm.created_at
        FROM subscription_mapping sm
    """)
    
    # Drop the simplified subscription_mapping table
    op.drop_table('subscription_mapping')