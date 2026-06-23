"""
Email verification service (Gmail SMTP)
"""
import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from loguru import logger
from config import settings
from typing import Optional


def _gmail_configured() -> bool:
    return bool(settings.GMAIL_USER and settings.GMAIL_APP_PASSWORD)


async def _send(subject: str, recipient: str, html: str) -> bool:
    if not _gmail_configured():
        logger.error(
            "Gmail SMTP not configured — set GMAIL_USER and GMAIL_APP_PASSWORD "
            "in backend/.env (App Password from myaccount.google.com/apppasswords)"
        )
        return False

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = settings.GMAIL_USER
    message["To"] = recipient
    message.attach(MIMEText(html, "html"))

    try:
        await aiosmtplib.send(
            message,
            hostname="smtp.gmail.com",
            port=587,
            start_tls=True,
            username=settings.GMAIL_USER,
            password=settings.GMAIL_APP_PASSWORD,
        )
        return True
    except Exception as e:
        logger.error(f"Gmail SMTP send failed to {recipient}: {e}")
        return False


async def send_verification_email(email: str, verification_token: str) -> bool:
    """Send email-verification link via Gmail SMTP."""
    verification_url = f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"

    html = f"""
    <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0;">Welcome to ThirdEye</h1>
            </div>
            <div style="background: #f7f7f7; padding: 30px; border-radius: 0 0 10px 10px;">
                <h2 style="color: #333;">Verify Your Email Address</h2>
                <p style="color: #666; line-height: 1.6;">
                    Thank you for signing up for ThirdEye! Please verify your email address to complete registration.
                </p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verification_url}"
                       style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                              color: white; padding: 15px 40px; text-decoration: none;
                              border-radius: 5px; display: inline-block; font-weight: bold;">
                        Verify Email Address
                    </a>
                </div>
                <p style="color: #999; font-size: 12px; text-align: center;">
                    Or paste this link into your browser: <br>
                    <span style="color: #667eea;">{verification_url}</span>
                </p>
                <p style="color: #999; font-size: 12px; text-align: center;">
                    This link will expire in 24 hours.
                </p>
                <p style="color: #999; font-size: 12px; text-align: center;">
                    If you didn't create this account, you can safely ignore this email.
                </p>
            </div>
        </body>
    </html>
    """

    ok = await _send("Verify your ThirdEye account", email, html)
    if ok:
        logger.info(f"Verification email sent to {email}")
    return ok


async def send_welcome_email(email: str, full_name: Optional[str] = None) -> bool:
    """Send welcome email after successful verification via Gmail SMTP."""
    greeting = f"Hi {full_name}," if full_name else "Hi there,"

    html = f"""
    <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0;">You're All Set!</h1>
            </div>
            <div style="background: #f7f7f7; padding: 30px; border-radius: 0 0 10px 10px;">
                <p style="color: #333; font-size: 16px;">{greeting}</p>
                <p style="color: #666; line-height: 1.6;">
                    Your ThirdEye account has been verified! You now have full access to the AI-powered surveillance platform.
                </p>
                <h3 style="color: #333;">What's Next?</h3>
                <ul style="color: #666; line-height: 1.8;">
                    <li>Connect your cameras to start monitoring</li>
                    <li>Configure alert thresholds</li>
                    <li>Explore AI-powered scene analysis</li>
                </ul>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{settings.FRONTEND_URL}"
                       style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                              color: white; padding: 15px 40px; text-decoration: none;
                              border-radius: 5px; display: inline-block; font-weight: bold;">
                        Go to Dashboard
                    </a>
                </div>
            </div>
        </body>
    </html>
    """

    ok = await _send("Welcome to ThirdEye — Your Account is Ready!", email, html)
    if ok:
        logger.info(f"Welcome email sent to {email}")
    return ok
