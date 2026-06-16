# SouvenirX Admin User Guide

**Version:** 2.0  
**Last Updated:** 2026-06-16  
**For:** Admin Dashboard Users

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [User Management](#user-management)
3. [Customer Management](#customer-management)
4. [Audit Logs](#audit-logs)
5. [Email Verification](#email-verification)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)

---

## Getting Started

### What's New in Version 2.0

Welcome to the upgraded SouvenirX admin dashboard! Here's what's new:

✅ **User Management** - Manage all users, not just customers  
✅ **Role Management** - Promote/demote users between roles  
✅ **Bulk Operations** - Update multiple users at once  
✅ **Audit Logs** - See who did what and when  
✅ **Password Reset** - Reset customer passwords  
✅ **Email Verification** - Manually verify user emails  
✅ **Enhanced Security** - Email verification required for orders  

---

## User Management

### Viewing All Users

**Location:** Admin Dashboard → Users

**Features:**
- View all users (customers, affiliates, admins)
- Search by name or email
- Filter by role, status, or verification
- See user roles and verification status

**How to Use:**
1. Navigate to **Users** page
2. Use search bar to find specific users
3. Use filters to narrow results:
   - **Role:** Customer, Affiliate, Admin
   - **Status:** Active, Inactive
   - **Email Verified:** Yes, No
4. Click on a user to view details

---

### Managing User Roles

**What are roles?**
- **Customer:** Can place orders, view order history
- **Affiliate:** Can refer customers, earn commissions
- **Admin:** Can manage users, orders, and settings

**Users can have multiple roles!** For example, a customer can also be an affiliate.

**How to Update Roles:**
1. Find the user in the Users list
2. Click **Edit Roles** button
3. Select/deselect roles:
   - ☑ Customer
   - ☑ Affiliate
   - ☐ Admin
4. Click **Save**

**Important Notes:**
- ⚠️ At least one role is required
- ⚠️ You cannot remove your own admin role
- ✅ Changes are logged in audit trail

---

### Deleting Users

There are two types of deletion:

#### Soft Delete (Recommended)
**What it does:**
- Deactivates the user account
- Anonymizes email address
- Preserves order history
- Can be reversed if needed

**When to use:**
- Customer requests account closure
- Inactive accounts cleanup
- GDPR compliance (right to be forgotten)

**How to soft delete:**
1. Find user in Users list
2. Click **Delete** button
3. Confirm deletion (permanent=false)
4. User is deactivated

#### Hard Delete (Permanent)
**What it does:**
- Permanently removes user from database
- Deletes all associated data
- **Cannot be undone!**

**When to use:**
- Legal requirement to delete data
- Spam/fake accounts
- Super admin cleanup only

**How to hard delete:**
1. Find user in Users list
2. Click **Delete** button
3. Check "Permanent deletion" checkbox
4. Type "DELETE" to confirm
5. User is permanently removed

**⚠️ Warning:** Hard delete requires admin role and cannot be undone!

---

### Bulk Operations

Update multiple users at once to save time.

**Available Actions:**
- **Activate** - Enable multiple user accounts
- **Deactivate** - Disable multiple user accounts
- **Verify Email** - Manually verify multiple emails
- **Add Tag** - Add a tag to multiple users
- **Remove Tag** - Remove a tag from multiple users

**How to Use:**
1. Go to Users list
2. Select users using checkboxes
3. Choose action from dropdown:
   - Activate Users
   - Deactivate Users
   - Verify Emails
   - Add Tag
   - Remove Tag
4. If adding/removing tag, enter tag name
5. Click **Apply**
6. Confirm action

**Example Use Cases:**
- Activate 50 new users after verification
- Add "VIP" tag to top customers
- Deactivate inactive accounts
- Verify emails for imported users

**⚠️ Important:**
- You cannot perform bulk operations on your own account
- All bulk operations are logged in audit trail
- Changes cannot be undone (except reactivation)

---

## Customer Management

### Viewing Customer Details

**Location:** Admin Dashboard → Customers → [Customer Name]

**What you can see:**
- Basic info (name, email, phone)
- Order history
- Lifetime value (LTV)
- Tags
- Notes
- Verification status

---

### Resetting Customer Passwords

Sometimes customers forget their passwords or need help accessing their accounts.

**How to Reset:**
1. Go to Customers list
2. Click on customer name
3. Click **Reset Password** button
4. Enter new password (minimum 8 characters)
5. Click **Confirm**

**What happens:**
- Password is immediately changed
- Customer receives email notification
- Email includes:
  - Notification of password change
  - Your admin name
  - Security recommendations
  - Instructions to contact support if unauthorized

**⚠️ Security Notes:**
- Only reset passwords when customer requests it
- Verify customer identity before resetting
- Use strong passwords (suggest password manager)
- Customer should change password after first login

---

### Calculating Customer Lifetime Value (LTV)

**What is LTV?**
Customer Lifetime Value shows how much a customer has spent over their entire relationship with SouvenirX.

**How to View:**
1. Go to customer detail page
2. Click **Calculate LTV** button
3. View metrics:
   - **Total Spent:** Total revenue from customer
   - **Total Orders:** Number of successful orders
   - **Average Order Value:** Average spend per order
   - **Customer Lifetime:** Days since first order
   - **Purchase Frequency:** Orders per month

**How to Use:**
- Identify VIP customers (high LTV)
- Target marketing campaigns
- Offer loyalty rewards
- Prioritize customer support

**Example:**
```
LTV: ₦150,000
Total Orders: 12
Avg Order Value: ₦12,500
Customer Lifetime: 147 days
Purchase Frequency: 2.45 orders/month
```

This customer is a high-value, frequent buyer - perfect for VIP program!

---

### Adding Customer Notes

Keep track of important customer information.

**How to Add:**
1. Go to customer detail page
2. Scroll to **Notes** section
3. Click **Add Note**
4. Type note (max 1000 characters)
5. Click **Save**

**Use Cases:**
- Special delivery instructions
- Customer preferences
- Support interactions
- Payment issues
- VIP status reasons

**Example Notes:**
- "Prefers delivery on weekends"
- "Allergic to latex - no balloon products"
- "VIP customer - priority shipping"
- "Requested refund on order #SVX-12345"

**⚠️ Note:** All notes are logged in audit trail with your name.

---

### Exporting Customer Data

Export customer list to CSV for analysis or backup.

**How to Export:**
1. Go to Customers page
2. Click **Export CSV** button
3. File downloads automatically

**What's Included:**
- Customer ID
- Name
- Email
- Phone
- Tags
- Status (Active/Inactive)
- Join Date
- Total Orders
- Total Spent
- Email Verified (Yes/No)

**Use Cases:**
- Backup customer data
- Import to email marketing tool
- Analyze customer segments
- Create reports for management

**Performance:**
- Handles thousands of customers
- Streams data (no timeout)
- Opens in Excel, Google Sheets, etc.

---

## Audit Logs

### What are Audit Logs?

Audit logs track every action performed by admins. This ensures accountability and helps troubleshoot issues.

**What's Logged:**
- Who performed the action (admin name)
- What action was performed
- When it happened (timestamp)
- What changed (before/after values)
- IP address
- Browser/device info

---

### Viewing Audit Logs

**Location:** Admin Dashboard → Audit Logs

**How to Use:**
1. Navigate to Audit Logs page
2. View recent actions (newest first)
3. Use filters to narrow results:
   - **Date Range:** From/To dates
   - **Admin:** Filter by admin user
   - **Action:** Filter by action type
   - **Resource:** Filter by user/order/etc.

**Example Filters:**
- "Show me all password resets in June"
- "Show me all actions by Admin John"
- "Show me all changes to customer #12345"

---

### Understanding Audit Log Entries

**Example Entry:**
```
Admin: John Smith (john@souvenirx.com)
Action: Reset Password
Resource: User #abc-123
Changes: {"reset_by_admin": "John Smith"}
IP Address: 192.168.1.100
Time: 2024-06-16 10:30:00
```

**What it means:**
- John Smith reset a customer's password
- Customer ID is abc-123
- Action performed from IP 192.168.1.100
- Happened at 10:30 AM on June 16

---

### Common Audit Log Actions

| Action | Description |
|--------|-------------|
| `update_customer` | Customer info changed |
| `reset_password` | Password reset by admin |
| `add_note` | Note added to customer |
| `delete_note` | Note deleted from customer |
| `update_tags` | Customer tags changed |
| `update_roles` | User roles changed |
| `soft_delete_user` | User deactivated |
| `hard_delete_user` | User permanently deleted |
| `verify_email` | Email manually verified |
| `bulk_activate` | Multiple users activated |
| `bulk_deactivate` | Multiple users deactivated |

---

### Why Audit Logs Matter

**Security:**
- Detect unauthorized access
- Track suspicious activity
- Investigate security incidents

**Compliance:**
- GDPR audit trail
- Legal requirements
- Data protection compliance

**Troubleshooting:**
- "Who changed this customer's email?"
- "When was this password reset?"
- "Who deleted this user?"

**Accountability:**
- Track admin actions
- Prevent abuse
- Maintain trust

---

## Email Verification

### Why Email Verification Matters

Email verification ensures:
- Users own the email address they registered with
- Reduces spam and fake accounts
- Enables secure password resets
- Improves email deliverability

---

### Email Verification Status

**Verified (✅):**
- User clicked verification link
- Can place orders
- Can receive important emails

**Unverified (⚠️):**
- User hasn't verified email yet
- **Cannot place orders** (registered users only)
- Receives error when trying to checkout

**Guest Users:**
- Don't need verification
- Can checkout as guest

---

### Manually Verifying Emails

Sometimes you need to manually verify a customer's email (e.g., phone verification, known customer).

**How to Manually Verify:**
1. Go to customer detail page
2. Check verification status
3. If unverified, click **Verify Email** button
4. Confirm action
5. Email is immediately verified

**When to Use:**
- Customer verified identity by phone
- Known/trusted customer
- Email verification email not received
- Technical issues with verification link

**⚠️ Important:**
- Only verify emails you've confirmed
- Don't verify suspicious accounts
- Action is logged in audit trail

---

### Email Verification Tokens

**How it works:**
1. User registers account
2. System sends verification email
3. Email contains unique token link
4. User clicks link within 24 hours
5. Email is verified

**Token Expiration:**
- Tokens expire after 24 hours
- User can request new verification email
- Old token is invalidated when new one is sent

**Rate Limiting:**
- 5 verification attempts per 5 minutes
- Prevents brute-force attacks
- Protects against spam

---

## Best Practices

### Security

✅ **DO:**
- Use strong, unique passwords
- Log out when done
- Review audit logs regularly
- Verify customer identity before password resets
- Use soft delete instead of hard delete
- Keep admin accounts to minimum

❌ **DON'T:**
- Share your admin credentials
- Reset passwords without verification
- Delete users without backup
- Perform bulk operations without double-checking
- Ignore suspicious audit log entries

---

### Customer Service

✅ **DO:**
- Add notes for important customer info
- Tag VIP customers
- Respond to customer requests promptly
- Verify identity before account changes
- Send password reset confirmation

❌ **DON'T:**
- Share customer data with unauthorized people
- Reset passwords without customer request
- Delete accounts without confirmation
- Ignore customer privacy requests

---

### Data Management

✅ **DO:**
- Export customer data regularly (backup)
- Use tags to organize customers
- Review inactive accounts periodically
- Clean up test accounts
- Document important changes in notes

❌ **DON'T:**
- Hard delete without good reason
- Bulk delete without verification
- Export customer data to unsecured locations
- Share CSV exports via email

---

## Troubleshooting

### "Cannot delete your own account"

**Problem:** You're trying to delete or demote yourself.

**Solution:** Ask another admin to perform the action. This is a security feature to prevent accidental self-lockout.

---

### "At least one role is required"

**Problem:** You're trying to remove all roles from a user.

**Solution:** Every user must have at least one role. If you want to disable the account, use deactivate instead.

---

### "Email already verified"

**Problem:** You're trying to manually verify an email that's already verified.

**Solution:** No action needed. The email is already verified.

---

### "User not found"

**Problem:** The user ID is invalid or user was deleted.

**Solution:** Double-check the user ID. If user was deleted, check audit logs to see who deleted it and when.

---

### "Admin access required"

**Problem:** Your account doesn't have admin role.

**Solution:** Contact a super admin to grant you admin role.

---

### CSV Export Not Downloading

**Problem:** CSV export button doesn't work or file is empty.

**Solution:**
1. Check your browser's download settings
2. Disable popup blockers
3. Try a different browser
4. Check if you have customers in the database
5. Contact support if issue persists

---

### Bulk Operation Failed

**Problem:** Bulk operation didn't complete or some users weren't updated.

**Solution:**
1. Check audit logs to see what happened
2. Verify user IDs are valid
3. Check if you selected your own account (not allowed)
4. Try smaller batches (50 users at a time)
5. Contact support with error message

---

## Keyboard Shortcuts

Speed up your workflow with keyboard shortcuts:

| Shortcut | Action |
|----------|--------|
| `Ctrl + K` | Search users |
| `Ctrl + E` | Export CSV |
| `Ctrl + N` | Add note |
| `Esc` | Close modal |
| `Ctrl + S` | Save changes |

*(Note: Shortcuts may vary by browser)*

---

## Getting Help

### Support Resources

**Documentation:**
- API Documentation: `API_DOCUMENTATION_NEW_ENDPOINTS.md`
- Implementation Plan: `IMPLEMENTATION_PLAN.md`
- Upgrade Summary: `UPGRADE_SUMMARY.md`

**Contact Support:**
- Email: support@souvenirx.com
- Phone: +234-XXX-XXXX-XXX
- Live Chat: Available 9 AM - 5 PM WAT

**Report Bugs:**
- Email: bugs@souvenirx.com
- Include: What you were doing, error message, screenshot

---

## Glossary

**Audit Log:** Record of all admin actions  
**Bulk Operation:** Action performed on multiple users at once  
**Hard Delete:** Permanent deletion (cannot be undone)  
**LTV (Lifetime Value):** Total revenue from a customer  
**Soft Delete:** Deactivation (can be reversed)  
**Tag:** Label to categorize customers  
**Token:** Unique code for email verification  
**Verification:** Confirming user owns their email address  

---

## Changelog

### Version 2.0 (2026-06-16)

**New Features:**
- User management page
- Role management
- Bulk operations
- Audit log viewer
- Password reset functionality
- Manual email verification
- Streaming CSV export
- Email verification enforcement

**Improvements:**
- Better search and filtering
- Optimized LTV calculation
- Enhanced security
- Comprehensive audit trail

---

## Tips & Tricks

💡 **Use tags to segment customers:**
- "VIP" for high-value customers
- "Wholesale" for bulk buyers
- "Frequent" for repeat customers
- "New" for recent signups

💡 **Review audit logs weekly:**
- Catch suspicious activity early
- Track admin performance
- Identify training needs

💡 **Export data before bulk operations:**
- Create backup before mass changes
- Easy to restore if needed

💡 **Add notes for future reference:**
- Document special requests
- Track customer preferences
- Record support interactions

💡 **Use filters to find users quickly:**
- Combine multiple filters
- Save time on large user lists
- Focus on specific segments

---

**Happy Administering! 🎉**

For questions or feedback, contact the SouvenirX support team.

© 2024 SouvenirX. All rights reserved.
