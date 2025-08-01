# Subscription System Documentation

## Overview

The USDOT Lookup Tool now includes a comprehensive subscription system with usage-based quotas and Stripe payment integration. Users can subscribe to different tiers and purchase additional operations as needed.

## Subscription Tiers

### Free Tier
- **Price**: $0/month
- **Quota**: 20 operations per month
- **Features**: Image OCR, manual USDOT input, Salesforce sync

### Basic Tier  
- **Price**: $9.99/month
- **Quota**: 150 operations per month
- **Features**: Image OCR, manual USDOT input, Salesforce sync

### Professional Tier
- **Price**: $29.99/month  
- **Quota**: 500 operations per month
- **Features**: Image OCR, manual USDOT input, Salesforce sync

### Enterprise Tier
- **Price**: $99.99/month
- **Quota**: 2000 operations per month
- **Features**: Image OCR, manual USDOT input, Salesforce sync

## Key Features

### Quota Management
- Monthly quota tracking with real-time usage monitoring
- Unused quota carries over to next month (e.g., 10 remaining + 150 new = 160 total)
- Quota validation before processing operations
- Graceful degradation when quota is exhausted

### One-Time Payments
- Purchase additional operations at $0.10 per operation
- Instant quota replenishment
- No subscription required for one-time purchases

### Access Control
- Upload operations blocked when quota exceeded
- Dashboard and existing data remain accessible
- Existing carrier sync operations continue to work
- Clear error messages with upgrade prompts

## Technical Implementation

### Database Schema

#### SubscriptionPlan
- `id`: Primary key
- `name`: Plan name (Free, Basic, Professional, Enterprise)
- `price_cents`: Price in cents (999 = $9.99)
- `monthly_quota`: Operations allowed per month
- `stripe_price_id`: Stripe price ID for billing
- `is_active`: Whether plan is available
- `created_at`: Creation timestamp

#### Subscription
- `id`: Primary key
- `user_id`: Foreign key to AppUser
- `org_id`: Foreign key to AppOrg
- `plan_id`: Foreign key to SubscriptionPlan
- `stripe_subscription_id`: Stripe subscription ID
- `status`: active, inactive, cancelled, past_due, unpaid
- `current_period_start/end`: Billing period dates
- `created_at/updated_at`: Timestamps

#### UsageQuota
- `id`: Primary key
- `subscription_id`: Foreign key to Subscription
- `user_id/org_id`: User and organization references
- `period_start/end`: Quota period dates
- `quota_limit`: Total quota for period
- `quota_used`: Operations consumed
- `quota_remaining`: Operations available
- `carryover_from_previous`: Unused quota from last period
- `created_at/updated_at`: Timestamps

#### OneTimePayment
- `id`: Primary key
- `user_id/org_id`: User and organization references
- `stripe_payment_intent_id`: Stripe payment intent ID
- `amount_cents`: Payment amount in cents
- `quota_purchased`: Additional operations purchased
- `description`: Payment description
- `created_at`: Payment timestamp

### API Endpoints

#### Billing Management
- `GET /billing/`: Subscription management page
- `GET /billing/plans`: List available subscription plans
- `GET /billing/subscription`: Get current user subscription
- `GET /billing/usage`: Get current usage quota
- `POST /billing/subscribe/{plan_id}`: Subscribe to a plan
- `POST /billing/purchase-quota`: Purchase additional quota
- `GET /billing/invoices`: Get user invoices
- `POST /billing/cancel-subscription`: Cancel subscription

#### Webhooks
- `POST /webhooks/stripe`: Handle Stripe webhook events
  - `payment_intent.succeeded`: One-time payment completion
  - `invoice.payment_succeeded`: Subscription renewal
  - `customer.subscription.updated`: Subscription changes
  - `customer.subscription.deleted`: Subscription cancellation

### Integration Points

#### Upload Route Modifications
The `/upload` endpoint now includes:
1. **Quota Validation**: Checks available quota before processing
2. **Usage Tracking**: Decrements quota after successful operations
3. **Error Handling**: Returns structured error responses for quota issues
4. **Quota Information**: Includes quota status in response

#### User Registration
- New users automatically receive a free subscription
- Free subscription includes 20 operations per month
- Immediate access to basic functionality

#### Stripe Integration
- Sandbox mode using `STRIPE_SB_PK` and `STRIPE_SB_SK` environment variables
- Customer creation and management
- Subscription lifecycle handling
- Webhook event processing
- Payment intent creation for one-time purchases

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

The migration creates:
- Subscription tables with proper foreign key relationships
- Default subscription plans (Free, Basic, Professional, Enterprise)
- Indexes for efficient quota lookups

## Usage Examples

### Checking User Quota
```python
from app.crud.subscription import get_current_usage_quota

quota = get_current_usage_quota(db, user_id, org_id)
if quota and quota.quota_remaining > 0:
    # User has available quota
    operations_available = quota.quota_remaining
else:
    # User needs to upgrade or purchase quota
```

### Using Quota
```python
from app.crud.subscription import use_quota

success = use_quota(db, user_id, org_id, amount=5)
if success:
    # Quota was successfully used
    proceed_with_operations()
else:
    # Insufficient quota
    return_quota_error()
```

### Creating Subscription
```python
from app.crud.subscription import create_subscription
from app.models.subscription import SubscriptionCreate

subscription_data = SubscriptionCreate(
    user_id="user_123",
    org_id="org_456", 
    plan_id=2  # Basic plan
)
subscription = create_subscription(db, subscription_data)
```

## Error Handling

### Quota Exceeded Response
```json
{
  "error": "quota_exceeded",
  "message": "Insufficient quota. You need 5 operations but only have 2 remaining.",
  "quota_remaining": 2,
  "quota_needed": 5
}
```

### No Subscription Response  
```json
{
  "error": "no_subscription", 
  "message": "No active subscription found. Please subscribe to a plan to continue.",
  "quota_needed": 3
}
```

## Frontend Integration

The subscription management page (`/billing/`) provides:
- Current usage visualization with progress bars
- Available plans with pricing and features
- One-click subscription management
- Additional quota purchase with Stripe integration
- Real-time quota updates after operations

## Security Considerations

1. **Webhook Verification**: All Stripe webhooks are verified using signature validation
2. **User Isolation**: Quota tracking is scoped to user_id and org_id
3. **Payment Security**: All payment processing handled by Stripe
4. **Data Protection**: Sensitive payment data never stored locally
5. **Access Control**: Subscription status checked on every protected operation

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