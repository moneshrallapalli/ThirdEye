"""
Simple script to initialize webcam via direct service access
This works with the running server since camera_service is a singleton
"""
import asyncio
import requests
import cv2


def check_webcam():
    """Check if webcam is accessible"""
    print("🎥 Checking webcam accessibility...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Webcam not accessible!")
        print("   Make sure:")
        print("   - Camera is not in use by another app")
        print("   - Camera permissions are granted")
        return False
    print("✅ Webcam is accessible!")
    cap.release()
    return True


def init_camera_via_service():
    """Initialize camera directly through the running service"""
    print("\n🔧 Initializing camera in the running server...")

    # Import the camera service (this will access the same singleton as the server)
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    from services.camera_service import camera_service

    async def init():
        success = await camera_service.initialize_camera(
            camera_id=0,
            source=0,  # Webcam
            fps=2,
            resolution=(1280, 720)
        )

        if success:
            print("✅ Camera initialized successfully!")
            print(f"   Active cameras: {camera_service.get_active_camera_count()}")

            # Test frame capture
            frame = await camera_service.capture_frame(0)
            if frame is not None:
                print(f"✅ Frame capture working! Shape: {frame.shape}")
                return True
        return False

    return asyncio.run(init())


def main():
    print("=" * 60)
    print("  SentinTinel Webcam Initialization")
    print("=" * 60)

    # Check webcam
    if not check_webcam():
        return

    # Initialize through service
    if init_camera_via_service():
        print("\n🎉 SUCCESS! Camera is now active!")
        print("\n📝 Next steps:")
        print("   1. Open http://localhost:3000")
        print("   2. You should see the camera feed")
        print("   3. Use AI Command Center to send monitoring commands:")
        print("      • 'Watch for people'")
        print("      • 'Monitor for movement'")
        print("      • 'Alert if you see anything suspicious'")
        print("\n✨ The surveillance worker will now process frames from your webcam!")
    else:
        print("\n❌ Failed to initialize camera")


if __name__ == "__main__":
    main()
