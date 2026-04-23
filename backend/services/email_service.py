"""
Email notification service using Gmail SMTP.

The HTML mirrors the ThirdEye product theme: warm cream surface
(#FAF9F7), warm-ink text (#1A1714), Space Grotesk display font, DM Sans
body font, and muted severity chips matched to the in-app `.badge-*`
classes.  All timestamps are rendered in the user's display timezone so
they match what the operator sees in the UI.
"""
import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from loguru import logger
import sys
import os
import base64

try:
    from zoneinfo import ZoneInfo
except ImportError:  # Python < 3.9 fallback
    ZoneInfo = None  # type: ignore

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings


# ─────────────────────────────────────────────────────────────
# ThirdEye theme tokens (kept in sync with frontend/src/index.css)
# ─────────────────────────────────────────────────────────────
THEME = {
    "bg_page":       "#FAF9F7",
    "bg_surface":    "#FFFFFF",
    "bg_subtle":     "#F2EFE9",
    "border":        "#E8E3DB",
    "border_strong": "#D5CEC4",
    "text_primary":  "#1A1714",
    "text_secondary": "#4A4340",
    "text_muted":    "#8C837A",
    "text_faint":    "#B5ADA6",
    "ink_inverse":   "#FAF9F7",
    "accent":        "#1A1714",
}

SEVERITY_STYLES = {
    "CRITICAL": {
        "bar":    "#F87171",
        "text":   "#7C2D2D",
        "bg":     "#FDF2F2",
        "border": "#F0D0D0",
        "label":  "Critical",
    },
    "WARNING": {
        "bar":    "#FB923C",
        "text":   "#78490A",
        "bg":     "#FDFAF2",
        "border": "#EDD9A3",
        "label":  "Warning",
    },
    "INFO": {
        "bar":    "#8C837A",
        "text":   "#4A4340",
        "bg":     "#F2EFE9",
        "border": "#E8E3DB",
        "label":  "Info",
    },
    "SYSTEM": {
        "bar":    "#8C837A",
        "text":   "#4A4340",
        "bg":     "#F2EFE9",
        "border": "#E8E3DB",
        "label":  "System",
    },
}

FONT_STACK_BODY = (
    "'DM Sans','Helvetica Neue',Helvetica,Arial,sans-serif"
)
FONT_STACK_DISPLAY = (
    "'Space Grotesk','DM Sans','Helvetica Neue',Helvetica,Arial,sans-serif"
)


def _display_tz():
    """Resolve the configured display timezone or fall back to local."""
    name = (getattr(settings, "DISPLAY_TIMEZONE", "") or "").strip()
    if name and ZoneInfo is not None:
        try:
            return ZoneInfo(name)
        except Exception as e:
            logger.warning(f"Invalid DISPLAY_TIMEZONE '{name}': {e} — using local")
    # Use the local machine timezone
    return datetime.now().astimezone().tzinfo


def _format_timestamp(raw: Optional[str]) -> str:
    """Parse an ISO timestamp (assumed UTC if naive) and format in local TZ."""
    try:
        if not raw:
            dt = datetime.now(timezone.utc)
        else:
            # `datetime.utcnow().isoformat()` produces a naive UTC string
            # without a trailing Z — treat anything naive as UTC.
            cleaned = raw.replace("Z", "+00:00")
            dt = datetime.fromisoformat(cleaned)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

        dt_local = dt.astimezone(_display_tz())
        tz_abbr = dt_local.strftime("%Z") or ""
        base = dt_local.strftime("%b %d, %Y • %I:%M %p").replace(" 0", " ")
        return f"{base} {tz_abbr}".strip()
    except Exception:
        return datetime.now(_display_tz()).strftime("%b %d, %Y • %I:%M %p")


def _chip(label: str, *, bg: str, fg: str, border: str) -> str:
    return (
        f'<span style="display:inline-block;padding:3px 10px;'
        f'background:{bg};color:{fg};border:1px solid {border};'
        f'border-radius:999px;font-size:11px;font-weight:500;'
        f'letter-spacing:0.02em;margin-right:6px;">{label}</span>'
    )


def _object_chips(objects):
    if not objects:
        return ""
    chips = "".join(
        _chip(
            str(obj),
            bg=THEME["bg_subtle"],
            fg=THEME["text_secondary"],
            border=THEME["border"],
        )
        for obj in objects
    )
    return (
        f'<div style="margin-top:14px;display:flex;flex-wrap:wrap;gap:4px;">{chips}</div>'
    )


