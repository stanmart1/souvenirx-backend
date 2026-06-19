"""Email service supporting both Resend and SMTP with template system."""
import resend
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.multipart import MIMEMultipart as Multipart
from app.config import settings

if settings.resend_api_key:
    resend.api_key = settings.resend_api_key


async def send_email(to: str, subject: str, html: str) -> bool:
    """Send email using configured provider (Resend or SMTP)."""
    if settings.email_provider == "smtp":
        return await send_email_smtp(to, subject, html)
    else:
        return await send_email_resend(to, subject, html)


async def send_email_resend(to: str, subject: str, html: str) -> bool:
    """Send email using Resend API."""
    if not settings.resend_api_key:
        print(f"[EMAIL MOCK] To: {to}, Subject: {subject}")
        return True

    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": [to],
            "subject": subject,
            "html": html,
        })
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False


async def send_email_smtp(to: str, subject: str, html: str) -> bool:
    """Send email using SMTP."""
    if not settings.smtp_host or not settings.smtp_username:
        print(f"[EMAIL MOCK] To: {to}, Subject: {subject}")
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.email_from
        msg["To"] = to
        
        # Attach HTML version
        html_part = MIMEText(html, "html")
        msg.attach(html_part)
        
        # Connect to SMTP server
        if settings.smtp_use_tls:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port)
            server.starttls()
        else:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port)
        
        server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False


async def send_templated_email(template_name: str, to: str, variables: dict, db=None) -> bool:
    """Send email using a template from the database."""
    if db is None:
        from app.database import get_db
        db_gen = get_db()
        db = await db_gen.__anext__()
    
    from sqlalchemy import select
    from app.models.settings import EmailTemplate
    
    result = await db.execute(select(EmailTemplate).where(EmailTemplate.name == template_name, EmailTemplate.is_active == True))
    template = result.scalar_one_or_none()
    
    if not template:
        print(f"[EMAIL ERROR] Template not found: {template_name}")
        return False
    
    # Replace variables in subject and content
    subject = template.subject
    html_content = template.html_content
    
    for key, value in variables.items():
        subject = subject.replace(f"{{{{{key}}}}}", str(value))
        html_content = html_content.replace(f"{{{{{key}}}}}", str(value))
    
    return await send_email(to, subject, html_content)


async def send_order_confirmation(to: str, order_number: str, customer_name: str, total: int, items: list, db=None):
    """Send order confirmation email using template."""
    from app.config import settings as cfg

    # Build items HTML table rows
    rows = "".join(
        f'<tr>'
        f'<td style="padding:10px 0;color:#333333;font-size:14px;border-bottom:1px solid #f0e4db;">{item.get("name", "Item")}</td>'
        f'<td style="padding:10px 0;color:#555555;font-size:14px;text-align:center;border-bottom:1px solid #f0e4db;">x{item.get("qty", 1)}</td>'
        f'<td style="padding:10px 0;color:#333333;font-size:14px;text-align:right;border-bottom:1px solid #f0e4db;">&#8358;{int(item.get("unitPrice", 0)):,}</td>'
        f'</tr>'
        for item in (items or [])
    )
    items_html = (
        f'<table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin:0 0 8px;">'
        f'<tr>'
        f'<th style="padding:8px 0;color:#888888;font-size:12px;text-transform:uppercase;letter-spacing:0.8px;font-weight:600;text-align:left;border-bottom:2px solid #f0e4db;">Product</th>'
        f'<th style="padding:8px 0;color:#888888;font-size:12px;text-transform:uppercase;letter-spacing:0.8px;font-weight:600;text-align:center;border-bottom:2px solid #f0e4db;">Qty</th>'
        f'<th style="padding:8px 0;color:#888888;font-size:12px;text-transform:uppercase;letter-spacing:0.8px;font-weight:600;text-align:right;border-bottom:2px solid #f0e4db;">Price</th>'
        f'</tr>'
        f'{rows}'
        f'</table>'
    ) if items else "<p style='color:#888888;font-size:14px;'>Order items are available in your dashboard.</p>"

    variables = {
        "customer_name": customer_name,
        "order_number": order_number,
        "total_formatted": f"{int(total):,}",
        "items_html": items_html,
        "frontend_url": cfg.frontend_url,
    }
    await send_templated_email("order_confirmation", to, variables, db)


