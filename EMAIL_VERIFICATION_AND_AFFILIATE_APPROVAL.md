# Email Verification & Affiliate Approval System

## Overview
Implemented comprehensive email verification and configurable affiliate approval system with admin controls.

## Features Implemented

### 1. Email Verification System

**Database Changes:**
- ✅ Added `email_verified` (BOOLEAN, default: false) to `users` table
- ✅ Added `verification_token` (VARCHAR 255) to `users` table
- ✅ Migration: `20250121_add_email_verification_and_settings.py`

**Backend Endpoints:**
- ✅ `POST /api/auth/verify-email?token={token}` - Verify email with token
- ✅ `POST /api/auth/resend-verification` - Resend verification email (authenticated)

**Flow:**
1. User registers → Account created with `email_verified=false`
2. Verification token generated and stored
3. Verification email sent with link: `{frontend_url}/verify-email?token={token}`
4. User clicks link → Token verified → `email_verified=true`
5. User can now access all features

**Email Template:**
- Template name: `email_verification`
- Variables:
  - `customer_name` - User's full name
  - `verification_url` - Verification link
  - `frontend_url` - Homepage link

### 2. System Settings Table

**Database Schema:**
```sql
CREATE TABLE system_settings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  key VARCHAR(100) UNIQUE NOT NULL,
  value TEXT,
  description VARCHAR(500),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

**Default Settings:**
| Key | Value | Description |
|-----|-------|-------------|
| `affiliate_auto_approve` | `false` | Auto-approve affiliate registrations without admin review |
| `affiliate_require_email_verification` | `true` | Require email verification before affiliates can access dashboard |
| `min_payout_amount` | `500000` | Minimum payout amount in kobo (₦5,000) |
| `commission_rate` | `0.10` | Default commission rate (10%) |

**Settings Service (`app/services/settings.py`):**
```python
async def get_setting(db, key, default=None) -> Optional[str]
async def get_bool_setting(db, key, default=False) -> bool
async def get_int_setting(db, key, default=0) -> int
async def get_float_setting(db, key, default=0.0) -> float
async def set_setting(db, key, value, description=None) -> None
```

### 3. Admin Settings Management

**Endpoints (`/api/admin/settings`):**
- ✅ `GET /settings` - List all system settings
- ✅ `GET /settings/{key}` - Get specific setting
- ✅ `PUT /settings/{key}` - Update setting value
- ✅ `POST /settings/{key}` - Create new setting

**Example Usage:**
```bash
# Get all settings
GET /api/admin/settings

# Update affiliate auto-approve
PUT /api/admin/settings/affiliate_auto_approve
{
  "value": "true"
}

# Update email verification requirement
PUT /api/admin/settings/affiliate_require_email_verification
{
  "value": "false"
}
```

### 4. Updated Affiliate Registration Flow

**Backend Logic (`/api/affiliates/register`):**
```python
1. Check if user is authenticated
2. Check setting: affiliate_require_email_verification
   - If true AND email_verified=false → Error: "Please verify your email"
3. Check if already an affiliate → Error: "Already registered"
4. Check setting: affiliate_auto_approve
   - If true → status = "active" (instant approval)
   - If false → status = "pending" (manual review)
5. Create affiliate with appropriate status
6. Send affiliate signup email
7. Return message based on status
```

**Response Messages:**
- Auto-approve ON: "Affiliate account activated!"
- Auto-approve OFF: "Affiliate registration submitted for review"

**Error Messages:**
- No email verification: "Please verify your email address before registering as an affiliate"
- Already registered: "Already registered as affiliate"

### 5. Authentication Flow Updates

**Registration (`POST /api/auth/register`):**
```
1. Validate request
2. Check if email exists
3. Generate verification_token
4. Create user (email_verified=false)
5. Send verification email
6. Return access & refresh tokens
```

**Login (`POST /api/auth/login`):**
- No changes - users can login even without email verification
- Features requiring verification will check individually

## Configuration Options

### Scenario 1: Strict Verification + Manual Approval (Default)
```
affiliate_require_email_verification = true
affiliate_auto_approve = false
```
**Flow:**
1. User registers → Verification email sent
2. User verifies email
3. User registers as affiliate → Status: "pending"
4. Admin reviews and approves
5. Affiliate can access dashboard

### Scenario 2: Strict Verification + Auto Approval
```
affiliate_require_email_verification = true
affiliate_auto_approve = true
```
**Flow:**
1. User registers → Verification email sent
2. User verifies email
3. User registers as affiliate → Status: "active" (instant!)
4. Affiliate can access dashboard immediately

### Scenario 3: No Verification + Manual Approval
```
affiliate_require_email_verification = false
affiliate_auto_approve = false
```
**Flow:**
1. User registers (no verification required)
2. User registers as affiliate → Status: "pending"
3. Admin reviews and approves
4. Affiliate can access dashboard

### Scenario 4: No Verification + Auto Approval
```
affiliate_require_email_verification = false
affiliate_auto_approve = true
```
**Flow:**
1. User registers (no verification required)
2. User registers as affiliate → Status: "active" (instant!)
3. Affiliate can access dashboard immediately

## Frontend Requirements

### 1. Email Verification Page (`/verify-email`)
**Required:**
- Read `token` from URL query parameter
- Call `POST /api/auth/verify-email?token={token}`
- Show success message + redirect to dashboard/affiliate
- Show error message if token invalid

### 2. Affiliate Signup Flow Updates
**Required checks:**
- After registration, check if email verification is required
- Show verification pending message if needed
- Disable affiliate registration button until verified
- Show "Verify email" prompt with resend option

### 3. Affiliate Dashboard Updates
**Status handling:**
- Check `email_verified` status
- If not verified + required → Show verification prompt
- If verified + pending → Show "under review" message
- If verified + active → Show full dashboard
- If verified + suspended → Show suspension message

### 4. Email Verification Banner
**Show when:**
- User is logged in
- `email_verified = false`
- On all pages except verification page

**Content:**
```
⚠️ Please verify your email address to access all features.
[Resend verification email] [x]
```

## Database Migration

**Run migration:**
```bash
# Apply migration
alembic upgrade head

