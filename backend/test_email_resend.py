#!/usr/bin/env python3
"""
Test Resend email notification system
"""
import asyncio
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.email_service import email_service
from dotenv import load_dotenv

# Load environment
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

print("=" * 70)
print("📧 RESEND EMAIL TEST")
print("=" * 70)
print()

# Check configuration
print("Configuration:")
print(f"  Resend API Key: {'✓ Set' if email_service.enabled else '✗ Not set'}")
print(f"  Sender: {email_service.sender_email}")
print(f"  Recipient: {email_service.recipient_email}")
print(f"  Enabled: {email_service.enabled}")
print()

if not email_service.enabled:
    print("❌ Email service is not enabled!")
    print()
    print("To enable Resend email notifications:")
    print("=" * 70)
    print()
    print("STEP 1: Sign up for free Resend account")
    print("        https://resend.com/signup")
    print()
    print("STEP 2: Get your API key")
    print("        Dashboard → API Keys → Create API Key")
    print("        Copy the key (starts with: re_...)")
    print()
    print("STEP 3: Update .env file")
    print("        cd /Users/monesh/University/practice/backend")
    print("        nano .env")
    print()
    print("        Add this line:")
    print("        RESEND_API_KEY=re_your_actual_key_here")
    print()
    print("=" * 70)
    print()
    print("✅ FREE TIER: 100 emails/day, 3,000/month")
    print("✅ NO SMTP configuration needed!")
    print("✅ Works in 2 minutes!")
    print()
    sys.exit(1)

print("=" * 70)
print("Test 1: Sending critical alert email...")
print("=" * 70)
print()

async def test_critical_alert():
    """Test critical alert email"""
    # Use the same alert data structure as the frontend receives
    alert_data = {
        "id": f"test_alert_{int(datetime.now().timestamp())}",
        "severity": "CRITICAL",
        "title": "✓ Person Left Camera Frame - Camera 0",
        "message": """Hey, I need to notify you about something important.

I've detected that the person has left the camera frame.

Here's what happened: Initially, I observed a person seated in chair, partially visible on the right side. Now, the room shows an empty chair with no person present.

After analyzing the scene progression, I'm very confident (95% match) that the person has left the camera frame.

This was verified through advanced AI reasoning to ensure accuracy.

This alert was triggered 2 minutes after I started monitoring. I've attached visual evidence for you to review.

Would you like me to continue monitoring, or should I take any other action?""",
        "camera_id": 0,
        "timestamp": datetime.now().isoformat(),
        "significance": 95,
        "frame_base64": None,  # No image in test
        "alert_type": "immediate",
        "is_read": False
    }
    
    success = await email_service.send_critical_alert(alert_data=alert_data)
    
    if success:
        print("✅ Critical alert email sent successfully!")
        print(f"   Check your inbox at: {email_service.recipient_email}")
    else:
        print("❌ Failed to send critical alert email")
        print("   Check the error messages above")
    
    return success

async def test_summary():
    """Test summary email"""
    print()
    print("=" * 70)
    print("Test 2: Sending 2-minute summary email...")
    print("=" * 70)
    print()
    
    # Use the same alert data structure as the frontend receives
    alert_data = {
        "id": f"test_summary_{int(datetime.now().timestamp())}",
        "severity": "INFO",
        "title": "📊 2-Minute Activity Summary - Camera 0",
        "message": """**Period Summary (2 minutes)**

I've observed **3 significant events** during this period, with a peak significance of **85%**.

**Most Notable Activity:**
Person seated in chair drinking from a glass with laptop visible on desk

**Activity Timeline:**
• 85% - Person seated in chair drinking from a glass
• 70% - Person looking at laptop on desk
• 60% - Person standing near door

**Next Update:** In 2 minutes""",
        "camera_id": 0,
        "timestamp": datetime.now().isoformat(),
        "significance": 85,
        "frame_base64": None,  # No image in test
        "alert_type": "summary",
        "event_count": 3,
        "is_read": False
    }
    
    success = await email_service.send_summary_email(alert_data=alert_data)
    
    if success:
        print("✅ Summary email sent successfully!")
        print(f"   Check your inbox at: {email_service.recipient_email}")
    else:
        print("❌ Failed to send summary email")
        print("   Check the error messages above")
    
    return success

async def main():
    """Run tests"""
    try:
        # Test critical alert
        alert_success = await test_critical_alert()
        
        # Wait a bit
        await asyncio.sleep(2)
        
        # Test summary
        summary_success = await test_summary()
        
        print()
        print("=" * 70)
        print("TEST COMPLETE")
        print("=" * 70)
        print()
        
        if alert_success and summary_success:
            print("✅ ALL TESTS PASSED!")
            print()
            print("🎉 Email notifications are working perfectly!")
            print()
            print("Next steps:")
            print("1. Check your email: moneshralapalli@gmail.com")
            print("2. You should have received 2 test emails")
            print("3. If you got them, restart your system:")
            print("   cd /Users/monesh/University/practice")
            print("   ./restart.sh")
            print()
            print("Your surveillance system will now send:")
            print("  ✓ Critical alerts (immediate)")
            print("  ✓ 2-minute activity summaries")
            print("  ✓ Same messages as your Alerts tab")
        else:
            print("⚠️ Some tests failed")
            print()
            print("Common issues:")
            print("1. Invalid Resend API key")
            print("2. API key permissions not set correctly")
            print("3. Network connectivity issue")
            print()
            print("To fix:")
            print("1. Go to: https://resend.com/api-keys")
            print("2. Generate a new API key with Full Access")
            print("3. Update RESEND_API_KEY in .env")
            print("4. Run this test again")
    
    except Exception as e:
        print()
        print("=" * 70)
        print("❌ TEST FAILED WITH ERROR")
        print("=" * 70)
        print()
        print(f"Error: {str(e)}")
        print()
        print("This usually means:")
        print("1. Resend API key is invalid or missing")
        print("2. Check your RESEND_API_KEY in .env file")
        print("3. Make sure it starts with 're_'")
        print()
        print("Get your API key:")
        print("1. Go to: https://resend.com/api-keys")
        print("2. Create new key with Full Access")
        print("3. Copy and paste into .env")

if __name__ == "__main__":
    asyncio.run(main())

