# Mobile App Configuration Endpoint

## Overview
Added a new `/api/config` endpoint that provides public configuration to the mobile app, including OAuth client IDs and payment gateway public keys.

## Changes Made

### 1. New Route: `app/routes/config.py`
Created a new public endpoint that returns runtime configuration for the mobile app.

**Endpoint:** `GET /api/config`

**Response:**
```json
{
  "google_web_client_id": "your-google-oauth-web-client-id",
  "paystack_public_key": "pk_live_xxxxx",
  "flutterwave_public_key": "FLWPUBK_xxxxx"
}
```

**Security:**
- ✅ Returns ONLY public keys (safe to expose)
- ✅ No authentication required (public endpoint)
- ❌ Never returns secret keys or private keys

### 2. Updated `app/main.py`
- Imported the new `config_router`
- Registered it at `/api/config` (first in the list for easy discovery)

## Environment Variables Required

Ensure these are set in your `.env` file:

```bash
# Google OAuth (for social login)
GOOGLE_CLIENT_ID=your-google-oauth-web-client-id-from-firebase-console

# Paystack (for payments)
PAYSTACK_PUBLIC_KEY=pk_live_your-paystack-public-key
PAYSTACK_SECRET_KEY=sk_live_your-paystack-secret-key  # Never exposed to mobile

# Flutterwave (optional, for payments)
FLUTTERWAVE_PUBLIC_KEY=FLWPUBK_TEST-xxxxx
FLUTTERWAVE_SECRET_KEY=FLWSECK_TEST-xxxxx  # Never exposed to mobile
```

## How the Mobile App Uses This

1. **On App Startup:**
   - Mobile app calls `GET /api/config`
   - Stores the keys in `configStore` (Zustand state)

2. **Google Sign-In:**
   - Uses `google_web_client_id` to configure `GoogleSignin.configure()`
   - Exchanges the ID token with backend via `POST /api/auth/google`

3. **Paystack Payments:**
   - Wraps app in `<PaystackProvider publicKey={paystackPublicKey}>`
   - Uses the hook to trigger payment checkout
   - Backend verifies payment using the secret key

## Testing

```bash
# Test the endpoint
curl http://localhost:8000/api/config

# Expected response:
{
  "google_web_client_id": "123456789-abc.apps.googleusercontent.com",
  "paystack_public_key": "pk_test_xxxxx",
  "flutterwave_public_key": "FLWPUBK_TEST-xxxxx"
}
```

## Deployment Checklist

- [ ] Set `GOOGLE_CLIENT_ID` in production environment
- [ ] Set `PAYSTACK_PUBLIC_KEY` in production environment  
- [ ] Set `PAYSTACK_SECRET_KEY` in production environment (never expose this)
- [ ] Set `FLUTTERWAVE_PUBLIC_KEY` in production environment (if using Flutterwave)
- [ ] Set `FLUTTERWAVE_SECRET_KEY` in production environment (never expose this)
- [ ] Verify `/api/config` returns correct keys in production
- [ ] Verify mobile app can fetch config on startup

## Security Notes

1. **Public vs Secret Keys:**
   - ✅ Public keys (returned by `/api/config`): Safe to expose, used for client-side initialization
   - ❌ Secret keys (stored in backend only): Never expose, used for server-side verification

2. **Why This is Safe:**
   - Google Web Client ID: Public by design, used for OAuth flow
   - Paystack Public Key: Public by design, used for checkout UI
   - Flutterwave Public Key: Public by design, used for payment initialization
   - All payment verification happens on the backend using secret keys

3. **What's Protected:**
   - Payment verification (backend only, using secret keys)
   - OAuth token exchange (backend only)
   - Webhook signature verification (backend only, using webhook secrets)

## Related Files

**Backend:**
- `app/routes/config.py` (new)
- `app/main.py` (updated)
- `app/config.py` (existing settings)

**Mobile:**
- `src/api/endpoints.ts` (added `configApi.getConfig()`)
- `src/store/configStore.ts` (new store for runtime config)
- `App.tsx` (fetches config on startup, wraps in PaystackProvider)
- `src/screens/auth/LoginScreen.tsx` (reconfigures GoogleSignin when key loads)
