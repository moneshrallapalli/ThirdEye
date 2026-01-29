"""
Email notification service for SentinTinel
Sends email alerts for critical events and summaries
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from typing import List, Optional, Dict, Any
from datetime import datetime
from loguru import logger
import base64
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings


class EmailService:
    """Service for sending email notifications"""
    
    def __init__(self):
        """Initialize email service with Gmail settings"""
        self.smtp_server = settings.EMAIL_SMTP_SERVER
        self.smtp_port = settings.EMAIL_SMTP_PORT
        self.sender_email = settings.EMAIL_SENDER
        self.sender_password = settings.EMAIL_PASSWORD
        self.recipient_email = settings.EMAIL_RECIPIENT
        
        # Check if email is configured
        self.enabled = bool(self.sender_email and self.sender_password)
        
        if not self.enabled:
            logger.warning("⚠️ Email notifications disabled - EMAIL_SENDER or EMAIL_PASSWORD not configured in .env")
        else:
            logger.info(f"📧 Email service initialized - will send to {self.recipient_email}")
    
    async def send_critical_alert(
        self,
        alert_data: Dict[str, Any]
    ) -> bool:
        """
        Send critical alert email using the exact same data structure as the frontend
        
        Args:
            alert_data: The complete alert data dict sent to frontend (includes title, message, 
                       camera_id, timestamp, significance, frame_base64, etc.)
            
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
            
            # Create message
            msg = MIMEMultipart('related')
            msg['From'] = self.sender_email
            msg['To'] = self.recipient_email
            msg['Subject'] = f"🚨 {severity}: {title}"
            
            # Build HTML body - clean and simple, matching the alert tab display
            html_body = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; background: #f5f5f5; margin: 0; padding: 20px; }}
                    .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
                    .header {{ background: {'#dc3545' if severity == 'CRITICAL' else '#ffc107' if severity == 'WARNING' else '#17a2b8'}; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
                    .header h1 {{ margin: 0; font-size: 20px; font-weight: 600; }}
                    .content {{ padding: 24px; }}
                    .message {{ font-size: 15px; line-height: 1.7; color: #333; white-space: pre-wrap; margin: 0; }}
                    .meta {{ margin-top: 24px; padding-top: 16px; border-top: 1px solid #e0e0e0; color: #666; font-size: 13px; }}
                    .meta-item {{ margin: 4px 0; }}
                    .image {{ max-width: 100%; height: auto; margin-top: 20px; border-radius: 6px; border: 1px solid #e0e0e0; }}
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
                        {'<img src="cid:alert_image" class="image" alt="Alert Snapshot">' if frame_base64 else ''}
                    </div>
                    <div class="footer">
                        SentinTinel AI Surveillance System
                    </div>
                </div>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(html_body, 'html'))
            
            # Attach image if provided
            if frame_base64:
                try:
                    # Remove data URL prefix if present
                    if ',' in frame_base64:
                        frame_base64 = frame_base64.split(',')[1]
                    
                    img_data = base64.b64decode(frame_base64)
                    img = MIMEImage(img_data, 'jpeg')
                    img.add_header('Content-ID', '<alert_image>')
                    msg.attach(img)
                except Exception as img_error:
                    logger.warning(f"Failed to attach image to alert email: {img_error}")
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
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
            alert_data: The complete alert data dict sent to frontend (includes title, message,
                       timestamp, events, etc.)
            
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
            frame_base64 = alert_data.get('frame_base64')
            
            # Parse timestamp for display
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_str = dt.strftime('%B %d, %Y at %I:%M %p')
            except:
                time_str = datetime.now().strftime('%B %d, %Y at %I:%M %p')
            
            # Create message
            msg = MIMEMultipart('related')
            msg['From'] = self.sender_email
            msg['To'] = self.recipient_email
            msg['Subject'] = f"📊 {title}"
            
            # Build HTML body - clean and simple, matching the alert tab display
            html_body = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; background: #f5f5f5; margin: 0; padding: 20px; }}
                    .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
                    .header {{ background: #007bff; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
                    .header h1 {{ margin: 0; font-size: 20px; font-weight: 600; }}
                    .content {{ padding: 24px; }}
                    .message {{ font-size: 15px; line-height: 1.7; color: #333; white-space: pre-wrap; margin: 0; }}
                    .meta {{ margin-top: 24px; padding-top: 16px; border-top: 1px solid #e0e0e0; color: #666; font-size: 13px; }}
                    .meta-item {{ margin: 4px 0; }}
                    .image {{ max-width: 100%; height: auto; margin-top: 20px; border-radius: 6px; border: 1px solid #e0e0e0; }}
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
                        {'<img src="cid:summary_image" class="image" alt="Activity Snapshot">' if frame_base64 else ''}
                    </div>
                    <div class="footer">
                        SentinTinel AI Surveillance System
                    </div>
                </div>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(html_body, 'html'))
            
            # Attach image if provided
            if frame_base64:
                try:
                    # Remove data URL prefix if present
                    if ',' in frame_base64:
                        frame_base64 = frame_base64.split(',')[1]
                    
                    img_data = base64.b64decode(frame_base64)
                    img = MIMEImage(img_data, 'jpeg')
                    img.add_header('Content-ID', '<summary_image>')
                    msg.attach(img)
                except Exception as img_error:
                    logger.warning(f"Failed to attach image to summary email: {img_error}")
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            logger.info(f"✅ Summary email sent to {self.recipient_email}: {title}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send summary email: {e}")
            return False


# Global email service instance
email_service = EmailService()