# Status metadata used by send_order_status_update
_ORDER_STATUS_META = {
    "in_production":    ("In Production",    "Your order is now being produced by our team.", "#e6a817"),
    "shipped":          ("Shipped",          "Your order has been dispatched and is on its way to you.", "#2d8a4e"),
    "delivered":        ("Delivered",        "Your order has been delivered. We hope you love it!", "#2d8a4e"),
    "payment_rejected": ("Payment Rejected", "Unfortunately we could not verify your bank transfer. Please contact support or re-upload your proof of payment.", "#c0392b"),
    "cancelled":        ("Cancelled",        "Your order has been cancelled. If this was unexpected, please contact our support team.", "#c0392b"),
    "pending":          ("Pending",          "Your order is pending payment confirmation.", "#888888"),
    "processing":       ("Processing",       "Your order has been received and is being reviewed.", "#2980b9"),
}


async def send_order_status_update(to: str, order_number: str, customer_name: str, new_status: str, db=None):
    """Send order status update email using the order_status_update template."""
    from app.config import settings as cfg

    label, message, color = _ORDER_STATUS_META.get(
        new_status,
        (new_status.replace("_", " ").title(), f"Your order status has been updated to {new_status}.", "#888888"),
    )
    variables = {
        "customer_name": customer_name,
        "order_number": order_number,
        "status_label": label,
        "status_message": message,
        "status_color": color,
        "frontend_url": cfg.frontend_url,
    }
    await send_templated_email("order_status_update", to, variables, db)


async def send_bank_transfer_notification(order_number: str, customer_name: str, db=None):
    """Send bank transfer notification to admin using template."""
    from app.config import settings as cfg
    # Use dedicated admin_email env var if set, otherwise fall back to the sender address
    admin_email = cfg.admin_email or cfg.email_from
    variables = {
        "order_number": order_number,
        "customer_name": customer_name,
        "admin_url": cfg.admin_url or cfg.frontend_url,
    }
    await send_templated_email("bank_transfer_admin_notification", admin_email, variables, db)


async def send_welcome_email(to: str, name: str, db=None):
    """Send welcome email using template."""
    from app.config import settings as cfg
    variables = {
        "customer_name": name,
        "frontend_url": cfg.frontend_url,
    }
    await send_templated_email("welcome", to, variables, db)


async def send_verification_email(to: str, name: str, token: str, db=None, otp: str | None = None):
    """Send email verification link (and optional 6-digit OTP for mobile) using template."""
    from app.config import settings as cfg
    verification_url = f"{cfg.frontend_url}/verify-email?token={token}"
    if otp:
        otp_block = (
            '<table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" '
            'style="background-color:#fff5ee;border:1px solid #f0e4db;border-radius:8px;margin:0 0 28px;">'
            '<tr><td style="padding:20px;text-align:center;">'
            '<p style="margin:0 0 10px;color:#888888;font-size:12px;text-transform:uppercase;'
            'letter-spacing:0.8px;font-weight:600;">Mobile app verification code</p>'
            f'<p style="margin:0;color:#c4673a;font-size:32px;font-weight:800;letter-spacing:8px;">{otp}</p>'
            '<p style="margin:10px 0 0;color:#888888;font-size:12px;">Enter this 6-digit code in the SouvenirX mobile app.</p>'
            '</td></tr></table>'
        )
    else:
        otp_block = ""
    variables = {
        "customer_name": name,
        "verification_url": verification_url,
        "frontend_url": cfg.frontend_url,
        "otp_block": otp_block,
    }
    await send_templated_email("email_verification", to, variables, db)


async def send_password_reset_email(to: str, name: str, token: str, db=None):
    """Send password reset email using template."""
    from app.config import settings as cfg
    reset_url = f"{cfg.frontend_url}/reset-password?token={token}"
    variables = {
        "customer_name": name,
        "reset_url": reset_url,
    }
    await send_templated_email("password_reset", to, variables, db)


async def send_cart_recovery_email(to: str, customer_name: str, db=None):
    """Send cart recovery email using template."""
    from app.config import settings as cfg
    variables = {
        "customer_name": customer_name,
        "frontend_url": cfg.frontend_url,
    }
    await send_templated_email("cart_recovery", to, variables, db)


async def send_affiliate_signup_email(to: str, affiliate_name: str, db=None):
    """Send affiliate signup email using template."""
    from app.config import settings as cfg
    variables = {
        "affiliate_name": affiliate_name,
        "frontend_url": cfg.frontend_url,
    }
    await send_templated_email("affiliate_signup", to, variables, db)


async def send_payout_notification_email(to: str, affiliate_name: str, payout_amount: int, db=None):
    """Send payout notification email using template."""
    from app.config import settings as cfg
    variables = {
        "affiliate_name": affiliate_name,
        "payout_amount": f"{payout_amount:,}",
        "frontend_url": cfg.frontend_url,
    }
    await send_templated_email("payout_notification", to, variables, db)
