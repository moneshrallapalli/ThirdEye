#!/usr/bin/env python3
"""
Test email with actual image to verify image embedding works
"""
import asyncio
from datetime import datetime
import sys
import os
import base64
import cv2
import numpy as np

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.email_service import email_service

print("=" * 70)
print("📧 TESTING EMAIL WITH EMBEDDED IMAGE")
print("=" * 70)
print()

# Check configuration
print("Configuration:")
print(f"  API Key: {'✓ Set' if email_service.enabled else '✗ Missing'}")
print(f"  Sender: {email_service.sender_email}")
print(f"  Recipient: {email_service.recipient_email}")
print(f"  Enabled: {email_service.enabled}")
print()

if not email_service.enabled:
    print("❌ RESEND_API_KEY not configured")
    sys.exit(1)

def create_test_image_base64():
    """Create a test image with text and encode it to base64"""
    # Create a 640x480 image with a gradient background
    img = np.zeros((480, 640, 3), dtype=np.uint8)

    # Create gradient
    for i in range(480):
        img[i, :] = [int(50 + i * 0.2), int(30 + i * 0.1), int(80 + i * 0.15)]

    # Add rectangles to simulate detected objects
    cv2.rectangle(img, (100, 150), (300, 350), (0, 255, 0), 3)  # Green box for "person"
    cv2.rectangle(img, (350, 200), (550, 300), (255, 0, 0), 3)  # Blue box for "laptop"

    # Add text
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(img, 'TEST SURVEILLANCE ALERT', (120, 50), font, 0.8, (255, 255, 255), 2)
    cv2.putText(img, 'Camera 1 - Live Feed', (180, 430), font, 0.7, (200, 200, 200), 2)
    cv2.putText(img, 'Person Detected', (110, 140), font, 0.6, (0, 255, 0), 2)
    cv2.putText(img, 'Laptop Detected', (360, 190), font, 0.6, (255, 0, 0), 2)

    # Add timestamp
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cv2.putText(img, timestamp, (220, 460), font, 0.5, (255, 255, 0), 1)

    # Encode to JPEG
    _, buffer = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 85])

    # Convert to base64
    img_base64 = base64.b64encode(buffer).decode('utf-8')

    print(f"✓ Test image created: 640x480 pixels")
    print(f"✓ Base64 length: {len(img_base64)} characters")
    print(f"✓ Image size: ~{len(buffer) / 1024:.1f} KB")
    print()

    return img_base64

async def test_critical_alert_with_image():
    """Test critical alert email with embedded image"""
    print("=" * 70)
    print("Sending critical alert with EMBEDDED IMAGE...")
    print("=" * 70)
    print()

    # Create test image
    frame_base64 = create_test_image_base64()

    alert_data = {
        "id": f"test_img_alert_{int(datetime.now().timestamp())}",
        "severity": "CRITICAL",
        "title": "🚨 Unauthorized Access Detected - Camera 1",
        "message": """**SECURITY ALERT**

I've detected unauthorized access in the restricted area.

**What I observed:**
- Unknown person entered server room
- Person carrying laptop and backpack
- No visible identification badge

**Confidence:** 94% - This is a high-priority security event

**Recommended Actions:**
1. Verify person's identity immediately
2. Check access control logs
3. Review security footage

The image below shows what I captured. You can see the person and the laptop clearly marked with detection boxes.""",
        "camera_id": 1,
        "timestamp": datetime.now().isoformat(),
        "significance": 94,
        "query_confidence": 94,
        "detected_objects": ["person", "laptop", "backpack"],
        "frame_base64": frame_base64,  # THIS IS THE KEY - Real base64 image
        "alert_type": "immediate",
        "is_read": False
    }

    print("Sending email with:")
    print(f"  - Image: YES (base64, {len(frame_base64)} chars)")
    print(f"  - Detected objects: {len(alert_data['detected_objects'])} items")
    print(f"  - Confidence: {alert_data['significance']}%")
    print()

    success = await email_service.send_critical_alert(alert_data=alert_data)

    if success:
        print("✅ Email sent successfully!")
        print()
        print("🔍 CHECK YOUR INBOX NOW!")
        print(f"   Email: {email_service.recipient_email}")
        print()
        print("   You should see:")
        print("   ✓ 🚨 CRITICAL severity badge")
        print("   ✓ Camera 1 badge")
        print("   ✓ 94% confidence badge")
        print("   ✓ Green badges: person, laptop, backpack")
        print("   ✓ Full alert message")
        print("   ✓ 📷 EMBEDDED IMAGE showing test surveillance scene")
        print("   ✓ Detection boxes on person and laptop")
        print()
        print("📸 The image should show:")
        print("   - Green box around 'Person Detected'")
        print("   - Blue box around 'Laptop Detected'")
        print("   - Timestamp at bottom")
        print("   - 'TEST SURVEILLANCE ALERT' header")
        print()
    else:
        print("❌ Failed to send email")
        print("   Check error messages above")

    return success

