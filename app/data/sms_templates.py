"""Default SMS templates for all notifications."""

DEFAULT_SMS_TEMPLATES = {
    "cart_recovery": "Hi {customer_name}, you have items waiting in your cart at SouvenirX. Complete your order now: {frontend_url}/cart",
    "order_confirmation": "Hi {customer_name}, your order {order_number} has been confirmed. Track at {frontend_url}/track?id={order_number}",
    "shipping_notification": "Hi {customer_name}, your order {order_number} has been shipped. Track at {frontend_url}/track?id={order_number}",
    "password_reset": "Hi {customer_name}, use this link to reset your password: {reset_url}. Link expires in 1 hour.",
    "welcome": "Hi {customer_name}, welcome to SouvenirX! Browse products at {frontend_url}/shop",
    "affiliate_signup": "Hi {affiliate_name}, welcome to the SouvenirX affiliate program! Access dashboard at {frontend_url}/dashboard/affiliate",
    "payout_notification": "Hi {affiliate_name}, your payout of ₦{payout_amount} has been processed. View dashboard at {frontend_url}/dashboard/affiliate",
    "order_status_update": "Hi {customer_name}, your order {order_number} status is now: {status}. Track at {frontend_url}/track?id={order_number}",
}
