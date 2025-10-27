#!/usr/bin/env python3
"""
Example script demonstrating OpenAI + DICOM MCP integration.

This script shows how to use the OpenAI DICOM client to interact
with DICOM servers using natural language queries.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add the src directory to the path so we can import dicom_mcp
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dicom_mcp.openai_client import OpenAIDicomClient

def main():
    """Run example OpenAI + DICOM interactions."""
    
    # Load .env file if it exists
    project_root = Path(__file__).parent.parent
    env_file = project_root / '.env'
    if env_file.exists():
        load_dotenv(env_file)
        print(f"✅ Loaded environment variables from {env_file}")
    
    # Check for API key
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ Please set OPENAI_API_KEY environment variable")
        print("\nTo set it up:")
        print("1. Copy .env.example to .env:")
        print("   cp .env.example .env")
        print("2. Edit .env and add your OpenAI API key:")
        print("   OPENAI_API_KEY=your-actual-api-key-here")
        return
    
    # Configuration file path
    config_path = Path(__file__).parent.parent / "configuration.yaml"
    
    if not config_path.exists():
        print(f"❌ Configuration file not found: {config_path}")
        print("Please make sure configuration.yaml exists in the project root.")
        return
    
    try:
        # Initialize the OpenAI DICOM client
        print("🔧 Initializing OpenAI DICOM client...")
        client = OpenAIDicomClient(str(config_path))
        print("✅ Client initialized successfully!")
        
        # Example queries to demonstrate functionality
        example_queries = [
            "Can you check if the DICOM server is connected?",
            "Search for any patients with the name pattern 'DOE*'",
            "Find all CT studies from the last month",
            "What types of imaging studies are available in the system?",
        ]
        
        print("\n" + "="*80)
        print("🏥 OpenAI + DICOM MCP Integration Examples")
        print("="*80)
        
        for i, query in enumerate(example_queries, 1):
            print(f"\n📝 Example {i}: {query}")
            print("-" * 60)
            
            # Send query to OpenAI
            response = client.chat(query)
            
            if response['success']:
                print(f"🤖 Response: {response['response']}")
                
                # Show tool calls if any were made
                if response['tool_calls']:
                    print(f"\n🔧 Tools used: {len(response['tool_calls'])} function call(s)")
                    for j, tool_call in enumerate(response['tool_calls'], 1):
                        function_name = tool_call['function_name']
                        result = tool_call['result']
                        success_icon = "✅" if result.get('success') else "❌"
                        print(f"   {j}. {function_name}: {success_icon}")
                        
                        # Show result summary
                        if result.get('success') and 'count' in result:
                            print(f"      Found {result['count']} result(s)")
                        elif not result.get('success'):
                            print(f"      Error: {result.get('error', 'Unknown error')}")
            else:
                print(f"❌ Error: {response.get('error', 'Unknown error')}")
            
            print()
        
        print("="*80)
        print("✨ Examples completed! You can now use the interactive chat:")
        print("   python -m dicom_mcp.openai_chat configuration.yaml")
        print("="*80)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print("\nTroubleshooting:")
        print("1. Make sure OPENAI_API_KEY is set")
        print("2. Ensure DICOM server (Orthanc) is running")
        print("3. Check configuration.yaml settings")
        print("4. Install dependencies: pip install -e .")

if __name__ == "__main__":
    main()
