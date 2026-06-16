# SouvenirX API Documentation - New Endpoints

**Version:** 2.0  
**Last Updated:** 2026-06-16  
**Base URL:** `https://api.souvenirx.com`

---

## Table of Contents

1. [Authentication](#authentication)
2. [User Management](#user-management)
3. [Audit Logs](#audit-logs)
4. [Email Verification](#email-verification)
5. [Customer Management](#customer-management)
6. [Error Codes](#error-codes)

---

## Authentication

All admin endpoints require authentication with an admin JWT token.

**Headers:**
```
Authorization: Bearer <admin_jwt_token>
```

---

## User Management

### List All Users

Get a paginated list of all users with filtering options.

**Endpoint:** `GET /api/admin/users`

**Query Parameters:**
- `search` (optional): Search by name or email
- `role_filter` (optional): Filter by role (`customer`, `affiliate`, `admin`)
- `is_active` (optional): Filter by active status (`true`, `false`)
- `email_verified` (optional): Filter by email verification status (`true`, `false`)
- `page` (optional, default: 1): Page number
- `limit` (optional, default: 50, max: 100): Items per page

**Response:**
```json
{
  "users": [
    {
      "id": "uuid",
      "name": "John Doe",
      "email": "john@example.com",
      "phone": "+2348012345678",
      "roles": ["customer", "affiliate"],
      "active_role": "customer",
      "joined": "2024-01-15",
      "is_active": true,
      "email_verified": true,
      "tags": "vip,frequent-buyer"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 150,
    "pages": 3
  }
}
```

**Example:**
```bash
curl -X GET "https://api.souvenirx.com/api/admin/users?search=john&role_filter=customer&page=1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### Update User Roles

Update a user's roles (customer, affiliate, admin).

**Endpoint:** `PATCH /api/admin/users/{user_id}/roles`

**Request Body:**
```json
{
  "roles": ["customer", "affiliate"]
}
```

**Response:**
```json
{
  "message": "Roles updated successfully",
  "roles": ["customer", "affiliate"]
}
```

**Validation Rules:**
- At least one role required
- Valid roles: `customer`, `affiliate`, `admin`
- Cannot remove admin role from yourself
- Automatically updates `active_role` if needed

**Example:**
```bash
curl -X PATCH "https://api.souvenirx.com/api/admin/users/uuid/roles" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"roles": ["customer", "affiliate"]}'
```

---

### Delete User

Soft delete (deactivate) or hard delete (permanent) a user.

**Endpoint:** `DELETE /api/admin/users/{user_id}?permanent=false`

**Query Parameters:**
- `permanent` (optional, default: false): If true, permanently deletes user (requires admin role)

**Soft Delete Response:**
```json
{
  "message": "User deactivated successfully"
}
```

**Hard Delete Response:**
```json
{
  "message": "User permanently deleted"
}
```

**Behavior:**
- **Soft Delete:** Sets `is_active=false`, anonymizes email to `deleted_{uuid}@deleted.local`
- **Hard Delete:** Permanently removes user from database (GDPR compliance)
- Cannot delete yourself

**Example:**
```bash
# Soft delete
curl -X DELETE "https://api.souvenirx.com/api/admin/users/uuid" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Hard delete (permanent)
curl -X DELETE "https://api.souvenirx.com/api/admin/users/uuid?permanent=true" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### Manually Verify User Email

Admin can manually verify a user's email address.

**Endpoint:** `POST /api/admin/users/{user_id}/verify-email`

**Response:**
```json
{
  "message": "Email verified successfully"
}
```

**Behavior:**
- Sets `email_verified=true`
- Clears `verification_token` and `verification_token_expires_at`
- Logs audit trail

**Example:**
```bash
curl -X POST "https://api.souvenirx.com/api/admin/users/uuid/verify-email" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### Bulk Update Users

Perform bulk operations on multiple users.

**Endpoint:** `POST /api/admin/users/bulk-update`

**Request Body:**
```json
{
  "user_ids": ["uuid1", "uuid2", "uuid3"],
  "action": "activate",
  "value": "optional-value-for-tags"
}
```

**Supported Actions:**
- `activate`: Set `is_active=true`
- `deactivate`: Set `is_active=false`
- `verify_email`: Manually verify emails
- `add_tag`: Add a tag to users (requires `value`)
- `remove_tag`: Remove a tag from users (requires `value`)

**Response:**
```json
{
  "message": "3 users updated successfully",
  "action": "activate"
}
```

**Example:**
```bash
# Bulk activate users
curl -X POST "https://api.souvenirx.com/api/admin/users/bulk-update" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_ids": ["uuid1", "uuid2"],
    "action": "activate"
  }'

# Bulk add tag
curl -X POST "https://api.souvenirx.com/api/admin/users/bulk-update" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_ids": ["uuid1", "uuid2"],
    "action": "add_tag",
    "value": "vip"
  }'
```

---

## Audit Logs

### List Audit Logs

View audit trail of all admin actions with filtering.

**Endpoint:** `GET /api/admin/audit-logs`

**Query Parameters:**
- `resource_type` (optional): Filter by resource type (`user`, `order`, etc.)
- `resource_id` (optional): Filter by specific resource ID
- `admin_id` (optional): Filter by admin who performed action
- `action` (optional): Filter by action type (`update_customer`, `reset_password`, etc.)
- `start_date` (optional): Filter from date (ISO format: YYYY-MM-DD)
- `end_date` (optional): Filter until date (ISO format: YYYY-MM-DD)
- `page` (optional, default: 1): Page number
- `limit` (optional, default: 50, max: 100): Items per page

**Response:**
```json
{
  "logs": [
    {
      "id": 123,
      "admin_id": "uuid",
      "admin_name": "Admin User",
      "admin_email": "admin@souvenirx.com",
      "action": "reset_password",
      "resource_type": "user",
      "resource_id": "customer-uuid",
      "changes": {
        "reset_by_admin": "Admin User"
      },
      "ip_address": "192.168.1.1",
      "user_agent": "Mozilla/5.0...",
      "created_at": "2024-06-16T10:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 250,
    "pages": 5
  }
}
```

**Example:**
```bash
# Get all audit logs
curl -X GET "https://api.souvenirx.com/api/admin/audit-logs" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Filter by date range and action
curl -X GET "https://api.souvenirx.com/api/admin/audit-logs?action=reset_password&start_date=2024-06-01&end_date=2024-06-16" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Customer Management

### Reset Customer Password

Admin can reset a customer's password.

**Endpoint:** `POST /api/admin/customers/{customer_id}/reset-password`

**Request Body:**
```json
{
  "new_password": "newSecurePassword123"
}
```

**Response:**
```json
{
  "message": "Password reset successfully"
}
```

**Behavior:**
- Validates password minimum 8 characters
- Sends email notification to customer
- Logs audit trail with admin name
- Cannot reset own password

**Email Notification:**
Customer receives an email with:
- Notification that password was reset
- Admin name who performed the action
- Security recommendations
- Warning to contact support if unauthorized

**Example:**
```bash
curl -X POST "https://api.souvenirx.com/api/admin/customers/uuid/reset-password" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"new_password": "newSecurePassword123"}'
```

---

### Calculate Customer LTV (Optimized)

Calculate customer lifetime value using database aggregation.

**Endpoint:** `GET /api/admin/customers/{customer_id}/ltv`

**Response:**
```json
{
  "ltv": 150000,
  "total_orders": 12,
  "avg_order_value": 12500,
  "first_order_date": "2024-01-15T10:00:00Z",
  "last_order_date": "2024-06-10T15:30:00Z",
  "customer_lifetime_days": 147,
  "purchase_frequency": 2.45
}
```

**Metrics:**
- `ltv`: Total lifetime value (in kobo)
- `total_orders`: Number of successful orders
- `avg_order_value`: Average order value (in kobo)
- `first_order_date`: Date of first order
- `last_order_date`: Date of most recent order
- `customer_lifetime_days`: Days since first order
- `purchase_frequency`: Orders per month

**Performance:**
Uses SQL aggregation (COUNT, SUM, MIN, MAX) instead of loading all orders. Handles large order histories efficiently.

**Example:**
```bash
curl -X GET "https://api.souvenirx.com/api/admin/customers/uuid/ltv" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### Export Customers (Streaming)

Export customer list as CSV with streaming for large datasets.

**Endpoint:** `GET /api/admin/customers/export`

**Response:**
CSV file download with headers:
```
ID,Name,Email,Phone,Tags,Status,Joined,Total Orders,Total Spent (NGN),Email Verified
```

**Features:**
- Streams data in batches of 100 customers
- Handles large datasets without timeout
- Includes order statistics (total orders, total spent)
- Proper CSV escaping for commas and quotes
- Email verification status included

**Example:**
```bash
curl -X GET "https://api.souvenirx.com/api/admin/customers/export" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -o customers_export.csv
```

---

## Email Verification

### Email Verification Enforcement

Registered users must verify their email before placing orders.

**Affected Endpoints:**
- `POST /api/orders` - Create order

**Behavior:**
- Guest users can still checkout without verification
- Registered users with unverified emails receive 403 error
- Clear error message with instructions to verify email

**Error Response:**
```json
{
  "detail": "Please verify your email address before placing an order. Check your inbox for the verification link."
}
```

**Token Expiration:**
- Verification tokens expire after 24 hours
- Users can request a new verification email
- Rate limited to 5 verification attempts per 5 minutes

---

## Error Codes

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 400 | Bad Request | Invalid input or validation error |
| 401 | Unauthorized | Missing or invalid authentication token |
| 403 | Forbidden | Insufficient permissions or email not verified |
| 404 | Not Found | Resource not found |
| 409 | Conflict | Duplicate request (idempotency) |
| 500 | Internal Server Error | Server error |

### Common Error Responses

**Invalid Input:**
```json
{
  "detail": "At least one role is required"
}
```

**Unauthorized:**
```json
{
  "detail": "Admin access required"
}
```

**Email Not Verified:**
```json
{
  "detail": "Please verify your email address before placing an order. Check your inbox for the verification link."
}
```

**Self-Operation Prevention:**
```json
{
  "detail": "Cannot delete your own account"
}
```

---

## Rate Limiting

### Email Verification
- **Limit:** 5 attempts per 5 minutes per IP address
- **Scope:** Verification endpoint only
- **Response:** 429 Too Many Requests

### Admin Endpoints
- **Limit:** Not yet implemented (planned)
- **Recommended:** 100 requests per minute per admin

---

## Audit Trail

All admin actions are automatically logged with:
- Admin ID, name, and email
- Action performed
- Resource type and ID
- Changes made (before/after values)
- IP address
- User agent
- Timestamp

**Logged Actions:**
- `update_customer` - Customer info updated
- `add_note` - Note added to customer
- `delete_note` - Note deleted from customer
- `update_tags` - Customer tags updated
- `reset_password` - Password reset by admin
- `update_roles` - User roles changed
- `soft_delete_user` - User deactivated
- `hard_delete_user` - User permanently deleted
- `verify_email` - Email manually verified
- `bulk_activate` - Bulk user activation
- `bulk_deactivate` - Bulk user deactivation
- `bulk_verify_email` - Bulk email verification
- `bulk_add_tag` - Bulk tag addition
- `bulk_remove_tag` - Bulk tag removal

---

## Security Best Practices

### For API Consumers

1. **Always use HTTPS** - Never send tokens over HTTP
2. **Store tokens securely** - Use secure storage (not localStorage for sensitive apps)
3. **Implement token refresh** - Refresh tokens before expiration
4. **Validate responses** - Check status codes and error messages
5. **Rate limit your requests** - Respect API rate limits
6. **Log API errors** - Monitor for unusual activity

### For Admins

1. **Use strong passwords** - Minimum 12 characters with mixed case, numbers, symbols
2. **Enable 2FA** - When available (planned feature)
3. **Review audit logs regularly** - Check for suspicious activity
4. **Limit admin accounts** - Only create admin accounts when necessary
5. **Use soft delete** - Prefer soft delete over hard delete for data recovery
6. **Verify before bulk operations** - Double-check user selections before bulk updates

---

## Changelog

### Version 2.0 (2026-06-16)

**New Features:**
- User management endpoints (list, update roles, delete, verify email)
- Bulk operations endpoint
- Audit log viewer with filtering
- Admin password reset with email notification
- Streaming CSV export for large datasets
- Email verification enforcement on orders
- Optimized LTV calculation using aggregation

**Improvements:**
- Multi-role user support (fixed query bug)
- Input validation on all endpoints
- Comprehensive audit logging
- Rate limiting on email verification
- 24-hour token expiration
- Improved error messages

**Security:**
- Email verification required for registered users
- Audit trail for all admin actions
- IP address and user agent tracking
- Self-operation prevention (can't delete/demote self)
- Password reset email notifications

---

## Support

For API support, contact:
- **Email:** support@souvenirx.com
- **Documentation:** https://docs.souvenirx.com
- **Status Page:** https://status.souvenirx.com

---

## License

© 2024 SouvenirX. All rights reserved.
