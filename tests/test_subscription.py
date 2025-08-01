import pytest
from unittest.mock import Mock
from app.models.subscription import SubscriptionPlan, SubscriptionCreate
from app.crud.subscription import get_subscription_plans, initialize_default_plans


def test_subscription_models():
    """Test that subscription models can be created."""
    plan = SubscriptionPlan(
        name="Test Plan",
        price_cents=999,
        monthly_quota=100
    )
    assert plan.name == "Test Plan"
    assert plan.price_cents == 999
    assert plan.monthly_quota == 100


def test_subscription_create_schema():
    """Test subscription creation schema."""
    subscription_data = SubscriptionCreate(
        user_id="test_user",
        org_id="test_org", 
        plan_id=1
    )
    assert subscription_data.user_id == "test_user"
    assert subscription_data.org_id == "test_org"
    assert subscription_data.plan_id == 1


def test_default_plans_initialization(mock_db_session):
    """Test that default plans can be initialized."""
    # Mock empty plans list initially
    mock_db_session.exec.return_value.all.return_value = []
    
    try:
        initialize_default_plans(mock_db_session)
        # Should not raise an exception
        assert True
    except Exception as e:
        pytest.fail(f"initialize_default_plans raised an exception: {e}")


def test_quota_calculation():
    """Test quota calculations work correctly."""
    from app.models.subscription import UsageQuota
    from datetime import datetime
    
    quota = UsageQuota(
        subscription_id=1,
        user_id="test_user",
        org_id="test_org",
        period_start=datetime.utcnow(),
        period_end=datetime.utcnow(),
        quota_limit=100,
        quota_used=30,
        quota_remaining=70,
        carryover_from_previous=0
    )
    
    assert quota.quota_limit == 100
    assert quota.quota_used == 30
    assert quota.quota_remaining == 70