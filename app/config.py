from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://souvenirx:souvenirx_secret@localhost:5432/souvenirx"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_ssl_ca_certs: str = ""  # Path to CA certificate file for SSL verification
    redis_ssl_certfile: str = ""  # Path to client certificate file
    redis_ssl_keyfile: str = ""  # Path to client key file
    # Default "none" so self-signed Redis certificates (e.g. Coolify-provisioned
    # Redis on a non-standard port) work without extra env-var configuration.
    # Set to "required" + REDIS_SSL_CA_CERTS when using a CA-signed cert.
    redis_ssl_cert_reqs: str = "none"  # "none", "optional", or "required"

    # JWT
    jwt_secret: str = "change-me-to-a-random-secret-key"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Paystack
    paystack_secret_key: str = ""
    paystack_public_key: str = ""

    # Flutterwave
    flutterwave_secret_key: str = ""
    flutterwave_public_key: str = ""
    # Set this in Flutterwave Dashboard > API Settings > Webhooks as the "Verification Hash"
    flutterwave_webhook_secret: str = ""

    # Email
    resend_api_key: str = ""
    email_from: str = "SouvenirX <noreply@souvenirx.com>"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    email_provider: str = "resend"  # "resend" or "smtp"

    # SMS (Termii)
    termii_api_key: str = ""
    termii_sender_id: str = ""

    # App
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"
    upload_dir: str = "/app/uploads"
    # Admin notifications — defaults to email_from if not set
    admin_email: str = ""
    admin_url: str = ""  # e.g. https://admin.souvenir-x.com

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""

    # Firebase / FCM Push Notifications
    firebase_credentials_path: str = ""  # Path to firebase-adminsdk JSON file

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
