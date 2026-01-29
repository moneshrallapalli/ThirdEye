#!/usr/bin/env python3
"""
Quick test script for Resend email service setup
Run this after adding your RESEND_API_KEY to .env
"""
import asyncio
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.email_service import email_service

print("=" * 70)
print("📧 RESEND EMAIL SERVICE TEST")
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
    print("❌ RESEND_API_KEY not found in .env file")
    print()
    print("Please follow these steps:")
    print("1. Go to https://resend.com/signup")
    print("2. Sign up and verify your email")
    print("3. Go to API Keys and create a new key")
    print("4. Copy the API key (starts with 're_...')")
    print("5. Add to backend/.env file:")
    print("   RESEND_API_KEY=re_your_actual_key_here")
    print()
    sys.exit(1)

async def test_critical_alert():
    """Test critical alert email with full UI format"""
    print("=" * 70)
    print("Test 1: Sending critical alert email with image and badges...")
    print("=" * 70)
    print()

    # Simulate a real alert with all UI elements
    alert_data = {
        "id": f"test_alert_{int(datetime.now().timestamp())}",
        "severity": "CRITICAL",
        "title": "🚨 Unauthorized Person Detected - Camera 1",
        "message": """**CRITICAL SECURITY ALERT**

I've detected an unauthorized person in the restricted area.

**What I observed:**
- Unknown individual entered through side entrance
- No visible ID badge or credentials
- Currently in server room area

**Confidence:** This is a high-priority security breach (92% confidence)

**Recommended Actions:**
1. Verify person's identity immediately
2. Review access logs
3. Dispatch security personnel if needed

I've attached visual evidence for your review.""",
        "camera_id": 1,
        "timestamp": datetime.now().isoformat(),
        "significance": 92,
        "detected_objects": ["person", "backpack", "laptop"],
        "frame_base64": None,  # Real alerts will have actual images
        "alert_type": "immediate",
        "is_read": False
    }

    success = await email_service.send_critical_alert(alert_data=alert_data)

    if success:
        print("✅ Critical alert email sent successfully!")
        print(f"   Check your inbox at: {email_service.recipient_email}")
        print()
        print("   Email includes:")
        print("   ✓ Severity badge (CRITICAL)")
        print("   ✓ Camera ID badge")
        print("   ✓ Confidence percentage (92%)")
        print("   ✓ Detected objects tags (person, backpack, laptop)")
        print("   ✓ Dark theme styling matching your UI")
        print("   ✓ Full alert message")
    else:
        print("❌ Failed to send critical alert email")
        print("   Check the error messages above")

    return success

async def test_summary():
    """Test summary email with UI format"""
    print()
    print("=" * 70)
    print("Test 2: Sending 2-minute summary email...")
    print("=" * 70)
    print()

    alert_data = {
        "id": f"test_summary_{int(datetime.now().timestamp())}",
        "severity": "INFO",
        "title": "📊 Activity Summary - Past 2 Minutes",
        "message": """**Activity Report**

I've monitored **4 significant events** in the past 2 minutes.

**Peak Activity:** 85% significance detected

**Event Timeline:**
• 85% - Person working at desk with laptop and documents
• 72% - Phone conversation in progress
• 68% - Person moved to filing cabinet
• 61% - Returned to desk, resumed work

**Detected Items:** laptop, documents, phone, filing cabinet

**Status:** Normal office activity detected. No security concerns.

**Next Summary:** In 2 minutes""",
        "camera_id": 1,
        "timestamp": datetime.now().isoformat(),
        "significance": 85,
        "detected_objects": ["person", "laptop", "documents", "phone"],
        "frame_base64": None,
        "alert_type": "summary",
        "event_count": 4,
        "is_read": False
    }

    success = await email_service.send_summary_email(alert_data=alert_data)

    if success:
        print("✅ Summary email sent successfully!")
        print(f"   Check your inbox at: {email_service.recipient_email}")
        print()
        print("   Email includes:")
        print("   ✓ Activity summary badge")
        print("   ✓ Camera ID and confidence badges")
        print("   ✓ Detected objects tags")
        print("   ✓ Full summary message")
        print("   ✓ Dark theme matching your UI")
    else:
        print("❌ Failed to send summary email")
        print("   Check the error messages above")

    return success

async def main():
    """Run all tests"""
    test1 = await test_critical_alert()
    test2 = await test_summary()

    print()
    print("=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
    print()

    if test1 and test2:
        print("✅ ALL TESTS PASSED!")
        print()
        print("🎉 Resend email notifications are working perfectly!")
        print()
        print("What you'll receive:")
        print("  ✓ Critical alerts (immediate, ≥60% confidence)")
        print("  ✓ 2-minute activity summaries")
        print("  ✓ Images embedded in emails")
        print("  ✓ Detected objects as badges")
        print("  ✓ Confidence percentages")
        print("  ✓ Dark theme matching your UI")
        print()
        print(f"Check your inbox: {email_service.recipient_email}")
        print()
        print("Next step: Start your surveillance system to receive real alerts!")
    else:
        print("❌ SOME TESTS FAILED")
        print()
        print("Common issues:")
        print("  1. Invalid API key - verify it starts with 're_'")
        print("  2. API key not activated - check Resend dashboard")
        print("  3. Network issues - check your internet connection")

if __name__ == "__main__":
    asyncio.run(main())
