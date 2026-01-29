#!/usr/bin/env python3
"""
Test email notification system
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
print("📧 EMAIL NOTIFICATION TEST")
print("=" * 70)
print()

# Check configuration
print("Configuration:")
print(f"  SMTP Server: {email_service.smtp_server}")
print(f"  SMTP Port: {email_service.smtp_port}")
print(f"  Sender: {email_service.sender_email}")
print(f"  Recipient: {email_service.recipient_email}")
print(f"  Enabled: {email_service.enabled}")
print()

if not email_service.enabled:
    print("❌ Email service is not enabled!")
    print()
    print("To enable email notifications:")
    print("1. Edit backend/.env file")
    print("2. Set these values:")
    print("   EMAIL_SENDER=your-gmail@gmail.com")
    print("   EMAIL_PASSWORD=your-16-char-app-password")
    print()
    print("To get Gmail App Password:")
    print("1. Go to: https://myaccount.google.com/apppasswords")
    print("2. Create new app password")
    print("3. Name it: SentinTinel")
    print("4. Copy the 16-character password")
    print("5. Paste it in .env as EMAIL_PASSWORD")
    print()
    sys.exit(1)

print("=" * 70)
print("Sending test critical alert email...")
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
    print("Sending test 2-minute summary email...")
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
            print("✅ All email tests passed!")
            print()
            print("Next steps:")
            print("1. Check your email: moneshralapalli@gmail.com")
            print("2. You should have received 2 test emails")
            print("3. If you got them, email notifications are working!")
            print("4. Restart your surveillance system: ./restart.sh")
        else:
            print("⚠️ Some tests failed")
            print()
            print("Common issues:")
            print("1. Wrong Gmail address or password")
            print("2. App password not generated correctly")
            print("3. 2-Factor Authentication not enabled")
            print()
            print("Double-check your .env file settings")
    
    except Exception as e:
        print()
        print("=" * 70)
        print("❌ TEST FAILED WITH ERROR")
        print("=" * 70)
        print()
        print(f"Error: {str(e)}")
        print()
        print("Common causes:")
        print("1. Invalid Gmail credentials")
        print("2. App password not correct (should be 16 characters)")
        print("3. 2-Factor Authentication not enabled on Gmail")
        print("4. 'Less secure app access' might be needed")
        print()
        print("To fix:")
        print("1. Go to: https://myaccount.google.com/apppasswords")
        print("2. Generate a new app password")
        print("3. Update EMAIL_PASSWORD in .env")
        print("4. Run this test again")

if __name__ == "__main__":
    asyncio.run(main())