async def test_summary_with_image():
    """Test summary email with embedded image"""
    print()
    print("=" * 70)
    print("Sending 2-minute summary with EMBEDDED IMAGE...")
    print("=" * 70)
    print()

    # Create test image
    frame_base64 = create_test_image_base64()

    alert_data = {
        "id": f"test_img_summary_{int(datetime.now().timestamp())}",
        "severity": "INFO",
        "title": "📊 Activity Summary - Past 2 Minutes",
        "message": """**2-Minute Activity Report**

I've monitored **5 significant events** in the past 2 minutes.

**Peak Activity:** 89% significance

**Event Timeline:**
• 89% - Person working at desk with laptop
• 78% - Phone conversation detected
• 72% - Person accessing file cabinet
• 65% - Movement to printer area
• 61% - Returned to desk

**All Objects Detected:** person, laptop, backpack, phone, documents

**Status:** Normal office activity. No security concerns detected.

**Next Summary:** In 2 minutes

The image below shows the most significant frame from this period.""",
        "camera_id": 1,
        "timestamp": datetime.now().isoformat(),
        "significance": 89,
        "detected_objects": ["person", "laptop", "backpack", "phone", "documents"],
        "frame_base64": frame_base64,  # THIS IS THE KEY - Real base64 image
        "alert_type": "summary",
        "event_count": 5,
        "is_read": False
    }

    print("Sending summary email with:")
    print(f"  - Image: YES (base64, {len(frame_base64)} chars)")
    print(f"  - Events: {alert_data['event_count']}")
    print(f"  - Peak significance: {alert_data['significance']}%")
    print()

    success = await email_service.send_summary_email(alert_data=alert_data)

    if success:
        print("✅ Summary email sent successfully!")
        print()
        print("🔍 CHECK YOUR INBOX NOW!")
        print(f"   Email: {email_service.recipient_email}")
        print()
        print("   You should see:")
        print("   ✓ 📊 Activity Summary badge")
        print("   ✓ Camera 1 badge")
        print("   ✓ 89% confidence badge")
        print("   ✓ Green badges for all detected objects")
        print("   ✓ Full summary message")
        print("   ✓ 📷 EMBEDDED IMAGE with caption 'Most Significant Frame'")
        print()
    else:
        print("❌ Failed to send summary email")

    return success

async def main():
    """Run all tests"""
    test1 = await test_critical_alert_with_image()
    test2 = await test_summary_with_image()

    print()
    print("=" * 70)
    print("IMAGE EMAIL TEST COMPLETE")
    print("=" * 70)
    print()

    if test1 and test2:
        print("✅ BOTH EMAILS SENT WITH IMAGES!")
        print()
        print("📬 Check your inbox right now:")
        print(f"   {email_service.recipient_email}")
        print()
        print("You should have 2 new emails with:")
        print("   1. Critical Alert - with embedded test image")
        print("   2. Activity Summary - with embedded test image")
        print()
        print("Both should show the same test surveillance image")
        print("with detection boxes and timestamp.")
        print()
        print("If you see the images, your email system is working perfectly! 🎉")
        print()
        print("If you DON'T see the images:")
        print("   - Check your spam folder")
        print("   - Try viewing in different email client (web vs app)")
        print("   - Some email clients block images by default")
        print("   - Look for 'Show Images' or 'Load Images' button")
    else:
        print("❌ SOME TESTS FAILED")

if __name__ == "__main__":
    asyncio.run(main())
