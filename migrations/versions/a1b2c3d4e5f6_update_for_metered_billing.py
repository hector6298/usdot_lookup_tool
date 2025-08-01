"""Update subscription system for Stripe metered billing

Revision ID: update_for_metered_billing
Revises: f8a5b7c6d9e0
Create Date: 2025-01-01 18:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f8a5b7c6d9e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema for metered billing."""
    
    # Drop tables that are no longer needed with Stripe metered billing
    op.drop_table('onetimepayment')
    op.drop_table('usagequota')
    
    # Update SubscriptionPlan table for metered billing
    op.drop_column('subscriptionplan', 'price_cents')
    op.drop_column('subscriptionplan', 'monthly_quota')
    op.alter_column('subscriptionplan', 'stripe_price_id',
                   existing_type=sa.String(length=255),
                   nullable=False)
    op.add_column('subscriptionplan', sa.Column('free_quota', sa.Integer(), nullable=False, server_default='0'))
    
    # Update Subscription table for metered billing
    op.drop_column('subscription', 'current_period_start')
    op.drop_column('subscription', 'current_period_end')
    op.alter_column('subscription', 'stripe_subscription_id',
                   existing_type=sa.String(length=255),
                   nullable=False)
    op.add_column('subscription', sa.Column('stripe_customer_id', sa.String(length=255), nullable=False, server_default=''))
    
    # Update default plans with Stripe price IDs for metered billing
    # Note: These price IDs should be created in Stripe dashboard
    op.execute("""
        UPDATE subscriptionplan SET 
            stripe_price_id = 'price_free_tier',
            free_quota = 20
        WHERE name = 'Free'
    """)
    
    op.execute("""
        UPDATE subscriptionplan SET 
            stripe_price_id = 'price_basic_tier',
            free_quota = 20
        WHERE name = 'Basic'
    """)
    
    op.execute("""
        UPDATE subscriptionplan SET 
            stripe_price_id = 'price_professional_tier',
            free_quota = 20
        WHERE name = 'Professional'
    """)
    
    op.execute("""
        UPDATE subscriptionplan SET 
            stripe_price_id = 'price_enterprise_tier',
            free_quota = 20
        WHERE name = 'Enterprise'
    """)


def downgrade() -> None:
    """Downgrade schema back to original subscription system."""
    
    # Add back columns to SubscriptionPlan
    op.add_column('subscriptionplan', sa.Column('price_cents', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('subscriptionplan', sa.Column('monthly_quota', sa.Integer(), nullable=False, server_default='0'))
    op.drop_column('subscriptionplan', 'free_quota')
    op.alter_column('subscriptionplan', 'stripe_price_id',
                   existing_type=sa.String(length=255),
                   nullable=True)
    
    # Add back columns to Subscription
    op.add_column('subscription', sa.Column('current_period_start', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')))
    op.add_column('subscription', sa.Column('current_period_end', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')))
    op.drop_column('subscription', 'stripe_customer_id')
    op.alter_column('subscription', 'stripe_subscription_id',
                   existing_type=sa.String(length=255),
                   nullable=True)
    
    # Recreate UsageQuota table
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
    
    # Recreate OneTimePayment table
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
    
    # Restore original plan data
    op.execute("""
        UPDATE subscriptionplan SET 
            price_cents = 0,
            monthly_quota = 20
        WHERE name = 'Free'
    """)
    
    op.execute("""
        UPDATE subscriptionplan SET 
            price_cents = 999,
            monthly_quota = 150
        WHERE name = 'Basic'
    """)
    
    op.execute("""
        UPDATE subscriptionplan SET 
            price_cents = 2999,
            monthly_quota = 500
        WHERE name = 'Professional'
    """)
    
    op.execute("""
        UPDATE subscriptionplan SET 
            price_cents = 9999,
            monthly_quota = 2000
        WHERE name = 'Enterprise'
    """)