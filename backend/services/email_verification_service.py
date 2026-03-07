"""
Email verification service using Gmail SMTP
"""
import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from loguru import logger
from config import settings
from typing import Optional


async def send_verification_email(email: str, verification_token: str) -> bool:
    """
    Send email verification link to user via Gmail SMTP
    """
    try:
        verification_url = f"http://localhost:3000/verify-email?token={verification_token}"

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
                                  color: white;
                                  padding: 15px 40px;
                                  text-decoration: none;
                                  border-radius: 5px;
                                  display: inline-block;
                                  font-weight: bold;">
                            Verify Email Address
                        </a>
                    </div>
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

        message = MIMEMultipart("alternative")
        message["Subject"] = "Verify your ThirdEye account"
        message["From"] = settings.GMAIL_USER
        message["To"] = email
        message.attach(MIMEText(html, "html"))

        await aiosmtplib.send(
            message,
            hostname="smtp.gmail.com",
            port=587,
            start_tls=True,
            username=settings.GMAIL_USER,
            password=settings.GMAIL_APP_PASSWORD,
        )

        logger.info(f"Verification email sent to {email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send verification email to {email}: {str(e)}")
        return False


async def send_welcome_email(email: str, full_name: Optional[str] = None) -> bool:
    """
    Send welcome email after successful verification via Gmail SMTP
    """
    try:
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
                        <a href="http://localhost:3000"
                           style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                                  color: white;
                                  padding: 15px 40px;
                                  text-decoration: none;
                                  border-radius: 5px;
                                  display: inline-block;
                                  font-weight: bold;">
                            Go to Dashboard
                        </a>
                    </div>
                </div>
            </body>
        </html>
        """

        message = MIMEMultipart("alternative")
        message["Subject"] = "Welcome to ThirdEye - Your Account is Ready!"
        message["From"] = settings.GMAIL_USER
        message["To"] = email
        message.attach(MIMEText(html, "html"))

        await aiosmtplib.send(
            message,
            hostname="smtp.gmail.com",
            port=587,
            start_tls=True,
            username=settings.GMAIL_USER,
            password=settings.GMAIL_APP_PASSWORD,
        )

        logger.info(f"Welcome email sent to {email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send welcome email to {email}: {str(e)}")
        return False
