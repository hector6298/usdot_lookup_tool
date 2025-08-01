# Subscription System Documentation

## Overview

The USDOT Lookup Tool now includes a comprehensive subscription system using Stripe's native metered billing. This approach eliminates the need for custom quota tracking infrastructure by leveraging Stripe's proven billing capabilities.

## Subscription Tiers

All tiers use Stripe's metered billing with quantity transformation for tiered pricing:

### Free Tier
- **Free quota**: 20 operations per month
- **Overage**: No additional charges
- **Features**: Image OCR, manual USDOT input, Salesforce sync

### Basic Tier  
- **Free quota**: 20 operations per month
- **Overage**: Charged per operation beyond free quota
- **Features**: Image OCR, manual USDOT input, Salesforce sync

### Professional Tier
- **Free quota**: 20 operations per month
- **Overage**: Lower per-operation cost than Basic tier
- **Features**: Image OCR, manual USDOT input, Salesforce sync

### Enterprise Tier
- **Free quota**: 20 operations per month
- **Overage**: Lowest per-operation cost with volume discounts
- **Features**: Image OCR, manual USDOT input, Salesforce sync

## Key Features

### Stripe Metered Billing
- Automatic usage reporting to Stripe after each operation
- Real-time usage tracking via Stripe's infrastructure
- Quantity transformation for tiered pricing structures
- Automatic billing based on actual usage

### Simplified Architecture
- No custom quota tracking tables
- Stripe handles all billing calculations
- Reduced maintenance overhead
- Proven billing infrastructure

### Access Control
- No pre-validation of quotas (users can always perform operations)
- Usage reported to Stripe after successful operations
- Billing occurs automatically based on usage
- Clear usage information available from Stripe

## Technical Implementation

### Database Schema

#### SubscriptionPlan
- `id`: Primary key
- `name`: Plan name (Free, Basic, Professional, Enterprise)
- `stripe_price_id`: Stripe price ID for metered billing (required)
- `free_quota`: Free operations included per month
- `is_active`: Whether plan is available
- `created_at`: Creation timestamp

#### Subscription
- `id`: Primary key
- `user_id`: Foreign key to AppUser
- `org_id`: Foreign key to AppOrg
- `plan_id`: Foreign key to SubscriptionPlan
- `stripe_subscription_id`: Stripe subscription ID (required)
- `stripe_customer_id`: Stripe customer ID (required)
- `status`: active, inactive, cancelled, past_due, unpaid
- `created_at/updated_at`: Timestamps

### Stripe Integration

#### Metered Billing Setup
1. **Create Stripe Products**: One for each tier (Free, Basic, Professional, Enterprise)
2. **Create Stripe Prices**: Configure each with metered billing and quantity transformation
3. **Quantity Transformation**: Set up tiered pricing (e.g., first 20 free, then charge per operation)
4. **Usage Reporting**: Operations are reported to Stripe after successful completion

#### Price Configuration Example
```json
{
  "currency": "usd",
  "billing_scheme": "tiered",
  "tiers_mode": "graduated",
  "tiers": [
    {
      "up_to": 20,
      "unit_amount_decimal": "0"
    },
    {
      "up_to": "inf",
      "unit_amount_decimal": "500"
    }
  ],
  "usage_type": "metered"
}
```

### API Endpoints

#### Billing Management
- `GET /billing/`: Subscription management page
- `GET /billing/plans`: List available subscription plans
- `GET /billing/subscription`: Get current user subscription
- `GET /billing/usage`: Get current usage from Stripe
- `POST /billing/subscribe/{plan_id}`: Subscribe to a plan
- `POST /billing/cancel-subscription`: Cancel subscription

#### Webhooks
- `POST /webhooks/stripe`: Handle Stripe webhook events
  - `invoice.payment_succeeded`: Subscription billing events
  - `customer.subscription.updated`: Subscription changes
  - `customer.subscription.deleted`: Subscription cancellation

### Integration Points

#### Upload Route Modifications
The `/upload` endpoint now:
1. **Subscription Check**: Verifies user has active subscription
2. **Usage Reporting**: Reports usage to Stripe after successful operations
3. **Error Handling**: Returns structured error responses for subscription issues
4. **Usage Information**: Includes current usage data from Stripe in response

#### User Registration
- New users must subscribe to a plan (including free) to use the service
- Free plan provides 20 operations per month at no cost
- Usage beyond free quota is automatically billed via Stripe

#### Stripe Integration
- Metered billing with automatic usage reporting
- Customer and subscription management
- Webhook event processing for billing lifecycle
- Real-time usage tracking via Stripe APIs

## Configuration

