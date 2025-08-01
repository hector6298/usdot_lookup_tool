# Simplified Subscription System Documentation

## Overview

The subscription system has been significantly simplified to leverage Stripe's native infrastructure instead of maintaining complex custom billing logic locally.

## Architecture Changes

### Before (Complex Local System)
```
Local Database Tables:
├── SubscriptionPlan (plans, pricing, quotas)
├── Subscription (user subscriptions, status)
├── UsageQuota (quota tracking, carryovers)
└── OneTimePayment (one-time purchases)

Custom Logic:
├── Quota pre-validation
├── Usage tracking
├── Carryover calculations
├── Payment processing
└── Status management
```

### After (Stripe-Native System)
```
Local Database:
└── SubscriptionMapping (user_id/org_id → Stripe IDs)

Stripe Infrastructure:
├── Products (plan metadata)
├── Prices (metered billing tiers)
├── Subscriptions (status, billing)
├── Customers (user mapping)
└── Usage Records (automatic tracking)
```

## Key Benefits

1. **Reduced Maintenance**: ~500 lines of custom billing code eliminated
2. **Proven Reliability**: Stripe handles all edge cases and billing logic
3. **Better UX**: No quota pre-validation, users can always operate
4. **Accurate Billing**: True usage-based billing vs pre-paid quotas
5. **Simplified Testing**: Less custom logic means fewer bugs

## Data Flow

### Subscription Creation
```
1. User selects plan → POST /billing/subscribe/{price_id}
2. Create/get Stripe Customer
3. Create Stripe Subscription with metered price
4. Store mapping in SubscriptionMapping table
```

### Usage Tracking
```
1. User uploads files → POST /upload
2. Process files successfully 
3. Report usage to Stripe → stripe.UsageRecord.create()
4. Stripe handles billing automatically
```

### Usage Retrieval
```
1. User checks usage → GET /billing/usage
2. Fetch from Stripe → stripe.UsageRecordSummary.list()
3. Get free quota from Product metadata
4. Return real-time usage data
```

## Stripe Configuration

### Products Setup
Products should be created in Stripe Dashboard with:
```json
{
  "name": "Basic Plan",
  "metadata": {
    "is_subscription_plan": "true",
    "free_quota": "20"
  }
}
```

### Prices Setup  
Prices should use metered billing with quantity transformation:
```json
{
  "usage_type": "metered",
  "billing_scheme": "tiered", 
  "tiers": [
    {"up_to": 20, "unit_amount_decimal": "0"},
    {"up_to": "inf", "unit_amount_decimal": "500"}
  ]
}
```

## API Changes

### Endpoints Updated
- `GET /billing/plans` - Now fetches from Stripe Products
- `POST /billing/subscribe/{price_id}` - Uses Stripe price ID instead of local plan ID
- `GET /billing/subscription` - Returns Stripe subscription data
- `GET /billing/usage` - Real-time usage from Stripe

### Webhooks Simplified
- `invoice.payment_succeeded` - Logging only (Stripe handles billing)
- `customer.subscription.updated` - Status logging
- `customer.subscription.deleted` - Cleanup mapping

## Database Migration

The migration `b1c2d3e4f5g6_simplify_subscription_system.py`:
1. Creates new `subscription_mapping` table
2. Migrates active subscriptions with valid Stripe IDs
3. Drops old `subscription` and `subscriptionplan` tables

## Testing

Updated tests focus on:
- Stripe API integration mocking
- Subscription mapping CRUD operations
- Usage reporting and retrieval
- Plan fetching from Stripe Products

## Legacy Compatibility

Temporary compatibility functions maintain existing interfaces:
- `get_user_subscription()` → `get_user_subscription_mapping()`
- `get_subscription_plans()` → `get_active_subscription_plans()`

These can be removed once all code is updated to use the new functions directly.