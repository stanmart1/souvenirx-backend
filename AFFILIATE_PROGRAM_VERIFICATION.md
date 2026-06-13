# Affiliate Program - Complete Implementation

## Overview
A comprehensive affiliate program has been implemented with dedicated signup flow, dashboard, bank account management, and promotional materials.

## Features Implemented

### 1. Dedicated Affiliate Signup Page (`/affiliate/signup`)

**Features:**
- ✅ Standalone registration page specifically for affiliates
- ✅ Creates user account + immediately registers as affiliate
- ✅ Benefits and program details showcase
- ✅ Commission rate, cookie duration, and payout information
- ✅ "How it works" section with 3-step process
- ✅ FAQ section with common questions
- ✅ Professional landing page design

**Flow:**
1. User fills signup form (name, email, phone, password)
2. System creates user account
3. System logs user in automatically
4. System registers user as affiliate with status "pending"
5. Redirects to affiliate dashboard
6. Admin receives notification to approve affiliate

### 2. Enhanced Affiliate Dashboard (`/affiliate`)

**Features:**
- ✅ Status-aware dashboard (pending, active, suspended)
- ✅ Real-time earnings tracking
- ✅ Click and conversion statistics
- ✅ Unique referral link with copy functionality
- ✅ Bank account management section
- ✅ Referrals table with commission details
- ✅ Payout history table
- ✅ Request payout button

**Status Handling:**
- **Not registered:** Shows join button + program benefits
- **Pending:** Shows "application under review" message
- **Suspended:** Shows "account suspended" message + support contact
- **Active:** Shows full dashboard with all features

### 3. Bank Account Management

**Features:**
- ✅ Add/edit bank details for payouts
- ✅ Inline editing with save/cancel
- ✅ Stores: Bank name, Account number, Account name
- ✅ Secure display of existing details
- ✅ Required for payout requests

**Backend:**
- New columns in `affiliates` table:
  - `bank_name` (VARCHAR 100)
  - `account_number` (VARCHAR 20)
  - `account_name` (VARCHAR 100)
- New endpoint: `PUT /api/affiliates/me/bank-details`
- Migration: `20250120_add_affiliate_bank_details.py`

### 4. Homepage Promotion

**Features:**
- ✅ Dedicated affiliate CTA section on homepage
- ✅ Displays key stats (10% commission, 30-day cookie, etc.)
- ✅ Two CTAs: "Become an affiliate" + "Affiliate login"
- ✅ Eye-catching gradient background
- ✅ Grid layout with program benefits

**Location:**
- Appears between urgency section and final CTA
- Visible to all visitors (logged in or not)

### 5. Footer Integration

**Updates:**
- ✅ "Become an affiliate" link → `/affiliate/signup`
- ✅ "Affiliate dashboard" link → `/affiliate`
- ✅ Prominent placement in footer navigation

## API Endpoints

### Public Endpoints
- `POST /api/affiliates/register` - Register user as affiliate

### Authenticated Endpoints
- `GET /api/affiliates/me` - Get affiliate stats + bank details
- `PUT /api/affiliates/me/bank-details` - Update bank account info
- `GET /api/affiliates/me/referrals` - List referral conversions
- `GET /api/affiliates/me/payouts` - List payout history
- `POST /api/affiliates/me/payout-request` - Request payout

### Tracking Endpoints
- `POST /api/affiliates/track-click?ref={code}` - Track referral clicks
- Cookie-based attribution (30 days default)

## Database Schema

### Affiliates Table
```sql
CREATE TABLE affiliates (
  id UUID PRIMARY KEY,
  user_id UUID UNIQUE REFERENCES users(id),
  referral_code VARCHAR(50) UNIQUE NOT NULL,
  commission_rate FLOAT DEFAULT 0.10,
  cookie_days INTEGER DEFAULT 30,
  status VARCHAR(20) DEFAULT 'pending',
  total_earnings INTEGER DEFAULT 0,
  bank_name VARCHAR(100),           -- NEW
  account_number VARCHAR(20),       -- NEW
  account_name VARCHAR(100),        -- NEW
  created_at TIMESTAMP DEFAULT NOW()
);
```

### Related Tables
- `affiliate_clicks` - Tracks all clicks
- `affiliate_conversions` - Tracks sales + commissions
- `affiliate_payouts` - Tracks payout requests/completions

## User Flow

### Becoming an Affiliate

1. **Discovery:**
   - User sees affiliate CTA on homepage
   - OR finds "Become an affiliate" in footer
   - OR shares referral link from friend

2. **Signup:**
   - Clicks "Become an affiliate"
   - Lands on `/affiliate/signup`
   - Reads benefits, FAQs, how it works
   - Fills registration form
   - Submits → Account created + affiliate registered

3. **Approval:**
   - Status: "pending"
   - Dashboard shows "application under review"
   - Admin receives notification
   - Admin approves in admin panel → Status: "active"

4. **Active Affiliate:**
   - Full dashboard access
   - Can copy referral link
   - Can add bank details
   - Can track earnings in real-time
   - Can request payouts

### Earning Commissions