def _evidence_image_html(has_image: bool, caption: str) -> str:
    if not has_image:
        return ""
    return f"""
    <div style="margin-top:22px;border:1px solid {THEME['border']};
                border-radius:10px;overflow:hidden;background:{THEME['bg_subtle']};">
        <img src="cid:camera_frame" alt="Evidence frame"
             style="display:block;width:100%;max-height:420px;object-fit:contain;
                    background:{THEME['bg_subtle']};" />
        <div style="padding:8px 14px;background:{THEME['bg_subtle']};
                    border-top:1px solid {THEME['border']};
                    text-align:center;font-size:11px;color:{THEME['text_muted']};
                    letter-spacing:0.04em;text-transform:uppercase;">
            {caption}
        </div>
    </div>
    """


def _reason_row(label: str, value: Optional[str]) -> str:
    if not value:
        return ""
    return f"""
    <div style="margin-top:14px;">
      <div style="font-size:11px;text-transform:uppercase;letter-spacing:0.08em;
                  color:{THEME['text_muted']};font-weight:600;margin-bottom:4px;">
        {label}
      </div>
      <div style="font-size:14px;line-height:1.6;color:{THEME['text_secondary']};
                  white-space:pre-line;">{value}</div>
    </div>
    """


def _brand_header() -> str:
    """ThirdEye mark + wordmark rendered in the warm theme."""
    return f"""
    <div style="padding:20px 28px 0 28px;">
      <div style="display:flex;align-items:center;gap:10px;">
        <div style="width:26px;height:26px;border-radius:50%;
                    background:{THEME['text_primary']};
                    display:inline-flex;align-items:center;justify-content:center;">
          <div style="width:10px;height:10px;border-radius:50%;
                      background:{THEME['bg_surface']};"></div>
        </div>
        <div style="font-family:{FONT_STACK_DISPLAY};font-weight:700;
                    font-size:16px;letter-spacing:-0.02em;
                    color:{THEME['text_primary']};">
          ThirdEye
        </div>
      </div>
    </div>
    """


def _footer() -> str:
    return f"""
    <div style="padding:18px 28px;background:{THEME['bg_subtle']};
                border-top:1px solid {THEME['border']};
                text-align:center;font-size:11px;color:{THEME['text_muted']};
                letter-spacing:0.04em;">
      ThirdEye — AI-powered intelligent monitoring
    </div>
    """


