"""Default email templates with design system styling (no emojis)."""

# Shared layout helpers — kept as Python strings so each template stays self-contained.
_HEADER = """<tr>
                        <td style="background-color:#c4673a;padding:32px;text-align:center;">
                            <h1 style="margin:0;color:#ffffff;font-size:28px;font-weight:700;letter-spacing:-0.5px;">SouvenirX</h1>
                            <p style="margin:8px 0 0;color:#f5d9cc;font-size:14px;letter-spacing:0.5px;">Custom Souvenirs &amp; Corporate Gifts</p>
                        </td>
                    </tr>"""

_FOOTER = """<tr>
                        <td style="background-color:#f5f0ec;padding:28px 32px;text-align:center;border-top:1px solid #e8e0d8;">
                            <p style="margin:0 0 8px;color:#888888;font-size:13px;">Questions? Contact us at <a href="mailto:support@souvenirx.com" style="color:#c4673a;text-decoration:none;">support@souvenirx.com</a></p>
                            <p style="margin:0;color:#aaaaaa;font-size:12px;">© 2025 SouvenirX. All rights reserved.</p>
                        </td>
                    </tr>"""

_WRAPPER_OPEN = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
</head>
<body style="margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;background-color:#f5f0ec;-webkit-font-smoothing:antialiased;">
    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color:#f5f0ec;">
        <tr>
            <td style="padding:40px 20px;">
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="max-width:600px;margin:0 auto;background-color:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 4px 16px rgba(0,0,0,0.08);">"""

_WRAPPER_CLOSE = """                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""


def _btn(url: str, label: str) -> str:
    return f"""<table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin:32px auto 0;">
                                <tr>
                                    <td style="text-align:center;">
                                        <a href="{url}" style="display:inline-block;background-color:#c4673a;color:#ffffff;padding:16px 36px;text-decoration:none;border-radius:8px;font-weight:600;font-size:16px;letter-spacing:-0.3px;">{label}</a>
                                    </td>
                                </tr>
                            </table>"""


