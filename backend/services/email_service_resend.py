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
        self.sender_email = "SentinTinel <onboarding@resend.dev>"  # Free tier default
        self.recipient_email = settings.EMAIL_RECIPIENT
        
        # Check if email is configured
        self.enabled = bool(self.resend_api_key)
        
        if not self.enabled:
            logger.warning("⚠️ Email notifications disabled - RESEND_API_KEY not configured in .env")
        else:
            resend.api_key = self.resend_api_key
            logger.info(f"📧 Resend email service initialized - will send to {self.recipient_email}")
    
    async def send_critical_alert(
        self,
        alert_data: Dict[str, Any]
    ) -> bool:
        """
        Send critical alert email using the exact same format as the frontend UI

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
            significance = alert_data.get('significance')
            query_confidence = alert_data.get('query_confidence')
            detected_objects = alert_data.get('detected_objects', [])
            frame_base64 = alert_data.get('frame_base64')

            # Use query_confidence if available, otherwise use significance
            confidence = query_confidence if query_confidence is not None else significance

            # Parse timestamp for display
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_str = dt.strftime('%B %d, %Y at %I:%M %p')
            except:
                time_str = datetime.now().strftime('%B %d, %Y at %I:%M %p')

            # Determine severity emoji and color
            severity_emoji = '🚨' if severity == 'CRITICAL' else '⚠️' if severity == 'WARNING' else 'ℹ️'
            severity_color = '#dc3545' if severity == 'CRITICAL' else '#fd7e14' if severity == 'WARNING' else '#17a2b8'

            # Build detected objects HTML badges
            detected_objects_html = ''
            if detected_objects:
                badges = [f'<span style="display: inline-block; padding: 4px 12px; background: rgba(34, 197, 94, 0.2); color: #22c55e; border-radius: 12px; font-size: 12px; margin: 4px 4px 4px 0; border: 1px solid rgba(34, 197, 94, 0.3);">{obj}</span>'
                         for obj in detected_objects]
                detected_objects_html = f'<div style="margin-top: 16px;">{" ".join(badges)}</div>'

            # Build image HTML if frame_base64 is available
            image_html = ''
            if frame_base64:
                image_html = f"""
                <div style="margin-top: 20px; border-radius: 8px; overflow: hidden; border: 1px solid #374151; background: #111827;">
                    <img src="data:image/jpeg;base64,{frame_base64}" alt="Event Frame" style="width: 100%; max-height: 400px; object-fit: contain; display: block;" />
                    <div style="padding: 8px; background: #1f2937; text-align: center; font-size: 12px; color: #9ca3af;">
                        📷 Supporting Evidence
                    </div>
                </div>
                """

            # Build HTML body - exact match to UI display format
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #e5e7eb; background: #0f172a; margin: 0; padding: 20px; }}
                    .container {{ max-width: 600px; margin: 0 auto; background: #1e293b; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); border-left: 4px solid {severity_color}; }}
                    .header {{ padding: 20px 24px; border-bottom: 1px solid #334155; }}
                    .severity-badge {{ display: inline-block; padding: 4px 12px; background: {severity_color}33; color: {severity_color}; border-radius: 4px; font-size: 12px; font-weight: 600; margin-bottom: 8px; }}
                    .meta-badges {{ display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-bottom: 12px; }}
                    .confidence-badge {{ display: inline-block; padding: 4px 10px; background: rgba(59, 130, 246, 0.3); color: #60a5fa; border-radius: 4px; font-size: 11px; }}
                    .camera-badge {{ display: inline-block; font-size: 12px; color: #9ca3af; }}
                    .title {{ margin: 0; font-size: 18px; font-weight: 600; color: #f3f4f6; }}
                    .content {{ padding: 20px 24px; }}
                    .message {{ font-size: 14px; line-height: 1.7; color: #d1d5db; white-space: pre-line; margin: 0; }}
                    .meta {{ margin-top: 20px; padding-top: 16px; border-top: 1px solid #334155; color: #9ca3af; font-size: 13px; }}
                    .meta-item {{ margin: 6px 0; }}
                    .footer {{ padding: 16px 24px; background: #0f172a; border-radius: 0 0 8px 8px; text-align: center; color: #6b7280; font-size: 12px; border-top: 1px solid #334155; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <div class="meta-badges">
                            <span class="severity-badge">{severity_emoji} {severity}</span>
                            <span class="camera-badge">Camera {camera_id}</span>
                            {f'<span class="confidence-badge">{int(confidence)}% confidence</span>' if confidence is not None else ''}
                        </div>
                        <h1 class="title">{title}</h1>
                    </div>
                    <div class="content">
                        <div class="message">{message}</div>
                        {detected_objects_html}
                        {image_html}
                        <div class="meta">
                            <div class="meta-item">🕐 <strong>Time:</strong> {time_str}</div>
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
                "subject": f"{severity_emoji} {severity}: {title}",
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
        Send 2-minute summary email using the exact same format as the frontend UI

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
            camera_id = alert_data.get('camera_id')
            significance = alert_data.get('significance')
            detected_objects = alert_data.get('detected_objects', [])
            frame_base64 = alert_data.get('frame_base64')

            # Parse timestamp for display
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_str = dt.strftime('%B %d, %Y at %I:%M %p')
            except:
                time_str = datetime.now().strftime('%B %d, %Y at %I:%M %p')

            # Determine severity emoji and color (summaries are typically INFO/WARNING)
            severity_emoji = '📊' if severity == 'INFO' else '⚠️' if severity == 'WARNING' else '🚨'
            severity_color = '#17a2b8' if severity == 'INFO' else '#fd7e14' if severity == 'WARNING' else '#dc3545'

            # Build detected objects HTML badges
            detected_objects_html = ''
            if detected_objects:
                badges = [f'<span style="display: inline-block; padding: 4px 12px; background: rgba(34, 197, 94, 0.2); color: #22c55e; border-radius: 12px; font-size: 12px; margin: 4px 4px 4px 0; border: 1px solid rgba(34, 197, 94, 0.3);">{obj}</span>'
                         for obj in detected_objects]
                detected_objects_html = f'<div style="margin-top: 16px;">{" ".join(badges)}</div>'

            # Build image HTML if frame_base64 is available
            image_html = ''
            if frame_base64:
                image_html = f"""
                <div style="margin-top: 20px; border-radius: 8px; overflow: hidden; border: 1px solid #374151; background: #111827;">
                    <img src="data:image/jpeg;base64,{frame_base64}" alt="Event Frame" style="width: 100%; max-height: 400px; object-fit: contain; display: block;" />
                    <div style="padding: 8px; background: #1f2937; text-align: center; font-size: 12px; color: #9ca3af;">
                        📷 Most Significant Frame
                    </div>
                </div>
                """

            # Build camera and confidence badges
            extra_badges = ''
            if camera_id is not None:
                extra_badges += f'<span class="camera-badge">Camera {camera_id}</span>'
            if significance is not None:
                extra_badges += f'<span class="confidence-badge">{int(significance)}% confidence</span>'

            # Build HTML body - exact match to UI display format
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #e5e7eb; background: #0f172a; margin: 0; padding: 20px; }}
                    .container {{ max-width: 600px; margin: 0 auto; background: #1e293b; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); border-left: 4px solid {severity_color}; }}
                    .header {{ padding: 20px 24px; border-bottom: 1px solid #334155; }}
                    .severity-badge {{ display: inline-block; padding: 4px 12px; background: {severity_color}33; color: {severity_color}; border-radius: 4px; font-size: 12px; font-weight: 600; margin-bottom: 8px; }}
                    .meta-badges {{ display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-bottom: 12px; }}
                    .confidence-badge {{ display: inline-block; padding: 4px 10px; background: rgba(59, 130, 246, 0.3); color: #60a5fa; border-radius: 4px; font-size: 11px; margin-left: 8px; }}
                    .camera-badge {{ display: inline-block; font-size: 12px; color: #9ca3af; }}
                    .title {{ margin: 0; font-size: 18px; font-weight: 600; color: #f3f4f6; }}
                    .content {{ padding: 20px 24px; }}
                    .message {{ font-size: 14px; line-height: 1.7; color: #d1d5db; white-space: pre-line; margin: 0; }}
                    .meta {{ margin-top: 20px; padding-top: 16px; border-top: 1px solid #334155; color: #9ca3af; font-size: 13px; }}
                    .meta-item {{ margin: 6px 0; }}
                    .footer {{ padding: 16px 24px; background: #0f172a; border-radius: 0 0 8px 8px; text-align: center; color: #6b7280; font-size: 12px; border-top: 1px solid #334155; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <div class="meta-badges">
                            <span class="severity-badge">{severity_emoji} Activity Summary</span>
                            {extra_badges}
                        </div>
                        <h1 class="title">{title}</h1>
                    </div>
                    <div class="content">
                        <div class="message">{message}</div>
                        {detected_objects_html}
                        {image_html}
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
                "subject": f"{severity_emoji} {title}",
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