def _shell(inner_html: str, severity_bar: str) -> str:
    """Outer email shell with warm cream background."""
    return f"""
    <!DOCTYPE html>
    <html><head><meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
    </head>
    <body style="margin:0;padding:24px;background:{THEME['bg_page']};
                 font-family:{FONT_STACK_BODY};color:{THEME['text_primary']};
                 line-height:1.55;">
      <div style="max-width:620px;margin:0 auto;background:{THEME['bg_surface']};
                  border:1px solid {THEME['border']};border-radius:14px;
                  overflow:hidden;box-shadow:0 1px 2px rgba(26,23,20,0.04);">
        <div style="height:3px;background:{severity_bar};"></div>
        {inner_html}
      </div>
      <div style="max-width:620px;margin:10px auto 0 auto;
                  font-size:11px;color:{THEME['text_faint']};text-align:center;">
        You are receiving this alert because it matched an active monitoring
        trigger on your ThirdEye account.
      </div>
    </body></html>
    """


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
        message = MIMEMultipart("related")
        message["Subject"] = subject
        message["From"] = f"ThirdEye <{self.gmail_user}>"
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

    # ────────────────────────────────────────────
    # Public senders
    # ────────────────────────────────────────────

    async def send_critical_alert(self, alert_data: Dict[str, Any]) -> bool:
        """Send a trigger-matched alert email."""
        if not self.enabled:
            return False

        try:
            title            = alert_data.get("title", "Trigger matched")
            message          = alert_data.get("message", "")
            camera_id        = alert_data.get("camera_id")
            timestamp        = alert_data.get("timestamp")
            severity         = (alert_data.get("severity") or "CRITICAL").upper()
            significance     = alert_data.get("significance")
            query_confidence = alert_data.get("query_confidence")
            detected_objects = alert_data.get("detected_objects", [])
            frame_base64     = alert_data.get("frame_base64")
            user_query       = alert_data.get("user_query")
            query_details    = alert_data.get("query_details")
            claude_reasoning = alert_data.get("claude_reasoning")
            scene_description = alert_data.get("scene_description")
            activity         = alert_data.get("activity")

            confidence = query_confidence if query_confidence is not None else significance
            sev = SEVERITY_STYLES.get(severity, SEVERITY_STYLES["INFO"])
            time_str = _format_timestamp(timestamp)

            severity_chip = _chip(
                sev["label"],
                bg=sev["bg"], fg=sev["text"], border=sev["border"],
            )
            meta_chips = severity_chip
            if camera_id is not None:
                meta_chips += _chip(
                    f"Camera {camera_id}",
                    bg=THEME["bg_subtle"], fg=THEME["text_secondary"],
                    border=THEME["border"],
                )
            if confidence is not None:
                meta_chips += _chip(
                    f"{int(confidence)}% confidence",
                    bg=THEME["bg_subtle"], fg=THEME["text_secondary"],
                    border=THEME["border"],
                )

            trigger_chip = ""
            if user_query:
                trigger_chip = f"""
                <div style="margin-top:8px;font-size:12px;color:{THEME['text_muted']};">
                  Triggered by your rule:
                  <span style="color:{THEME['text_primary']};font-weight:500;">
                    &ldquo;{user_query}&rdquo;
                  </span>
                </div>
                """

            content_html = f"""
            {_brand_header()}
            <div style="padding:16px 28px 4px 28px;">
              <div>{meta_chips}</div>
              <h1 style="margin:12px 0 0 0;font-family:{FONT_STACK_DISPLAY};
                         font-size:22px;font-weight:600;letter-spacing:-0.02em;
                         color:{THEME['text_primary']};line-height:1.25;">
                {title}
              </h1>
              {trigger_chip}
            </div>
            <div style="padding:14px 28px 22px 28px;">
              <p style="margin:14px 0 0 0;font-size:14.5px;line-height:1.65;
                        color:{THEME['text_secondary']};white-space:pre-line;">
                {message}
              </p>
              {_reason_row("Match evidence", query_details)}
              {_reason_row("Model reasoning", claude_reasoning)}
              {_reason_row("Scene", scene_description)}
              {_reason_row("Activity", activity)}
              {_object_chips(detected_objects)}
              {_evidence_image_html(bool(frame_base64), "Frame analysed by the model")}
              <div style="margin-top:22px;padding-top:14px;
                          border-top:1px solid {THEME['border']};
                          font-size:12px;color:{THEME['text_muted']};">
                Captured <span style="color:{THEME['text_primary']};">{time_str}</span>
              </div>
            </div>
            {_footer()}
            """

            html_body = _shell(content_html, severity_bar=sev["bar"])
            subject = f"[ThirdEye • {sev['label']}] {title}"
            await self._send(subject, html_body, frame_base64)
            logger.info(f"Critical alert email sent: {title}")
            return True

        except Exception as e:
            logger.error(f"Failed to send critical alert email: {e}")
            return False

    async def send_summary_email(self, alert_data: Dict[str, Any]) -> bool:
        """Send the 2-minute activity summary email."""
        if not self.enabled:
            return False

        try:
            title            = alert_data.get("title", "Activity summary")
            message          = alert_data.get("message", "")
            timestamp        = alert_data.get("timestamp")
            severity         = (alert_data.get("severity") or "INFO").upper()
            camera_id        = alert_data.get("camera_id")
            significance     = alert_data.get("significance")
            detected_objects = alert_data.get("detected_objects", [])
            frame_base64     = alert_data.get("frame_base64")

            sev = SEVERITY_STYLES.get(severity, SEVERITY_STYLES["INFO"])
            time_str = _format_timestamp(timestamp)

            meta_chips = _chip(
                "Summary",
                bg=THEME["bg_subtle"], fg=THEME["text_secondary"],
                border=THEME["border"],
            )
            if camera_id is not None:
                meta_chips += _chip(
                    f"Camera {camera_id}",
                    bg=THEME["bg_subtle"], fg=THEME["text_secondary"],
                    border=THEME["border"],
                )
            if significance is not None:
                meta_chips += _chip(
                    f"{int(significance)}% peak",
                    bg=THEME["bg_subtle"], fg=THEME["text_secondary"],
                    border=THEME["border"],
                )

            content_html = f"""
            {_brand_header()}
            <div style="padding:16px 28px 4px 28px;">
              <div>{meta_chips}</div>
              <h1 style="margin:12px 0 0 0;font-family:{FONT_STACK_DISPLAY};
                         font-size:22px;font-weight:600;letter-spacing:-0.02em;
                         color:{THEME['text_primary']};line-height:1.25;">
                {title}
              </h1>
            </div>
            <div style="padding:14px 28px 22px 28px;">
              <p style="margin:14px 0 0 0;font-size:14.5px;line-height:1.65;
                        color:{THEME['text_secondary']};white-space:pre-line;">
                {message}
              </p>
              {_object_chips(detected_objects)}
              {_evidence_image_html(bool(frame_base64), "Most significant frame")}
              <div style="margin-top:22px;padding-top:14px;
                          border-top:1px solid {THEME['border']};
                          font-size:12px;color:{THEME['text_muted']};">
                Generated <span style="color:{THEME['text_primary']};">{time_str}</span>
                &nbsp;•&nbsp; 2-minute activity window
              </div>
            </div>
            {_footer()}
            """

            html_body = _shell(content_html, severity_bar=sev["bar"])
            subject = f"[ThirdEye] {title}"
            await self._send(subject, html_body, frame_base64)
            logger.info(f"Summary email sent: {title}")
            return True

        except Exception as e:
            logger.error(f"Failed to send summary email: {e}")
            return False


# Global email service instance
email_service = EmailService()
