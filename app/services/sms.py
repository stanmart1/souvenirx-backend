"""SMS service using Termii with template support."""
import httpx
from app.config import settings


async def send_sms(to: str, message: str) -> bool:
    """Send SMS using Termii API."""
    if not settings.termii_api_key:
        print(f"[SMS MOCK] To: {to}, Message: {message}")
        return True

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.ng.termii.com/api/sms/send",
                headers={
                    "Content-Type": "application/json",
                },
                json={
                    "to": to,
                    "from": settings.termii_sender_id or "SouvenirX",
                    "sms": message,
                    "type": "plain",
                    "channel": "dnd",
                    "api_key": settings.termii_api_key,
                },
                timeout=10.0,
            )
            response.raise_for_status()
            return True
    except Exception as e:
        print(f"[SMS ERROR] {e}")
        return False


async def send_templated_sms(template_name: str, to: str, variables: dict, db=None) -> bool:
    """Send SMS using a template from the database."""
    if db is None:
        from app.database import get_db
        db_gen = get_db()
        db = await db_gen.__anext__()
    
    from sqlalchemy import select
    from app.models.settings import SmsTemplate
    
    result = await db.execute(select(SmsTemplate).where(SmsTemplate.name == template_name, SmsTemplate.is_active == True))
    template = result.scalar_one_or_none()
    
    if not template:
        print(f"[SMS ERROR] Template not found: {template_name}")
        return False
    
    # Replace variables in the template
    message = template.template
    for key, value in variables.items():
        message = message.replace(f"{{{key}}}", str(value))
    
    return await send_sms(to, message)


async def send_order_sms(to: str, order_number: str, customer_name: str, status: str, db=None):
    """Send order status SMS using template."""
    from app.config import settings as cfg
    variables = {
        "customer_name": customer_name,
        "order_number": order_number,
        "status": status,
        "frontend_url": cfg.frontend_url,
    }
    await send_templated_sms("order_status_update", to, variables, db)


async def send_cart_recovery_sms(to: str, customer_name: str, db=None):
    """Send cart recovery SMS using template."""
    from app.config import settings as cfg
    variables = {
        "customer_name": customer_name,
        "frontend_url": cfg.frontend_url,
    }
    await send_templated_sms("cart_recovery", to, variables, db)
