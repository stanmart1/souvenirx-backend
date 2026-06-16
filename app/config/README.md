# Firebase Configuration

This directory contains Firebase configuration files for push notifications.

## Setup Instructions

1. **Download Firebase Credentials:**
   - Go to [Firebase Console](https://console.firebase.google.com/)
   - Select your project
   - Go to Project Settings > Service Accounts
   - Click "Generate New Private Key"
   - Download the JSON file

2. **Configure the Application:**
   - Copy `firebase-credentials.json.example` to `firebase-credentials.json`
   - Replace the contents with your downloaded credentials
   - **NEVER commit the actual credentials file to git**

3. **Update Environment Variables:**
   - Ensure `.env` has the correct path:
     ```
     FIREBASE_CREDENTIALS_PATH=app/config/firebase-credentials.json
     ```

## Security Notes

- ✅ `firebase-credentials.json` is in `.gitignore`
- ✅ Only `firebase-credentials.json.example` is tracked in git
- ⚠️ Never share or commit actual Firebase credentials
- ⚠️ Rotate credentials immediately if accidentally exposed

## Files

- `firebase-credentials.json.example` - Template file (tracked in git)
- `firebase-credentials.json` - Actual credentials (ignored by git)
