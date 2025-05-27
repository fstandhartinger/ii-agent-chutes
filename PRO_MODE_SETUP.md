# Pro Mode Implementation

This document describes the Pro mode feature that provides access to Claude Sonnet 4 for premium users.

## Overview

The Pro mode is implemented using a simple prime number-based validation system for Pro keys. Users who purchase a $20/month subscription get access to Claude Sonnet 4 with usage tracking.

## Features

### 1. Pro Upgrade Button
- Displayed in the top-right corner for non-Pro users
- Attractive gradient design with crown and sparkles icons
- Redirects to the Pro upgrade page

### 2. Pro Upgrade Page (`/pro-upgrade`)
- Beautiful landing page explaining Sonnet 4 benefits
- $20/month pricing
- Direct link to Stripe payment page
- Responsive design with animations

### 3. Model Access Control
- Claude Sonnet 4 is visible in the model dropdown for all users
- Non-Pro users are redirected to upgrade page when selecting Sonnet 4
- Pro users can use Sonnet 4 normally

### 4. Usage Tracking
- Tracks Sonnet 4 requests per Pro key per month
- 1000 request limit per month (configurable)
- Automatic blocking when limit is exceeded
- Database storage of usage statistics

### 5. Pro Key Validation
- 8-character hexadecimal keys
- Based on large prime number (982451)
- Valid keys are multiples of the prime when converted to decimal
- URL parameter: `?pro_user_key=XXXXXXXX`

## Technical Implementation

### Frontend Components

1. **ProUpgradeButton** (`frontend/components/pro-upgrade-button.tsx`)
   - Animated upgrade button with gradient styling

2. **Pro Upgrade Page** (`frontend/app/pro-upgrade/page.tsx`)
   - Full-featured landing page with benefits and pricing

3. **Pro Utils** (`frontend/utils/pro-utils.ts`)
   - Client-side validation and key checking functions

4. **Modified Model Picker** (`frontend/components/model-picker.tsx`)
   - Redirects to upgrade page for non-Pro users selecting Sonnet 4

### Backend Components

1. **Pro Utils** (`src/ii_agent/utils/pro_utils.py`)
   - Key generation and validation functions
   - Prime number-based validation logic

2. **Database Models** (`src/ii_agent/db/models.py`)
   - `ProUsage` table for tracking monthly usage

3. **Database Manager** (`src/ii_agent/db/manager.py`)
   - `track_pro_usage()` and `get_pro_usage()` methods

4. **WebSocket Server** (`ws_server.py`)
   - Pro key extraction from query parameters
   - Access control for Sonnet 4 model
   - Usage tracking integration

5. **Agent Integration** (`src/ii_agent/agents/anthropic_fc.py`)
   - Usage tracking before each Sonnet 4 request
   - Automatic blocking when limit exceeded

### API Endpoints

- `POST /api/pro/generate-key` - Generate new Pro key (testing)
- `GET /api/pro/usage/{pro_key}` - Get usage statistics

## Usage

### For Testing

1. Generate a Pro key:
   ```bash
   python generate_pro_key.py
   ```

2. Use the generated URL to access Pro features

3. Or use the API endpoint:
   ```bash
   curl -X POST http://localhost:8000/api/pro/generate-key
   ```

### For Production

1. User purchases subscription via Stripe link
2. Admin generates Pro key using the script
3. Admin sends Pro key URL to user via email
4. User accesses the application with Pro key in URL

## Configuration

### Prime Number
The validation prime is set to `982451` in both frontend and backend utils. This can be changed if needed, but both sides must use the same value.

### Usage Limits
Monthly limit is set to 1000 requests in `DatabaseManager.track_pro_usage()`. This can be adjusted as needed.

### Stripe Integration
The Stripe payment link is configured in:
- `frontend/app/pro-upgrade/page.tsx` (STRIPE_PAYMENT_LINK constant)

## Database Schema

### ProUsage Table
```sql
CREATE TABLE pro_usage (
    id TEXT PRIMARY KEY,
    pro_key TEXT NOT NULL,
    month_year TEXT NOT NULL,
    sonnet_requests INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_pro_usage_key_month ON pro_usage(pro_key, month_year);
```

## Security Considerations

1. **Key Validation**: Uses mathematical validation (prime multiples) rather than database lookups
2. **Usage Tracking**: Prevents abuse through monthly request limits
3. **No Sensitive Data**: Pro keys don't contain personal information
4. **Simple Revocation**: Keys can be invalidated by changing the prime number

## Future Enhancements

1. **Stripe Webhooks**: Automatic Pro key generation on payment
2. **User Management**: Proper user accounts and login system
3. **Multiple Plans**: Different tiers with different limits
4. **Usage Analytics**: Detailed usage reporting and analytics
5. **Key Management**: Admin interface for key generation and management

## Stripe Payment Flow

Currently, the payment flow is manual:

1. User clicks "Subscribe Now" button
2. Redirected to Stripe payment page
3. User completes payment
4. Stripe sends confirmation email to admin
5. Admin manually generates Pro key and sends to user

For production, this should be automated with Stripe webhooks. 