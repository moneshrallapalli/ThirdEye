import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from dotenv import load_dotenv
    import google.generativeai as genai
except ImportError:
    print("❌ Required packages not installed")
    print("Please run: pip install -r requirements.txt")
    sys.exit(1)

def test_api_key():
    """Test if Gemini API key is configured correctly"""

    print("=" * 60)
    print("🔑 GEMINI API KEY VALIDATOR")
    print("=" * 60)
    print()

    # Load environment
    env_path = os.path.join(os.path.dirname(__file__), '.env')

    if not os.path.exists(env_path):
        print("❌ ERROR: .env file not found!")
        print(f"   Expected location: {env_path}")
        print()
        print("To fix:")
        print("  1. Copy .env.example to .env")
        print("  2. Add your Gemini API key to .env")
        print()
        print("Commands:")
        print("  cp .env.example .env")
        print("  nano .env")
        return False

    load_dotenv(env_path)
    api_key = os.getenv('GEMINI_API_KEY')

    # Check if API key exists
    if not api_key:
        print("❌ ERROR: GEMINI_API_KEY not found in .env file!")
        print()
        print("To fix:")
        print("  1. Open backend/.env in a text editor")
        print("  2. Find the line: GEMINI_API_KEY=your_api_key_here")
        print("  3. Replace 'your_api_key_here' with your actual API key")
        print("  4. Save the file")
        print()
        print("Get your API key from:")
        print("  https://aistudio.google.com/app/apikey")
        return False

    # Check if it's still the placeholder
    if api_key in ['your_api_key_here', 'your_gemini_api_key_here']:
        print("❌ ERROR: API key still has placeholder value!")
        print(f"   Current value: {api_key}")
        print()
        print("To fix:")
        print("  1. Go to: https://aistudio.google.com/app/apikey")
        print("  2. Click 'Get API key' or 'Create API key'")
        print("  3. Copy your API key (starts with 'AIzaSy')")
        print("  4. Replace the placeholder in backend/.env")
        return False

    # Check format
    if not api_key.startswith('AIzaSy'):
        print("⚠️  WARNING: API key doesn't start with 'AIzaSy'")
        print(f"   Current value starts with: {api_key[:10]}...")
        print()
        print("This might not be a valid Gemini API key.")
        print("Double-check you copied it correctly from:")
        print("  https://aistudio.google.com/app/apikey")
        print()

    print(f"✅ API key found: {api_key[:20]}...")
    print(f"   Length: {len(api_key)} characters")
    print()

    # Test the API key
    print("Testing API key with Gemini API...")
    print()

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')

        print("Sending test request to Gemini...")
        response = model.generate_content("Say 'API key is working!' in exactly those words.")

        print()
        print("=" * 60)
        print("✅ SUCCESS! API KEY IS VALID AND WORKING!")
        print("=" * 60)
        print()
        print(f"Gemini responded: {response.text}")
        print()
        print("🎉 You're all set! Start the application with:")
        print("   ./start.sh       (Linux/Mac)")
        print("   start.bat        (Windows)")
        print()
        return True

    except Exception as e:
        error_msg = str(e)
        print()
        print("=" * 60)
        print("❌ API KEY TEST FAILED")
        print("=" * 60)
        print()
        print(f"Error: {error_msg}")
        print()

        # Provide specific guidance based on error
        if "API_KEY_INVALID" in error_msg or "invalid" in error_msg.lower():
            print("This API key is not valid.")
            print()
            print("To fix:")
            print("  1. Go to: https://aistudio.google.com/app/apikey")
            print("  2. Check if your API key is active")
            print("  3. Or create a new API key")
            print("  4. Update backend/.env with the new key")

        elif "quota" in error_msg.lower() or "limit" in error_msg.lower():
            print("API quota or rate limit exceeded.")
            print()
            print("To fix:")
            print("  1. Wait a few minutes and try again")
            print("  2. Check your quota at: https://aistudio.google.com/")
            print("  3. Consider reducing CAMERA_FPS in .env")

        elif "PERMISSION_DENIED" in error_msg:
            print("Permission denied - API key may not have access to Gemini.")
            print()
            print("To fix:")
            print("  1. Check API restrictions in Google AI Studio")
            print("  2. Make sure Gemini API is enabled")
            print("  3. Try creating a new unrestricted API key")

        else:
            print("Unexpected error occurred.")
            print()
            print("Troubleshooting steps:")
            print("  1. Check your internet connection")
            print("  2. Verify API key at: https://aistudio.google.com/app/apikey")
            print("  3. Try creating a new API key")
            print("  4. Check the full error message above")

        print()
        return False


if __name__ == "__main__":
    success = test_api_key()
    sys.exit(0 if success else 1)
