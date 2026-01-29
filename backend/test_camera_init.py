"""
Test script to initialize webcam for testing camera monitoring
"""
import asyncio
import sys
import cv2
from services.camera_service import camera_service


async def test_camera_init():
    """
    Test camera initialization with webcam
    """
    print("🎥 Testing camera initialization...")

    # Test if webcam is available
    print("\n1. Checking webcam availability...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Webcam not accessible. Please check:")
        print("   - Camera is not in use by another application")
        print("   - Camera permissions are granted")
        print("   - Camera is properly connected")
        return False

    print("✅ Webcam is accessible!")
    cap.release()

    # Initialize camera in camera service
    print("\n2. Initializing camera in surveillance system...")
    camera_id = 0
    success = await camera_service.initialize_camera(
        camera_id=camera_id,
        source=0,  # 0 = default webcam
        fps=2,
        resolution=(1280, 720)
    )

    if success:
        print(f"✅ Camera {camera_id} initialized successfully!")

        # Get camera info
        info = await camera_service.get_camera_info(camera_id)
        print(f"\n📊 Camera Info:")
        print(f"   - Camera ID: {info['camera_id']}")
        print(f"   - Active: {info['is_active']}")
        print(f"   - Resolution: {info['resolution']['width']}x{info['resolution']['height']}")
        print(f"   - FPS: {info['fps']}")
        print(f"   - Source: {info['source']}")

        # Capture a test frame
        print("\n3. Testing frame capture...")
        frame = await camera_service.capture_frame(camera_id)
        if frame is not None:
            print(f"✅ Successfully captured frame! Shape: {frame.shape}")
            print("\n🎉 Camera is ready for monitoring!")
            print("\n📝 Next steps:")
            print("   1. Go to http://localhost:3000")
            print("   2. Use the AI Command Center to send commands like:")
            print("      - 'Watch for people entering'")
            print("      - 'Monitor for movement'")
            print("      - 'Alert me if you see anything unusual'")
            print("\n⚠️  Note: Keep this script running to maintain camera connection")
            print("    Or press Ctrl+C to stop and the camera will remain active in the main server")

            # Keep the script running
            try:
                print("\n⏳ Camera active. Press Ctrl+C to exit...")
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\n\n👋 Stopping camera...")
                await camera_service.stop_camera(camera_id)
                print("✅ Camera stopped successfully!")
        else:
            print("❌ Failed to capture frame")
            return False
    else:
        print(f"❌ Failed to initialize camera {camera_id}")
        return False

    return True


if __name__ == "__main__":
    print("=" * 60)
    print("  SentinTinel Camera Initialization Test")
    print("=" * 60)

    try:
        asyncio.run(test_camera_init())
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
