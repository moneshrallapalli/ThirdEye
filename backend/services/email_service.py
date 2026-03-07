"""
Email notification service using Gmail SMTP
"""
import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from typing import Dict, Any
from datetime import datetime
from loguru import logger
import sys
import os
import base64

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings


class EmailService:
    """Service for sending email notifications using Gmail SMTP"""

    def __init__(self):
        self.gmail_user = settings.GMAIL_USER
        self.gmail_password = settings.GMAIL_APP_PASSWORD
        self.recipient_email = settings.GMAIL_USER
        self.enabled = bool(self.gmail_user and self.gmail_password)

        if not self.enabled:
            logger.warning("Email notifications disabled - GMAIL_USER or GMAIL_APP_PASSWORD not configured")
        else:
            logger.info(f"Gmail SMTP email service initialized - alerts will send to {self.recipient_email}")

    async def _send(self, subject: str, html_body: str, frame_base64: str = None) -> bool:
        """Internal helper to send an email via Gmail SMTP"""
        message = MIMEMultipart("related")
        message["Subject"] = subject
        message["From"] = self.gmail_user
        message["To"] = self.recipient_email

        html_part = MIMEMultipart("alternative")
        html_part.attach(MIMEText(html_body, "html"))
        message.attach(html_part)

        if frame_base64:
            try:
                image_data = base64.b64decode(frame_base64)
                image = MIMEImage(image_data, _subtype="jpeg")
                image.add_header("Content-ID", "<camera_frame>")
                image.add_header("Content-Disposition", "inline", filename="camera_frame.jpg")
                message.attach(image)
            except Exception as e:
                logger.warning(f"Could not attach camera frame: {e}")

        await aiosmtplib.send(
            message,
            hostname="smtp.gmail.com",
            port=587,
            start_tls=True,
            username=self.gmail_user,
            password=self.gmail_password,
        )
        return True

    async def send_critical_alert(self, alert_data: Dict[str, Any]) -> bool:
        """Send critical alert email"""
        if not self.enabled:
            return False

        try:
            title = alert_data.get('title', 'Critical Alert')
            message = alert_data.get('message', '')
            camera_id = alert_data.get('camera_id', 0)
            timestamp = alert_data.get('timestamp', datetime.now().isoformat())
            severity = alert_data.get('severity', 'CRITICAL')
            significance = alert_data.get('significance')
            query_confidence = alert_data.get('query_confidence')
            detected_objects = alert_data.get('detected_objects', [])
            frame_base64 = alert_data.get('frame_base64')

            confidence = query_confidence if query_confidence is not None else significance

            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_str = dt.strftime('%B %d, %Y at %I:%M %p')
            except Exception:
                time_str = datetime.now().strftime('%B %d, %Y at %I:%M %p')

            severity_emoji = '🚨' if severity == 'CRITICAL' else '⚠️' if severity == 'WARNING' else 'ℹ️'
            severity_color = '#dc3545' if severity == 'CRITICAL' else '#fd7e14' if severity == 'WARNING' else '#17a2b8'

            detected_objects_html = ''
            if detected_objects:
                badges = [
                    f'<span style="display:inline-block;padding:4px 12px;background:rgba(34,197,94,0.2);color:#22c55e;border-radius:12px;font-size:12px;margin:4px 4px 4px 0;border:1px solid rgba(34,197,94,0.3);">{obj}</span>'
                    for obj in detected_objects
                ]
                detected_objects_html = f'<div style="margin-top:16px;">{"".join(badges)}</div>'

            image_html = ''
            if frame_base64:
                image_html = """
                <div style="margin-top:20px;border-radius:8px;overflow:hidden;border:1px solid #374151;background:#111827;">
                    <img src="cid:camera_frame" alt="Event Frame" style="width:100%;max-height:400px;object-fit:contain;display:block;" />
                    <div style="padding:8px;background:#1f2937;text-align:center;font-size:12px;color:#9ca3af;">Supporting Evidence</div>
                </div>
                """

            confidence_badge = f'<span style="display:inline-block;padding:4px 10px;background:rgba(59,130,246,0.3);color:#60a5fa;border-radius:4px;font-size:11px;">{int(confidence)}% confidence</span>' if confidence is not None else ''

            html_body = f"""
            <!DOCTYPE html><html><head><meta charset="utf-8">
            <style>
                body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;line-height:1.6;color:#e5e7eb;background:#0f172a;margin:0;padding:20px;}}
                .container{{max-width:600px;margin:0 auto;background:#1e293b;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,0.3);border-left:4px solid {severity_color};}}
                .header{{padding:20px 24px;border-bottom:1px solid #334155;}}
                .title{{margin:0;font-size:18px;font-weight:600;color:#f3f4f6;}}
                .content{{padding:20px 24px;}}
                .message{{font-size:14px;line-height:1.7;color:#d1d5db;white-space:pre-line;margin:0;}}
                .meta{{margin-top:20px;padding-top:16px;border-top:1px solid #334155;color:#9ca3af;font-size:13px;}}
                .footer{{padding:16px 24px;background:#0f172a;border-radius:0 0 8px 8px;text-align:center;color:#6b7280;font-size:12px;border-top:1px solid #334155;}}
            </style></head><body>
            <div class="container">
                <div class="header">
                    <div style="margin-bottom:8px;">
                        <span style="display:inline-block;padding:4px 12px;background:{severity_color}33;color:{severity_color};border-radius:4px;font-size:12px;font-weight:600;">{severity_emoji} {severity}</span>
                        <span style="font-size:12px;color:#9ca3af;margin-left:8px;">Camera {camera_id}</span>
                        {confidence_badge}
                    </div>
                    <h1 class="title">{title}</h1>
                </div>
                <div class="content">
                    <div class="message">{message}</div>
                    {detected_objects_html}
                    {image_html}
                    <div class="meta"><div>🕐 <strong>Time:</strong> {time_str}</div></div>
                </div>
                <div class="footer">ThirdEye - AI-Powered Intelligent Monitoring System</div>
            </div>
            </body></html>
            """

            await self._send(f"{severity_emoji} {severity}: {title}", html_body, frame_base64)
            logger.info(f"Critical alert email sent: {title}")
            return True

        except Exception as e:
            logger.error(f"Failed to send critical alert email: {e}")
            return False

    async def send_summary_email(self, alert_data: Dict[str, Any]) -> bool:
        """Send 2-minute summary email"""
        if not self.enabled:
            return False

        try:
            title = alert_data.get('title', 'Activity Summary')
            message = alert_data.get('message', '')
            timestamp = alert_data.get('timestamp', datetime.now().isoformat())
            severity = alert_data.get('severity', 'INFO')
            camera_id = alert_data.get('camera_id')
            significance = alert_data.get('significance')
            detected_objects = alert_data.get('detected_objects', [])
            frame_base64 = alert_data.get('frame_base64')

            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_str = dt.strftime('%B %d, %Y at %I:%M %p')
            except Exception:
                time_str = datetime.now().strftime('%B %d, %Y at %I:%M %p')

            severity_emoji = '📊' if severity == 'INFO' else '⚠️' if severity == 'WARNING' else '🚨'
            severity_color = '#17a2b8' if severity == 'INFO' else '#fd7e14' if severity == 'WARNING' else '#dc3545'

            detected_objects_html = ''
            if detected_objects:
                badges = [
                    f'<span style="display:inline-block;padding:4px 12px;background:rgba(34,197,94,0.2);color:#22c55e;border-radius:12px;font-size:12px;margin:4px 4px 4px 0;border:1px solid rgba(34,197,94,0.3);">{obj}</span>'
                    for obj in detected_objects
                ]
                detected_objects_html = f'<div style="margin-top:16px;">{"".join(badges)}</div>'

            image_html = ''
            if frame_base64:
                image_html = """
                <div style="margin-top:20px;border-radius:8px;overflow:hidden;border:1px solid #374151;background:#111827;">
                    <img src="cid:camera_frame" alt="Event Frame" style="width:100%;max-height:400px;object-fit:contain;display:block;" />
                    <div style="padding:8px;background:#1f2937;text-align:center;font-size:12px;color:#9ca3af;">Most Significant Frame</div>
                </div>
                """

            extra_badges = ''
            if camera_id is not None:
                extra_badges += f'<span style="font-size:12px;color:#9ca3af;">Camera {camera_id}</span>'
            if significance is not None:
                extra_badges += f'<span style="display:inline-block;padding:4px 10px;background:rgba(59,130,246,0.3);color:#60a5fa;border-radius:4px;font-size:11px;margin-left:8px;">{int(significance)}% confidence</span>'

            html_body = f"""
            <!DOCTYPE html><html><head><meta charset="utf-8">
            <style>
                body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;line-height:1.6;color:#e5e7eb;background:#0f172a;margin:0;padding:20px;}}
                .container{{max-width:600px;margin:0 auto;background:#1e293b;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,0.3);border-left:4px solid {severity_color};}}
                .header{{padding:20px 24px;border-bottom:1px solid #334155;}}
                .title{{margin:0;font-size:18px;font-weight:600;color:#f3f4f6;}}
                .content{{padding:20px 24px;}}
                .message{{font-size:14px;line-height:1.7;color:#d1d5db;white-space:pre-line;margin:0;}}
                .meta{{margin-top:20px;padding-top:16px;border-top:1px solid #334155;color:#9ca3af;font-size:13px;}}
                .footer{{padding:16px 24px;background:#0f172a;border-radius:0 0 8px 8px;text-align:center;color:#6b7280;font-size:12px;border-top:1px solid #334155;}}
            </style></head><body>
            <div class="container">
                <div class="header">
                    <div style="margin-bottom:8px;">
                        <span style="display:inline-block;padding:4px 12px;background:{severity_color}33;color:{severity_color};border-radius:4px;font-size:12px;font-weight:600;">{severity_emoji} Activity Summary</span>
                        {extra_badges}
                    </div>
                    <h1 class="title">{title}</h1>
                </div>
                <div class="content">
                    <div class="message">{message}</div>
                    {detected_objects_html}
                    {image_html}
                    <div class="meta">
                        <div>🕐 <strong>Generated:</strong> {time_str}</div>
                        <div>📊 <strong>Type:</strong> 2-Minute Activity Summary</div>
                    </div>
                </div>
                <div class="footer">ThirdEye - AI-Powered Intelligent Monitoring System</div>
            </div>
            </body></html>
            """

            await self._send(f"{severity_emoji} {title}", html_body, frame_base64)
            logger.info(f"Summary email sent: {title}")
            return True

        except Exception as e:
            logger.error(f"Failed to send summary email: {e}")
            return False


# Global email service instance
email_service = EmailService()