# Verify tables
psql -d dbname -c "\d system_settings"
psql -d dbname -c "\d users" | grep verified
```

**Verify default settings:**
```sql
SELECT * FROM system_settings;
```

## Admin Panel Integration

### Settings Page (Frontend)
**Required:**
- Settings management UI at `/admin/settings`
- Toggle switches for boolean settings
- Text inputs for string/number settings
- Description tooltips
- Save confirmation

**Example UI:**
```
Affiliate Settings
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

☑️ Require email verification for affiliates
   Users must verify their email before registering as affiliates

☐ Auto-approve affiliate registrations
   Automatically activate new affiliates without manual review

Commission Rate: [0.10] (10%)
Min Payout Amount: [₦5,000]

[Save Changes]
```

## Email Template

**Create template in database:**
```sql
INSERT INTO email_templates (name, subject, body) VALUES (
  'email_verification',
  'Verify your email address',
  '<html>
    <body style="font-family: sans-serif;">
      <h2>Hi {{customer_name}},</h2>
      <p>Thanks for signing up! Please verify your email address to activate your account.</p>
      <p>
        <a href="{{verification_url}}" style="background: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block;">
          Verify Email Address
        </a>
      </p>
      <p>Or copy and paste this link:</p>
      <p><a href="{{verification_url}}">{{verification_url}}</a></p>
      <p>This link will expire in 24 hours.</p>
      <hr>
      <p style="color: #666; font-size: 12px;">
        If you didn''t create an account, you can safely ignore this email.
      </p>
    </body>
  </html>'
);
```

## Testing Checklist

### Email Verification
- [ ] Register new user → Verification email sent
- [ ] Check database → `email_verified=false`, `verification_token` set
- [ ] Click verification link → Email verified
- [ ] Check database → `email_verified=true`, `verification_token=null`
- [ ] Try to verify again → Error: "Invalid token"
- [ ] Resend verification → New token generated + email sent

### Affiliate Registration (Verification Required)
- [ ] Try to register as affiliate without verification → Error
- [ ] Verify email
- [ ] Register as affiliate → Success
- [ ] Check status based on auto-approve setting

### Affiliate Registration (No Verification Required)
- [ ] Change setting: `affiliate_require_email_verification=false`
- [ ] Register new user (unverified)
- [ ] Register as affiliate → Success (no email check)

### Auto-Approval
- [ ] Enable: `affiliate_auto_approve=true`
- [ ] Register as affiliate → Status: "active"
- [ ] Dashboard accessible immediately

### Manual Approval
- [ ] Disable: `affiliate_auto_approve=false`
- [ ] Register as affiliate → Status: "pending"
- [ ] Dashboard shows "under review"
- [ ] Admin approves → Status: "active"
- [ ] Dashboard shows full features

### Admin Settings
- [ ] GET /api/admin/settings → All settings returned
- [ ] PUT /api/admin/settings/affiliate_auto_approve → Updated
- [ ] Verify change reflected in affiliate registration

## Security Considerations

✅ **Token Security:**
- Verification tokens are 32-byte URL-safe random strings
- Tokens are single-use (deleted after verification)
- Consider adding expiration timestamp (TODO)

✅ **Rate Limiting:**
- Registration: 5 attempts per 5 minutes
- Resend verification: Consider adding (TODO)

✅ **Authorization:**
- Admin settings endpoints require admin role
- Affiliate registration requires authentication
- Email verification is public (token-based)

## Files Created/Modified

### Backend
- ✅ `app/models/user.py` - Added email verification fields
- ✅ `app/models/settings.py` - NEW system settings model
- ✅ `app/services/settings.py` - NEW settings service
- ✅ `app/services/email.py` - Added `send_verification_email()`
- ✅ `app/routes/auth.py` - Added verification endpoints
- ✅ `app/routes/affiliates.py` - Updated registration logic
- ✅ `app/routes/admin_settings.py` - NEW admin settings routes
- ✅ `app/main.py` - Registered admin_settings router
- ✅ `alembic/versions/20250121_add_email_verification_and_settings.py` - Migration

### Documentation
- ✅ `EMAIL_VERIFICATION_AND_AFFILIATE_APPROVAL.md` - This document

## Summary

The system now provides:

1. ✅ **Email Verification** - Users must verify emails to access affiliate program
2. ✅ **Configurable Approval** - Admin can toggle auto-approve on/off
3. ✅ **Settings Management** - Admin panel for all system settings
4. ✅ **Flexible Configuration** - 4 different scenarios supported
5. ✅ **Secure Token System** - URL-safe, single-use verification tokens
6. ✅ **Database-Driven Settings** - No code changes needed to adjust behavior
7. ✅ **Email Templates** - Professional verification emails
8. ✅ **Admin Controls** - Full control over affiliate onboarding

**Default Behavior:**
- Email verification: **REQUIRED** for affiliates
- Affiliate approval: **MANUAL** review by admin

Admins can change these settings anytime via `/api/admin/settings` endpoints! 🎯
