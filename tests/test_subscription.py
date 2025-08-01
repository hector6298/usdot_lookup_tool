import pytest
from unittest.mock import Mock, patch
from app.models.subscription import SubscriptionPlan, SubscriptionCreate
from app.crud.subscription import get_subscription_plans, initialize_default_plans


def test_subscription_models():
    """Test that subscription models can be created."""
    plan = SubscriptionPlan(
        name="Test Plan",
        stripe_price_id="price_test_123",
        free_quota=20
    )
    assert plan.name == "Test Plan"
    assert plan.stripe_price_id == "price_test_123"
    assert plan.free_quota == 20


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


@patch('app.crud.subscription.stripe')
def test_report_usage_to_stripe(mock_stripe):
    """Test usage reporting to Stripe."""
    from app.crud.subscription import report_usage_to_stripe
    from app.models.subscription import Subscription
    
    # Mock Stripe subscription response
    mock_subscription_item = Mock()
    mock_subscription_item.id = "si_test_123"
    
    mock_stripe_subscription = Mock()
    mock_stripe_subscription.items.data = [mock_subscription_item]
    
    mock_stripe.Subscription.retrieve.return_value = mock_stripe_subscription
    mock_stripe.UsageRecord.create.return_value = Mock()
    
    # Create test subscription
    subscription = Subscription(
        user_id="test_user",
        org_id="test_org",
        plan_id=1,
        stripe_subscription_id="sub_test_123",
        stripe_customer_id="cus_test_123"
    )
    
    # Test usage reporting
    result = report_usage_to_stripe(subscription, 5)
    
    assert result is True
    mock_stripe.Subscription.retrieve.assert_called_once_with("sub_test_123")
    mock_stripe.UsageRecord.create.assert_called_once()


@patch('app.crud.subscription.stripe')
def test_get_current_usage_from_stripe(mock_stripe):
    """Test getting current usage from Stripe."""
    from app.crud.subscription import get_current_usage_from_stripe
    from app.models.subscription import Subscription, SubscriptionPlan
    
    # Mock Stripe responses
    mock_subscription_item = Mock()
    mock_subscription_item.id = "si_test_123"
    
    mock_stripe_subscription = Mock()
    mock_stripe_subscription.items.data = [mock_subscription_item]
    mock_stripe_subscription.current_period_start = 1640995200  # Jan 1, 2022
    mock_stripe_subscription.current_period_end = 1643673600   # Feb 1, 2022
    
    mock_usage_summary = Mock()
    mock_usage_summary.total_usage = 15
    
    mock_stripe.Subscription.retrieve.return_value = mock_stripe_subscription
    mock_stripe.UsageRecordSummary.list.return_value.data = [mock_usage_summary]
    
    # Create test subscription with plan
    plan = SubscriptionPlan(
        id=1,
        name="Test Plan",
        stripe_price_id="price_test_123",
        free_quota=20
    )
    
    subscription = Subscription(
        user_id="test_user",
        org_id="test_org",
        plan_id=1,
        stripe_subscription_id="sub_test_123",
        stripe_customer_id="cus_test_123"
    )
    subscription.plan = plan
    
    # Test usage retrieval
    result = get_current_usage_from_stripe(subscription)
    
    assert result is not None
    assert result['usage_count'] == 15
    assert result['plan_free_quota'] == 20
    mock_stripe.Subscription.retrieve.assert_called_once_with("sub_test_123")
    mock_stripe.UsageRecordSummary.list.assert_called_once()