DEFAULT_EMAIL_TEMPLATES = [
    # ── 1. EMAIL VERIFICATION ────────────────────────────────────────────────
    {
        "name": "email_verification",
        "subject": "Verify Your Email — SouvenirX",
        "html_content": _WRAPPER_OPEN + _HEADER + """
                    <tr>
                        <td style="padding:48px 40px 40px;">
                            <h2 style="margin:0 0 8px;color:#1a1a1a;font-size:26px;font-weight:700;letter-spacing:-0.5px;">Verify Your Email Address</h2>
                            <p style="margin:0 0 28px;color:#888888;font-size:14px;">One last step to activate your account</p>
                            <p style="margin:0 0 20px;color:#444444;font-size:16px;line-height:1.7;">Hi <strong>{{customer_name}}</strong>,</p>
                            <p style="margin:0 0 28px;color:#555555;font-size:16px;line-height:1.7;">Thanks for signing up at SouvenirX! Please verify your email address by clicking the button below or entering the 6-digit code in the mobile app. <strong>This link and code expire in 24 hours</strong> for your security.</p>
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin:0 auto 32px;">
                                <tr>
                                    <td style="text-align:center;">
                                        <a href="{{verification_url}}" style="display:inline-block;background-color:#c4673a;color:#ffffff;padding:18px 40px;text-decoration:none;border-radius:8px;font-weight:700;font-size:16px;letter-spacing:-0.3px;">Verify Email Address</a>
                                    </td>
                                </tr>
                            </table>
                            {{otp_block}}
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color:#fdf8f5;border:1px solid #f0e4db;border-radius:8px;margin:0 0 28px;">
                                <tr>
                                    <td style="padding:16px 20px;">
                                        <p style="margin:0 0 6px;color:#888888;font-size:12px;text-transform:uppercase;letter-spacing:0.8px;font-weight:600;">Or copy this link into your browser</p>
                                        <p style="margin:0;color:#c4673a;font-size:13px;word-break:break-all;">{{verification_url}}</p>
                                    </td>
                                </tr>
                            </table>
                            <p style="margin:0;color:#aaaaaa;font-size:14px;line-height:1.6;">If you did not create an account, you can safely ignore this email.</p>
                        </td>
                    </tr>""" + _FOOTER + _WRAPPER_CLOSE,
        "variables": {"customer_name": "string", "verification_url": "string", "otp_block": "string"},
        "is_active": True,
    },

    # ── 2. WELCOME ───────────────────────────────────────────────────────────
    {
        "name": "welcome",
        "subject": "Welcome to SouvenirX — Your Account is Ready",
        "html_content": _WRAPPER_OPEN + _HEADER + """
                    <tr>
                        <td style="padding:48px 40px 40px;">
                            <h2 style="margin:0 0 8px;color:#1a1a1a;font-size:26px;font-weight:700;letter-spacing:-0.5px;">Welcome to SouvenirX!</h2>
                            <p style="margin:0 0 28px;color:#888888;font-size:14px;">Your account has been verified and is ready to use</p>
                            <p style="margin:0 0 20px;color:#444444;font-size:16px;line-height:1.7;">Hi <strong>{{customer_name}}</strong>,</p>
                            <p style="margin:0 0 28px;color:#555555;font-size:16px;line-height:1.7;">Your email has been verified. Welcome to SouvenirX — Nigeria's premier destination for custom souvenirs and corporate gifts.</p>
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin:0 0 32px;">
                                <tr>
                                    <td style="padding:20px;background-color:#fdf8f5;border-left:4px solid #c4673a;border-radius:0 8px 8px 0;">
                                        <p style="margin:0 0 8px;color:#1a1a1a;font-weight:600;font-size:15px;">What you can do now</p>
                                        <p style="margin:0 0 6px;color:#555555;font-size:14px;line-height:1.6;">Browse hundreds of customisable products — from branded mugs to bulk corporate orders.</p>
                                        <p style="margin:0;color:#555555;font-size:14px;line-height:1.6;">Upload your logo and get an instant preview before you order.</p>
                                    </td>
                                </tr>
                            </table>
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin:0 auto;">
                                <tr>
                                    <td style="text-align:center;">
                                        <a href="{{frontend_url}}/shop" style="display:inline-block;background-color:#c4673a;color:#ffffff;padding:18px 40px;text-decoration:none;border-radius:8px;font-weight:700;font-size:16px;letter-spacing:-0.3px;">Start Shopping</a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>""" + _FOOTER + _WRAPPER_CLOSE,
        "variables": {"customer_name": "string", "frontend_url": "string"},
        "is_active": True,
    },

    # ── 3. ORDER CONFIRMATION ────────────────────────────────────────────────
    {
        "name": "order_confirmation",
        "subject": "Order Confirmed — {{order_number}}",
        "html_content": _WRAPPER_OPEN + _HEADER + """
                    <tr>
                        <td style="padding:48px 40px 40px;">
                            <h2 style="margin:0 0 8px;color:#1a1a1a;font-size:26px;font-weight:700;letter-spacing:-0.5px;">Order Confirmed</h2>
                            <p style="margin:0 0 28px;color:#888888;font-size:14px;">We have received your order and are getting started</p>
                            <p style="margin:0 0 20px;color:#444444;font-size:16px;line-height:1.7;">Hi <strong>{{customer_name}}</strong>,</p>
                            <p style="margin:0 0 28px;color:#555555;font-size:16px;line-height:1.7;">Thank you for your order. We have received it and will begin processing shortly.</p>

                            <!-- Order reference box -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin:0 0 28px;background-color:#fdf8f5;border:1px solid #f0e4db;border-radius:8px;">
                                <tr>
                                    <td style="padding:20px 24px;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                            <tr>
                                                <td style="color:#888888;font-size:12px;text-transform:uppercase;letter-spacing:0.8px;font-weight:600;padding-bottom:6px;">Order Reference</td>
                                                <td style="color:#888888;font-size:12px;text-transform:uppercase;letter-spacing:0.8px;font-weight:600;padding-bottom:6px;text-align:right;">Order Total</td>
                                            </tr>
                                            <tr>
                                                <td style="color:#c4673a;font-size:20px;font-weight:700;letter-spacing:-0.5px;">{{order_number}}</td>
                                                <td style="color:#1a1a1a;font-size:20px;font-weight:700;letter-spacing:-0.5px;text-align:right;">&#8358;{{total_formatted}}</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>

                            <!-- Items summary -->
                            <p style="margin:0 0 12px;color:#1a1a1a;font-size:15px;font-weight:600;">Items Ordered</p>
                            {{items_html}}

                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin:32px auto 0;">
                                <tr>
                                    <td style="text-align:center;">
                                        <a href="{{frontend_url}}/track?id={{order_number}}" style="display:inline-block;background-color:#c4673a;color:#ffffff;padding:18px 40px;text-decoration:none;border-radius:8px;font-weight:700;font-size:16px;letter-spacing:-0.3px;">Track Your Order</a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>""" + _FOOTER + _WRAPPER_CLOSE,
        "variables": {
            "customer_name": "string",
            "order_number": "string",
            "total_formatted": "string",
            "items_html": "string",
            "frontend_url": "string",
        },
        "is_active": True,
    },

    # ── 4. ORDER STATUS UPDATE ───────────────────────────────────────────────
    {
        "name": "order_status_update",
        "subject": "Order Update — {{order_number}} is {{status_label}}",
        "html_content": _WRAPPER_OPEN + _HEADER + """
                    <tr>
                        <td style="padding:48px 40px 40px;">
                            <h2 style="margin:0 0 8px;color:#1a1a1a;font-size:26px;font-weight:700;letter-spacing:-0.5px;">Order Update</h2>
                            <p style="margin:0 0 28px;color:#888888;font-size:14px;">Your order status has changed</p>
                            <p style="margin:0 0 20px;color:#444444;font-size:16px;line-height:1.7;">Hi <strong>{{customer_name}}</strong>,</p>
                            <p style="margin:0 0 28px;color:#555555;font-size:16px;line-height:1.7;">{{status_message}}</p>

                            <!-- Status badge -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin:0 0 32px;background-color:#fdf8f5;border:1px solid #f0e4db;border-radius:8px;">
                                <tr>
                                    <td style="padding:20px 24px;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                            <tr>
                                                <td>
                                                    <p style="margin:0 0 4px;color:#888888;font-size:12px;text-transform:uppercase;letter-spacing:0.8px;font-weight:600;">Order Reference</p>
                                                    <p style="margin:0;color:#c4673a;font-size:18px;font-weight:700;letter-spacing:-0.5px;">{{order_number}}</p>
                                                </td>
                                                <td style="text-align:right;">
                                                    <p style="margin:0 0 4px;color:#888888;font-size:12px;text-transform:uppercase;letter-spacing:0.8px;font-weight:600;">Status</p>
                                                    <span style="display:inline-block;background-color:{{status_color}};color:#ffffff;padding:6px 16px;border-radius:20px;font-size:13px;font-weight:600;">{{status_label}}</span>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>

                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin:0 auto;">
                                <tr>
                                    <td style="text-align:center;">
                                        <a href="{{frontend_url}}/track?id={{order_number}}" style="display:inline-block;background-color:#c4673a;color:#ffffff;padding:18px 40px;text-decoration:none;border-radius:8px;font-weight:700;font-size:16px;letter-spacing:-0.3px;">View Order Details</a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>""" + _FOOTER + _WRAPPER_CLOSE,
        "variables": {
            "customer_name": "string",
            "order_number": "string",
            "status_label": "string",
            "status_message": "string",
            "status_color": "string",
            "frontend_url": "string",
        },
        "is_active": True,
    },

    # ── 5. SHIPPING NOTIFICATION (kept for backwards compatibility) ───────────
    {
        "name": "shipping_notification",
        "subject": "Your Order {{order_number}} Has Been Shipped",
        "html_content": _WRAPPER_OPEN + _HEADER + """
                    <tr>
                        <td style="padding:48px 40px 40px;">
                            <h2 style="margin:0 0 8px;color:#1a1a1a;font-size:26px;font-weight:700;letter-spacing:-0.5px;">Your Order Has Shipped</h2>
                            <p style="margin:0 0 28px;color:#888888;font-size:14px;">Your package is on its way</p>
                            <p style="margin:0 0 20px;color:#444444;font-size:16px;line-height:1.7;">Hi <strong>{{customer_name}}</strong>,</p>
                            <p style="margin:0 0 28px;color:#555555;font-size:16px;line-height:1.7;">Your order <strong>{{order_number}}</strong> has been dispatched and is on its way to you. You can track your delivery at any time using the button below.</p>
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin:0 auto;">
                                <tr>
                                    <td style="text-align:center;">
                                        <a href="{{frontend_url}}/track?id={{order_number}}" style="display:inline-block;background-color:#c4673a;color:#ffffff;padding:18px 40px;text-decoration:none;border-radius:8px;font-weight:700;font-size:16px;letter-spacing:-0.3px;">Track Shipment</a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>""" + _FOOTER + _WRAPPER_CLOSE,
        "variables": {"customer_name": "string", "order_number": "string", "frontend_url": "string"},
        "is_active": True,
    },

    # ── 6. PASSWORD RESET ────────────────────────────────────────────────────
    {
        "name": "password_reset",
        "subject": "Reset Your Password — SouvenirX",
        "html_content": _WRAPPER_OPEN + _HEADER + """
                    <tr>
                        <td style="padding:48px 40px 40px;">
                            <h2 style="margin:0 0 8px;color:#1a1a1a;font-size:26px;font-weight:700;letter-spacing:-0.5px;">Reset Your Password</h2>
                            <p style="margin:0 0 28px;color:#888888;font-size:14px;">You requested a password reset</p>
                            <p style="margin:0 0 20px;color:#444444;font-size:16px;line-height:1.7;">Hi <strong>{{customer_name}}</strong>,</p>
                            <p style="margin:0 0 28px;color:#555555;font-size:16px;line-height:1.7;">We received a request to reset your password. Click the button below to choose a new password. This link expires in <strong>1 hour</strong>.</p>
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin:0 auto 32px;">
                                <tr>
                                    <td style="text-align:center;">
                                        <a href="{{reset_url}}" style="display:inline-block;background-color:#c4673a;color:#ffffff;padding:18px 40px;text-decoration:none;border-radius:8px;font-weight:700;font-size:16px;letter-spacing:-0.3px;">Reset Password</a>
                                    </td>
                                </tr>
                            </table>
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color:#fdf8f5;border:1px solid #f0e4db;border-radius:8px;margin:0 0 28px;">
                                <tr>
                                    <td style="padding:16px 20px;">
                                        <p style="margin:0 0 6px;color:#888888;font-size:12px;text-transform:uppercase;letter-spacing:0.8px;font-weight:600;">Or copy this link into your browser</p>
                                        <p style="margin:0;color:#c4673a;font-size:13px;word-break:break-all;">{{reset_url}}</p>
                                    </td>
                                </tr>
                            </table>
                            <p style="margin:0;color:#aaaaaa;font-size:14px;line-height:1.6;">If you did not request a password reset, please ignore this email. Your password will not change.</p>
                        </td>
                    </tr>""" + _FOOTER + _WRAPPER_CLOSE,
        "variables": {"customer_name": "string", "reset_url": "string"},
        "is_active": True,
    },

    # ── 7. CART RECOVERY ─────────────────────────────────────────────────────
    {
        "name": "cart_recovery",
        "subject": "You left something behind — complete your order",
        "html_content": _WRAPPER_OPEN + _HEADER + """
                    <tr>
                        <td style="padding:48px 40px 40px;">
                            <h2 style="margin:0 0 8px;color:#1a1a1a;font-size:26px;font-weight:700;letter-spacing:-0.5px;">Items waiting in your cart</h2>
                            <p style="margin:0 0 28px;color:#888888;font-size:14px;">Don't let your personalised items go to waste</p>
                            <p style="margin:0 0 20px;color:#444444;font-size:16px;line-height:1.7;">Hi <strong>{{customer_name}}</strong>,</p>
                            <p style="margin:0 0 28px;color:#555555;font-size:16px;line-height:1.7;">You left some items in your cart. We have saved them for you — head back to complete your order before they expire.</p>
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin:0 auto 32px;">
                                <tr>
                                    <td style="text-align:center;">
                                        <a href="{{frontend_url}}/cart" style="display:inline-block;background-color:#c4673a;color:#ffffff;padding:18px 40px;text-decoration:none;border-radius:8px;font-weight:700;font-size:16px;letter-spacing:-0.3px;">Return to Cart</a>
                                    </td>
                                </tr>
                            </table>
                            <p style="margin:0;color:#aaaaaa;font-size:14px;line-height:1.6;">If you did not add these items, you can safely ignore this email.</p>
                        </td>
                    </tr>""" + _FOOTER + _WRAPPER_CLOSE,
        "variables": {"customer_name": "string", "frontend_url": "string"},
        "is_active": True,
    },

    # ── 8. AFFILIATE SIGNUP ──────────────────────────────────────────────────
    {
        "name": "affiliate_signup",
        "subject": "Welcome to the SouvenirX Affiliate Program",
        "html_content": _WRAPPER_OPEN + """<tr>
                        <td style="background-color:#c4673a;padding:32px;text-align:center;">
                            <h1 style="margin:0;color:#ffffff;font-size:28px;font-weight:700;letter-spacing:-0.5px;">SouvenirX Affiliates</h1>
                            <p style="margin:8px 0 0;color:#f5d9cc;font-size:14px;letter-spacing:0.5px;">Earn commissions. Grow together.</p>
                        </td>
                    </tr>""" + """
                    <tr>
                        <td style="padding:48px 40px 40px;">
                            <h2 style="margin:0 0 8px;color:#1a1a1a;font-size:26px;font-weight:700;letter-spacing:-0.5px;">You're In the Affiliate Program!</h2>
                            <p style="margin:0 0 28px;color:#888888;font-size:14px;">Start earning commissions on every referral</p>
                            <p style="margin:0 0 20px;color:#444444;font-size:16px;line-height:1.7;">Hi <strong>{{affiliate_name}}</strong>,</p>
                            <p style="margin:0 0 28px;color:#555555;font-size:16px;line-height:1.7;">Congratulations on joining the SouvenirX Affiliate Program. Your application has been approved and your account is now active.</p>

                            <!-- Benefit highlights -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin:0 0 32px;">
                                <tr>
                                    <td style="padding:20px 24px;background-color:#fdf8f5;border:1px solid #f0e4db;border-radius:8px;">
                                        <p style="margin:0 0 12px;color:#1a1a1a;font-size:15px;font-weight:600;">Your Affiliate Benefits</p>
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                            <tr>
                                                <td style="padding:6px 0;color:#555555;font-size:14px;line-height:1.6;vertical-align:top;width:24px;">&#8226;</td>
                                                <td style="padding:6px 0;color:#555555;font-size:14px;line-height:1.6;">Earn a commission on every order placed through your referral link</td>
                                            </tr>
                                            <tr>
                                                <td style="padding:6px 0;color:#555555;font-size:14px;line-height:1.6;vertical-align:top;width:24px;">&#8226;</td>
                                                <td style="padding:6px 0;color:#555555;font-size:14px;line-height:1.6;">Real-time dashboard to track clicks, conversions, and earnings</td>
                                            </tr>
                                            <tr>
                                                <td style="padding:6px 0;color:#555555;font-size:14px;line-height:1.6;vertical-align:top;width:24px;">&#8226;</td>
                                                <td style="padding:6px 0;color:#555555;font-size:14px;line-height:1.6;">Monthly payouts directly to your bank account</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>

                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin:0 auto;">
                                <tr>
                                    <td style="text-align:center;">
                                        <a href="{{frontend_url}}/affiliate" style="display:inline-block;background-color:#c4673a;color:#ffffff;padding:18px 40px;text-decoration:none;border-radius:8px;font-weight:700;font-size:16px;letter-spacing:-0.3px;">Go to Affiliate Dashboard</a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>""" + _FOOTER + _WRAPPER_CLOSE,
        "variables": {"affiliate_name": "string", "frontend_url": "string"},
        "is_active": True,
    },

    # ── 9. PAYOUT NOTIFICATION ───────────────────────────────────────────────
    {
        "name": "payout_notification",
        "subject": "Payout of ₦{{payout_amount}} Processed — SouvenirX Affiliates",
        "html_content": _WRAPPER_OPEN + """<tr>
                        <td style="background-color:#c4673a;padding:32px;text-align:center;">
                            <h1 style="margin:0;color:#ffffff;font-size:28px;font-weight:700;letter-spacing:-0.5px;">SouvenirX Affiliates</h1>
                            <p style="margin:8px 0 0;color:#f5d9cc;font-size:14px;letter-spacing:0.5px;">Earn commissions. Grow together.</p>
                        </td>
                    </tr>""" + """
                    <tr>
                        <td style="padding:48px 40px 40px;">
                            <h2 style="margin:0 0 8px;color:#1a1a1a;font-size:26px;font-weight:700;letter-spacing:-0.5px;">Payout Processed</h2>
                            <p style="margin:0 0 28px;color:#888888;font-size:14px;">Your earnings have been sent to your bank account</p>
                            <p style="margin:0 0 20px;color:#444444;font-size:16px;line-height:1.7;">Hi <strong>{{affiliate_name}}</strong>,</p>
                            <p style="margin:0 0 28px;color:#555555;font-size:16px;line-height:1.7;">Great news — your payout has been processed and is on its way to your bank account.</p>

                            <!-- Payout amount highlight -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin:0 0 32px;background-color:#fdf8f5;border:1px solid #f0e4db;border-radius:8px;">
                                <tr>
                                    <td style="padding:28px 24px;text-align:center;">
                                        <p style="margin:0 0 8px;color:#888888;font-size:12px;text-transform:uppercase;letter-spacing:0.8px;font-weight:600;">Amount Paid Out</p>
                                        <p style="margin:0;color:#c4673a;font-size:36px;font-weight:700;letter-spacing:-1px;">&#8358;{{payout_amount}}</p>
                                    </td>
                                </tr>
                            </table>

                            <p style="margin:0 0 32px;color:#555555;font-size:15px;line-height:1.7;">Bank transfers typically arrive within 1–3 business days. View your full payout history and current earnings balance in your dashboard.</p>
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin:0 auto;">
                                <tr>
                                    <td style="text-align:center;">
                                        <a href="{{frontend_url}}/affiliate" style="display:inline-block;background-color:#c4673a;color:#ffffff;padding:18px 40px;text-decoration:none;border-radius:8px;font-weight:700;font-size:16px;letter-spacing:-0.3px;">View Dashboard</a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>""" + _FOOTER + _WRAPPER_CLOSE,
        "variables": {"affiliate_name": "string", "payout_amount": "string", "frontend_url": "string"},
        "is_active": True,
    },

    # ── 10. BANK TRANSFER ADMIN NOTIFICATION ─────────────────────────────────
    {
        "name": "bank_transfer_admin_notification",
        "subject": "Action Required — Bank Transfer Proof for {{order_number}}",
        "html_content": _WRAPPER_OPEN + """<tr>
                        <td style="background-color:#1a1a1a;padding:32px;text-align:center;">
                            <h1 style="margin:0;color:#ffffff;font-size:28px;font-weight:700;letter-spacing:-0.5px;">SouvenirX Admin</h1>
                            <p style="margin:8px 0 0;color:#aaaaaa;font-size:14px;letter-spacing:0.5px;">Internal Notification</p>
                        </td>
                    </tr>""" + """
                    <tr>
                        <td style="padding:48px 40px 40px;">
                            <h2 style="margin:0 0 8px;color:#1a1a1a;font-size:26px;font-weight:700;letter-spacing:-0.5px;">Bank Transfer Proof Uploaded</h2>
                            <p style="margin:0 0 28px;color:#888888;font-size:14px;">Review and verify to release the order into production</p>

                            <!-- Order details box -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin:0 0 28px;background-color:#fdf8f5;border:1px solid #f0e4db;border-radius:8px;">
                                <tr>
                                    <td style="padding:20px 24px;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                            <tr>
                                                <td style="color:#888888;font-size:12px;text-transform:uppercase;letter-spacing:0.8px;font-weight:600;padding-bottom:6px;">Order Reference</td>
                                                <td style="color:#888888;font-size:12px;text-transform:uppercase;letter-spacing:0.8px;font-weight:600;padding-bottom:6px;text-align:right;">Customer</td>
                                            </tr>
                                            <tr>
                                                <td style="color:#c4673a;font-size:20px;font-weight:700;letter-spacing:-0.5px;">{{order_number}}</td>
                                                <td style="color:#1a1a1a;font-size:16px;font-weight:600;text-align:right;">{{customer_name}}</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>

                            <p style="margin:0 0 28px;color:#555555;font-size:16px;line-height:1.7;">The customer has uploaded proof of bank transfer. Please review the proof in the admin dashboard and either approve or reject the payment.</p>

                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin:0 auto;">
                                <tr>
                                    <td style="text-align:center;">
                                        <a href="{{admin_url}}/orders/{{order_number}}" style="display:inline-block;background-color:#1a1a1a;color:#ffffff;padding:18px 40px;text-decoration:none;border-radius:8px;font-weight:700;font-size:16px;letter-spacing:-0.3px;">Review in Admin Dashboard</a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>""" + _FOOTER + _WRAPPER_CLOSE,
        "variables": {
            "order_number": "string",
            "customer_name": "string",
            "admin_url": "string",
        },
        "is_active": True,
    },

    # ── PASSWORD RESET BY ADMIN ──────────────────────────────────────────────
    {
        "name": "password_reset_by_admin",
        "subject": "Your Password Has Been Reset — SouvenirX",
        "html_content": _WRAPPER_OPEN + _HEADER + """
                    <tr>
                        <td style="padding:48px 40px 40px;">
                            <h2 style="margin:0 0 8px;color:#1a1a1a;font-size:26px;font-weight:700;letter-spacing:-0.5px;">Password Reset Notification</h2>
                            <p style="margin:0 0 28px;color:#888888;font-size:14px;">Your account password has been changed</p>
                            <p style="margin:0 0 20px;color:#444444;font-size:16px;line-height:1.7;">Hi <strong>{{customer_name}}</strong>,</p>
                            <p style="margin:0 0 28px;color:#555555;font-size:16px;line-height:1.7;">Your password has been reset by our support team (<strong>{{admin_name}}</strong>). You can now log in with your new password.</p>
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color:#fff3e0;border:1px solid #ffe0b2;border-radius:8px;margin:0 0 28px;">
                                <tr>
                                    <td style="padding:16px 20px;">
                                        <p style="margin:0 0 6px;color:#e65100;font-size:13px;font-weight:600;">⚠️ Security Notice</p>
                                        <p style="margin:0;color:#666666;font-size:13px;line-height:1.6;">If you did not request this password reset, please contact our support team immediately and change your password.</p>
                                    </td>
                                </tr>
                            </table>
                            <p style="margin:0 0 20px;color:#555555;font-size:16px;line-height:1.7;">For your security, we recommend:</p>
                            <ul style="margin:0 0 28px;padding-left:20px;color:#555555;font-size:16px;line-height:1.7;">
                                <li style="margin-bottom:8px;">Change your password to something memorable and secure</li>
                                <li style="margin-bottom:8px;">Use a unique password not used on other websites</li>
                                <li>Enable two-factor authentication if available</li>
                            </ul>
                        </td>
                    </tr>""" + _FOOTER + _WRAPPER_CLOSE,
        "variables": {"customer_name": "string", "admin_name": "string"},
        "is_active": True,
    },
]
