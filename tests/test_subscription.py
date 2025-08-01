import pytest
from unittest.mock import Mock, patch
from app.models.subscription import SubscriptionMapping, SubscriptionCreate
from app.crud.subscription import get_active_subscription_plans, get_user_subscription_mapping


def test_subscription_mapping_model():
    """Test that subscription mapping model can be created."""
    mapping = SubscriptionMapping(
        user_id="test_user",
        org_id="test_org",
        stripe_customer_id="cus_test_123",
        stripe_subscription_id="sub_test_123"
    )
    assert mapping.user_id == "test_user"
    assert mapping.org_id == "test_org"
    assert mapping.stripe_customer_id == "cus_test_123"
    assert mapping.stripe_subscription_id == "sub_test_123"


def test_subscription_create_schema():
    """Test subscription creation schema."""
    subscription_data = SubscriptionCreate(
        user_id="test_user",
        org_id="test_org", 
        stripe_price_id="price_test_123"
    )
    assert subscription_data.user_id == "test_user"
    assert subscription_data.org_id == "test_org"
    assert subscription_data.stripe_price_id == "price_test_123"


@patch('app.crud.subscription.stripe')
def test_get_active_subscription_plans(mock_stripe):
    """Test getting subscription plans from Stripe."""
    # Mock Stripe products response
    mock_product = Mock()
    mock_product.id = "prod_test_123"
    mock_product.name = "Test Plan"
    mock_product.description = "Test Description"
    mock_product.metadata = {
        'is_subscription_plan': 'true',
        'free_quota': '20'
    }
    
    mock_price = Mock()
    mock_price.id = "price_test_123"
    mock_price.billing_scheme = "tiered"
    mock_price.usage_type = "metered"
    mock_price.tiers = [
        {"up_to": 20, "unit_amount_decimal": "0"},
        {"up_to": "inf", "unit_amount_decimal": "500"}
    ]
    
    mock_stripe.Product.list.return_value.data = [mock_product]
    mock_stripe.Price.list.return_value.data = [mock_price]
    
    plans = get_active_subscription_plans()
    
    assert len(plans) == 1
    assert plans[0]['product_name'] == "Test Plan"
    assert plans[0]['price_id'] == "price_test_123"
    assert plans[0]['free_quota'] == 20


@patch('app.crud.subscription.stripe')
def test_report_usage_to_stripe(mock_stripe):
    """Test usage reporting to Stripe."""
    from app.crud.subscription import report_usage_to_stripe
    
    # Mock Stripe subscription response
    mock_subscription_item = Mock()
    mock_subscription_item.id = "si_test_123"
    
    mock_stripe_subscription = Mock()
    mock_stripe_subscription.items.data = [mock_subscription_item]
    
    mock_stripe.Subscription.retrieve.return_value = mock_stripe_subscription
    mock_stripe.UsageRecord.create.return_value = Mock()
    
    # Create test subscription mapping
    mapping = SubscriptionMapping(
        user_id="test_user",
        org_id="test_org",
        stripe_customer_id="cus_test_123",
        stripe_subscription_id="sub_test_123"
    )
    
    # Test usage reporting
    result = report_usage_to_stripe(mapping, 5)
    
    assert result is True
    mock_stripe.Subscription.retrieve.assert_called_once_with("sub_test_123")
    mock_stripe.UsageRecord.create.assert_called_once()


@patch('app.crud.subscription.stripe')
def test_get_current_usage_from_stripe(mock_stripe):
    """Test getting current usage from Stripe."""
    from app.crud.subscription import get_current_usage_from_stripe
    
    # Mock Stripe responses
    mock_subscription_item = Mock()
    mock_subscription_item.id = "si_test_123"
    
    mock_product = Mock()
    mock_product.metadata = {'free_quota': '20'}
    
    mock_price = Mock()
    mock_price.product = mock_product
    
    mock_subscription_item.price = mock_price
    
    mock_stripe_subscription = Mock()
    mock_stripe_subscription.items.data = [mock_subscription_item]
    mock_stripe_subscription.current_period_start = 1640995200  # Jan 1, 2022
    mock_stripe_subscription.current_period_end = 1643673600   # Feb 1, 2022
    
    mock_usage_summary = Mock()
    mock_usage_summary.total_usage = 15
    
    mock_stripe.Subscription.retrieve.return_value = mock_stripe_subscription
    mock_stripe.UsageRecordSummary.list.return_value.data = [mock_usage_summary]
    
    # Create test subscription mapping
    mapping = SubscriptionMapping(
        user_id="test_user",
        org_id="test_org",
        stripe_customer_id="cus_test_123",
        stripe_subscription_id="sub_test_123"
    )
    
    # Test usage retrieval
    result = get_current_usage_from_stripe(mapping)
    
    assert result is not None
    assert result['usage_count'] == 15
    assert result['free_quota'] == 20
    mock_stripe.Subscription.retrieve.assert_called_once_with("sub_test_123")
    mock_stripe.UsageRecordSummary.list.assert_called_once()


def test_get_user_subscription_mapping(mock_db_session):
    """Test getting user subscription mapping."""
    # Mock database response
    mock_mapping = SubscriptionMapping(
        id=1,
        user_id="test_user",
        org_id="test_org",
        stripe_customer_id="cus_test_123",
        stripe_subscription_id="sub_test_123"
    )
    
    mock_db_session.exec.return_value.first.return_value = mock_mapping
    
    result = get_user_subscription_mapping(mock_db_session, "test_user", "test_org")
    
    assert result is not None
    assert result.user_id == "test_user"
    assert result.org_id == "test_org"
    assert result.stripe_customer_id == "cus_test_123"