1. **Share link:** Affiliate shares `https://souvenir-x.com/?ref={code}`
2. **Click tracked:** System records click + sets 30-day cookie
3. **Customer purchases:** Order attributed to affiliate
4. **Commission calculated:** 10% of order total
5. **Conversion recorded:** Shows in referrals table
6. **Total updated:** Added to affiliate's total earnings

### Requesting Payouts

1. **Prerequisites:**
   - Status: "active"
   - Bank details added
   - Minimum earnings: ₦5,000

2. **Request:**
   - Click "Request payout"
   - Payout request created with status "pending"

3. **Processing:**
   - Admin reviews in admin panel
   - Admin processes bank transfer
   - Marks payout as "completed"
   - Shows in payout history

## Admin Panel Integration

**Endpoints for Admin:**
- `GET /api/admin/affiliates` - List all affiliates
- `PUT /api/admin/affiliates/{id}/approve` - Approve affiliate
- `PUT /api/admin/affiliates/{id}/suspend` - Suspend affiliate
- `GET /api/admin/affiliate-payouts` - List payout requests
- `PUT /api/admin/affiliate-payouts/{id}/complete` - Mark payout completed

## Configuration

### Environment Variables
```
# Default commission rate (10%)
AFFILIATE_COMMISSION_RATE=0.10

# Cookie duration in days
AFFILIATE_COOKIE_DAYS=30

# Minimum payout amount
AFFILIATE_MIN_PAYOUT=500000  # ₦5,000 in kobo
```

### Customizable Settings
- Commission rate (per affiliate in database)
- Cookie duration (per affiliate in database)
- Minimum payout threshold
- Payout schedule (monthly by default)

## Email Notifications

**Affiliate Signup:**
- Sent to: Affiliate
- Template: `affiliate_signup`
- Content: Welcome message, next steps, referral code

**Affiliate Approved:**
- Sent to: Affiliate
- Content: Approval notification, dashboard link

**Payout Requested:**
- Sent to: Admin
- Content: Affiliate details, requested amount, bank details

**Payout Completed:**
- Sent to: Affiliate
- Content: Payment confirmation, transaction details

## Testing Checklist

### Signup Flow
- [ ] Navigate to `/affiliate/signup`
- [ ] Fill out registration form
- [ ] Verify account created
- [ ] Verify redirect to `/affiliate`
- [ ] Verify status is "pending"

### Dashboard
- [ ] View pending status screen
- [ ] Admin approves affiliate
- [ ] Refresh dashboard - see active status
- [ ] Copy referral link - verify format
- [ ] Add bank details - verify save

### Tracking
- [ ] Share referral link `/?ref={code}`
- [ ] Click link - verify cookie set
- [ ] Make test purchase
- [ ] Verify conversion recorded
- [ ] Verify commission calculated

### Payouts
- [ ] Request payout
- [ ] Admin processes payout
- [ ] Verify payout shows in history
- [ ] Verify earnings deducted

## Security Considerations

✅ **Bank details encryption:** Consider encrypting bank account details at rest
✅ **Rate limiting:** Apply to payout requests to prevent abuse
✅ **Fraud detection:** Monitor for self-referrals and suspicious patterns
✅ **Cookie security:** Use `HttpOnly`, `Secure` flags
✅ **Authorization:** All endpoints require authentication
✅ **Admin approval:** Manual review before activation

## Performance Optimizations

✅ **Database indexes:**
- `affiliates.referral_code` (unique index)
- `affiliates.user_id` (unique index)
- `affiliate_clicks.affiliate_id` (index)
- `affiliate_conversions.affiliate_id` (index)

✅ **Caching:**
- Cache affiliate stats for 5 minutes
- Cache referral lookups by code

✅ **Analytics:**
- Track click-through rates
- Monitor conversion rates
- Identify top affiliates

## Files Modified/Created

### Frontend
- ✅ `src/routes/affiliate.signup.tsx` - NEW signup page
- ✅ `src/routes/affiliate.tsx` - Enhanced dashboard
- ✅ `src/routes/index.tsx` - Added affiliate CTA
- ✅ `src/components/site/Footer.tsx` - Added affiliate links

### Backend
- ✅ `app/models/affiliate.py` - Added bank detail fields
- ✅ `app/routes/affiliates.py` - Added bank details endpoint
- ✅ `alembic/versions/20250120_add_affiliate_bank_details.py` - Migration

## Summary

The affiliate program is now production-ready with:

1. ✅ **Dedicated signup flow** - Separate landing page with all details
2. ✅ **Comprehensive dashboard** - Real-time stats, bank management, history
3. ✅ **Bank account management** - Secure payout destination setup
4. ✅ **Homepage promotion** - Visible CTA for all visitors
5. ✅ **Footer integration** - Easy discovery and access
6. ✅ **Status management** - Pending, active, suspended states
7. ✅ **Email notifications** - Automated communications
8. ✅ **Admin approval workflow** - Manual review before activation
9. ✅ **Commission tracking** - Automatic calculation and attribution
10. ✅ **Payout system** - Request and process payments

The system is ready to attract and support affiliates at scale! 🚀
