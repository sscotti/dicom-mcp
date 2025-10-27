#!/usr/bin/env python3
"""
Test script to verify .env setup is working correctly.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

def test_env_setup():
    """Test that .env file loading works correctly."""
    print("🧪 Testing .env setup...")
    
    # Check if .env.example exists
    if not Path('.env.example').exists():
        print("❌ .env.example file not found")
        return False
    else:
        print("✅ .env.example file exists")
    
    # Check if .env exists
    if not Path('.env').exists():
        print("⚠️  .env file not found - you need to create it from .env.example")
        print("   Run: cp .env.example .env")
        print("   Then edit .env and add your OPENAI_API_KEY")
        return False
    else:
        print("✅ .env file exists")
    
    # Load .env file
    load_dotenv('.env')
    print("✅ Loaded .env file")
    
    # Check for required environment variables
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY not found in .env file")
        return False
    elif api_key == 'your-openai-api-key-here':
        print("⚠️  OPENAI_API_KEY is still the placeholder value")
        print("   Please edit .env and add your actual OpenAI API key")
        return False
    else:
        # Mask the key for security
        masked_key = api_key[:10] + "..." + api_key[-4:] if len(api_key) > 14 else "***"
        print(f"✅ OPENAI_API_KEY found: {masked_key}")
    
    # Test configuration loading
    try:
        sys.path.insert(0, str(Path('src')))
        from dicom_mcp.config import load_config
        config = load_config('configuration.yaml')
        print("✅ Configuration loaded successfully")
        print(f"   Current DICOM node: {config.current_node}")
        print(f"   OpenAI config present: {config.openai is not None}")
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        return False
    
    # Test OpenAI client import
    try:
        from dicom_mcp.openai_client import OpenAIDicomClient
        print("✅ OpenAI client import successful")
    except Exception as e:
        print(f"❌ Error importing OpenAI client: {e}")
        return False
    
    print("\n🎉 All tests passed! Your .env setup is working correctly.")
    print("\nNext steps:")
    print("1. Start your DICOM server (Orthanc): cd tests && docker-compose up -d")
    print("2. Run the interactive chat: python -m dicom_mcp.openai_chat configuration.yaml")
    print("3. Or run the example: python examples/openai_dicom_example.py")
    
    return True

if __name__ == "__main__":
    success = test_env_setup()
    sys.exit(0 if success else 1)
