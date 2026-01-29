"""
Email notification service using Resend API
Much simpler and more reliable than SMTP
"""
import resend
from typing import Dict, Any
from datetime import datetime
from loguru import logger
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings


class EmailService:
    """Service for sending email notifications using Resend"""
    
    def __init__(self):
        """Initialize Resend email service"""
        self.resend_api_key = settings.RESEND_API_KEY if hasattr(settings, 'RESEND_API_KEY') else None
        self.recipient_email = settings.EMAIL_RECIPIENT
        # For testing, use onboarding@resend.dev (Resend's test domain)
        self.sender_email = "onboarding@resend.dev"
        
        # Check if email is configured
        self.enabled = bool(self.resend_api_key)
        
        if not self.enabled:
            logger.warning("⚠️ Email notifications disabled - RESEND_API_KEY not configured in .env")
        else:
            resend.api_key = self.resend_api_key
            logger.info(f"📧 Resend email service initialized - will send from {self.sender_email} to {self.recipient_email}")
    
    async def send_critical_alert(
        self,
        alert_data: Dict[str, Any]
    ) -> bool:
        """
        Send critical alert email using the exact same data structure as the frontend
        
        Args:
            alert_data: The complete alert data dict sent to frontend
            
        Returns:
            bool: True if email sent successfully
        """
        if not self.enabled:
            logger.debug("Email service not enabled, skipping critical alert email")
            return False
        
        try:
            # Extract data from alert (same structure as frontend receives)
            title = alert_data.get('title', 'Critical Alert')
            message = alert_data.get('message', '')
            camera_id = alert_data.get('camera_id', 0)
            timestamp = alert_data.get('timestamp', datetime.now().isoformat())
            severity = alert_data.get('severity', 'CRITICAL')
            frame_base64 = alert_data.get('frame_base64')
            
            # Parse timestamp for display
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_str = dt.strftime('%B %d, %Y at %I:%M %p')
            except:
                time_str = datetime.now().strftime('%B %d, %Y at %I:%M %p')
            
            # Build HTML body - clean and simple, matching the alert tab display
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; background: #f5f5f5; margin: 0; padding: 20px; }}
                    .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
                    .header {{ background: {'#dc3545' if severity == 'CRITICAL' else '#ffc107' if severity == 'WARNING' else '#17a2b8'}; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
                    .header h1 {{ margin: 0; font-size: 20px; font-weight: 600; }}
                    .content {{ padding: 24px; }}
                    .message {{ font-size: 15px; line-height: 1.7; color: #333; white-space: pre-wrap; margin: 0; }}
                    .meta {{ margin-top: 24px; padding-top: 16px; border-top: 1px solid #e0e0e0; color: #666; font-size: 13px; }}
                    .meta-item {{ margin: 4px 0; }}
                    .footer {{ padding: 16px 24px; background: #f8f9fa; border-radius: 0 0 8px 8px; text-align: center; color: #666; font-size: 12px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>{title}</h1>
                    </div>
                    <div class="content">
                        <div class="message">{message}</div>
                        <div class="meta">
                            <div class="meta-item">📹 <strong>Camera:</strong> {camera_id}</div>
                            <div class="meta-item">🕐 <strong>Time:</strong> {time_str}</div>
                            <div class="meta-item">⚠️ <strong>Severity:</strong> {severity}</div>
                        </div>
                    </div>
                    <div class="footer">
                        SentinTinel AI Surveillance System
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Send email via Resend
            params = {
                "from": self.sender_email,
                "to": [self.recipient_email],
                "subject": f"🚨 {severity}: {title}",
                "html": html_body
            }
            
            response = resend.Emails.send(params)
            
            logger.info(f"✅ Critical alert email sent to {self.recipient_email}: {title}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send critical alert email: {e}")
            return False
    
    async def send_summary_email(
        self,
        alert_data: Dict[str, Any]
    ) -> bool:
        """
        Send 2-minute summary email using the exact same data structure as the frontend
        
        Args:
            alert_data: The complete alert data dict sent to frontend
            
        Returns:
            bool: True if email sent successfully
        """
        if not self.enabled:
            logger.debug("Email service not enabled, skipping summary email")
            return False
        
        try:
            # Extract data from alert (same structure as frontend receives)
            title = alert_data.get('title', 'Activity Summary')
            message = alert_data.get('message', '')
            timestamp = alert_data.get('timestamp', datetime.now().isoformat())
            severity = alert_data.get('severity', 'INFO')
            
            # Parse timestamp for display
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_str = dt.strftime('%B %d, %Y at %I:%M %p')
            except:
                time_str = datetime.now().strftime('%B %d, %Y at %I:%M %p')
            
            # Build HTML body - clean and simple, matching the alert tab display
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; background: #f5f5f5; margin: 0; padding: 20px; }}
                    .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
                    .header {{ background: #007bff; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
                    .header h1 {{ margin: 0; font-size: 20px; font-weight: 600; }}
                    .content {{ padding: 24px; }}
                    .message {{ font-size: 15px; line-height: 1.7; color: #333; white-space: pre-wrap; margin: 0; }}
                    .meta {{ margin-top: 24px; padding-top: 16px; border-top: 1px solid #e0e0e0; color: #666; font-size: 13px; }}
                    .meta-item {{ margin: 4px 0; }}
                    .footer {{ padding: 16px 24px; background: #f8f9fa; border-radius: 0 0 8px 8px; text-align: center; color: #666; font-size: 12px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>{title}</h1>
                    </div>
                    <div class="content">
                        <div class="message">{message}</div>
                        <div class="meta">
                            <div class="meta-item">🕐 <strong>Generated:</strong> {time_str}</div>
                            <div class="meta-item">📊 <strong>Type:</strong> 2-Minute Activity Summary</div>
                        </div>
                    </div>
                    <div class="footer">
                        SentinTinel AI Surveillance System
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Send email via Resend
            params = {
                "from": self.sender_email,
                "to": [self.recipient_email],
                "subject": f"📊 {title}",
                "html": html_body
            }
            
            response = resend.Emails.send(params)
            
            logger.info(f"✅ Summary email sent to {self.recipient_email}: {title}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send summary email: {e}")
            return False


# Global email service instance
email_service = EmailService()