### Environment Variables
```bash
# Stripe Configuration (Sandbox)
STRIPE_SB_PK=pk_test_your_public_key
STRIPE_SB_SK=sk_test_your_secret_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
```

### Database Migration
Run the subscription tables migration:
```bash
alembic upgrade head
```

### Database Migration
Run the updated subscription migration:
```bash
alembic upgrade head
```

The migration:
- Removes custom quota tracking tables (UsageQuota, OneTimePayment)
- Updates SubscriptionPlan for metered billing with Stripe price IDs
- Updates Subscription to require Stripe IDs
- Eliminates custom billing infrastructure

## Usage Examples

### Getting Current Usage from Stripe
```python
from app.crud.subscription import get_current_usage_from_stripe

subscription = get_user_subscription(db, user_id, org_id)
usage_data = get_current_usage_from_stripe(subscription)
if usage_data:
    current_usage = usage_data['usage_count']
    free_quota = usage_data['plan_free_quota']
```

### Reporting Usage to Stripe
```python
from app.crud.subscription import report_usage_to_stripe

subscription = get_user_subscription(db, user_id, org_id)
success = report_usage_to_stripe(subscription, operations_count=5)
if success:
    # Usage successfully reported to Stripe
    logger.info("Usage reported to Stripe")
```

### Creating Subscription with Stripe
```python
from app.crud.subscription import create_subscription
from app.models.subscription import SubscriptionCreate

# Create Stripe subscription first
stripe_subscription = stripe.Subscription.create(
    customer=customer_id,
    items=[{'price': plan.stripe_price_id}]
)

# Then create in our database
subscription_data = SubscriptionCreate(
    user_id="user_123",
    org_id="org_456", 
    plan_id=2  # Basic plan
)
subscription = create_subscription(
    db, subscription_data, 
    stripe_subscription.id, 
    customer_id
)
```

## Error Handling

### No Subscription Response
```json
{
  "error": "quota_exceeded",
  "message": "Insufficient quota. You need 5 operations but only have 2 remaining.",
  "quota_remaining": 2,
  "quota_needed": 5
}
```

```json
{
  "error": "no_subscription", 
  "message": "No active subscription found. Please subscribe to a plan to continue.",
  "operations_needed": 3
}
```

## Frontend Integration

The subscription management page (`/billing/`) provides:
- Current usage visualization from Stripe data
- Available plans with metered pricing information
- One-click subscription management
- Real-time usage updates from Stripe
- Simplified billing without quota management complexity

## Security Considerations

1. **Webhook Verification**: All Stripe webhooks are verified using signature validation
2. **User Isolation**: Subscriptions are scoped to user_id and org_id
3. **Payment Security**: All payment processing handled by Stripe
4. **Data Protection**: Sensitive payment data never stored locally
5. **Metered Billing**: Usage reported securely to Stripe's infrastructure
6. **Access Control**: Subscription status checked on operations

## Benefits of Stripe Metered Billing

1. **Reduced Infrastructure**: No custom quota tracking, carryover logic, or payment handling
2. **Proven Reliability**: Leverage Stripe's battle-tested billing infrastructure
3. **Automatic Scaling**: Stripe handles high-volume usage tracking and billing
4. **Simplified Code**: Less custom logic means fewer bugs and easier maintenance
5. **Better UX**: No pre-validation means users can always perform operations
6. **Accurate Billing**: Real usage-based billing instead of pre-paid quotas

## Monitoring and Analytics

### Key Metrics to Track
- Monthly Active Users by subscription tier
- Average quota utilization per tier
- Conversion rates from free to paid tiers
- One-time payment frequency and amounts
- Churn rates and cancellation reasons

### Logging
All subscription operations are logged with appropriate levels:
- INFO: Successful operations and state changes
- WARNING: Quota warnings and edge cases  
- ERROR: Payment failures and system errors

## Troubleshooting

### Common Issues

1. **User has no subscription**: 
   - Check if free subscription was created during registration
   - Manually create subscription if needed

2. **Quota not updating**:
   - Verify database transactions are committing
   - Check for concurrent access issues

3. **Stripe webhook failures**:
   - Verify webhook endpoint is accessible
   - Check webhook secret configuration
   - Review Stripe dashboard for event details

4. **Payment processing errors**:
   - Validate Stripe API keys
   - Check customer and payment method setup
   - Review Stripe logs for detailed error messages

## Future Enhancements

1. **Analytics Dashboard**: Usage analytics and subscription metrics
2. **Enterprise Features**: Custom quotas, volume discounts, dedicated support
3. **API Access**: REST API quotas for enterprise customers
4. **Team Management**: Multi-user organization subscriptions
5. **Usage Alerts**: Email notifications for quota thresholds
6. **Annual Billing**: Discounted annual subscription options