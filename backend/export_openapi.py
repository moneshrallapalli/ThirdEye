"""
Export OpenAPI/Swagger JSON schema to a file
"""
import json
from pathlib import Path

# Import the FastAPI app
from api import app

def export_openapi_schema():
    """Export the OpenAPI schema to a JSON file"""
    openapi_schema = app.openapi()
    
    output_file = Path(__file__).parent / "openapi.json"
    
    with open(output_file, "w") as f:
        json.dump(openapi_schema, f, indent=2)
    
    print(f"✅ OpenAPI schema exported to: {output_file}")
    print(f"📄 File size: {output_file.stat().st_size} bytes")
    
    # Also print some basic info
    print(f"\n📊 API Information:")
    print(f"   Title: {openapi_schema.get('info', {}).get('title', 'N/A')}")
    print(f"   Version: {openapi_schema.get('info', {}).get('version', 'N/A')}")
    print(f"   Endpoints: {len(openapi_schema.get('paths', {}))}")

if __name__ == "__main__":
    export_openapi_schema()
