#!/usr/bin/env python3
"""
OpenAI Chat Interface for DICOM MCP.

This module provides a command-line chat interface that integrates
OpenAI's ChatGPT with DICOM MCP tools for medical image analysis.
"""
import sys
import json
import logging
from typing import List, Dict, Any
from pathlib import Path
from .openai_client import OpenAIDicomClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class OpenAIChatInterface:
    """Interactive chat interface with OpenAI and DICOM tools."""
    
    def __init__(self, config_path: str):
        """Initialize the chat interface.
        
        Args:
            config_path: Path to the DICOM MCP configuration file
        """
        try:
            self.client = OpenAIDicomClient(config_path)
            self.conversation_history = []
            logger.info("OpenAI DICOM chat interface initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize chat interface: {str(e)}")
            raise
    
    def display_welcome(self):
        """Display welcome message and instructions."""
        print("\n" + "="*80)
        print("🏥 DICOM MCP + OpenAI ChatGPT Integration")
        print("="*80)
        print("\nWelcome! I'm your AI assistant with access to DICOM server tools.")
        print("\nI can help you with:")
        print("• 🔍 Searching for patients, studies, and series")
        print("• 📄 Extracting text from DICOM PDF reports")
        print("• ➡️  Moving DICOM data between servers")
        print("• ⚙️  Managing DICOM server connections")
        print("\nExamples of what you can ask:")
        print('• "Find all CT studies for patient DOE^JOHN"')
        print('• "Show me the latest chest X-ray report for patient ID 12345"')
        print('• "What studies are available from last week?"')
        print('• "Extract the text from this radiology report"')
        print("\nType 'help' for more commands, 'quit' to exit.")
        print("-"*80)
    
    def display_help(self):
        """Display help information."""
        print("\n📋 Available Commands:")
        print("• help - Show this help message")
        print("• quit/exit - Exit the chat")
        print("• clear - Clear conversation history")
        print("• history - Show conversation history")
        print("• status - Check DICOM server connection")
        print("• debug - Toggle debug logging")
        print("\n🔧 DICOM Tools Available:")
        print("• Patient search by ID, name pattern, or birth date")
        print("• Study search by patient, date, modality, or description")
        print("• Series search within studies")
        print("• PDF text extraction from DICOM reports")
        print("• DICOM data movement between servers")
        print("• Server connectivity verification")
        print()
    
    def format_tool_results(self, tool_calls: List[Dict[str, Any]]) -> str:
        """Format tool call results for display."""
        if not tool_calls:
            return ""
        
        result_text = "\n🔧 Tool Calls Made:\n"
        for i, tool_call in enumerate(tool_calls, 1):
            function_name = tool_call['function_name']
            result = tool_call['result']
            
            result_text += f"\n{i}. {function_name}:\n"
            
            if result.get('success'):
                if 'results' in result:
                    count = result.get('count', 0)
                    result_text += f"   ✅ Found {count} result(s)\n"
                    if count > 0 and count <= 3:  # Show details for small result sets
                        for j, item in enumerate(result['results'][:3], 1):
                            result_text += f"      {j}. {self._format_result_item(item)}\n"
                elif 'text_content' in result:
                    text = result['text_content']
                    preview = text[:200] + "..." if len(text) > 200 else text
                    result_text += f"   ✅ Extracted text: {preview}\n"
                elif 'message' in result:
                    result_text += f"   ✅ {result['message']}\n"
                else:
                    result_text += f"   ✅ Success\n"
            else:
                error = result.get('error', 'Unknown error')
                result_text += f"   ❌ Error: {error}\n"
        
        return result_text
    
    def _format_result_item(self, item: Dict[str, Any]) -> str:
        """Format a single result item for display."""
        # Try to create a meaningful summary
        if 'PatientName' in item and 'PatientID' in item:
            return f"Patient: {item['PatientName']} (ID: {item['PatientID']})"
        elif 'StudyDescription' in item and 'StudyDate' in item:
            return f"Study: {item['StudyDescription']} ({item['StudyDate']})"
        elif 'SeriesDescription' in item and 'Modality' in item:
            return f"Series: {item['SeriesDescription']} ({item['Modality']})"
        else:
            # Fallback to showing a few key fields
            key_fields = ['PatientID', 'StudyInstanceUID', 'SeriesInstanceUID', 'Modality']
            parts = []
            for field in key_fields:
                if field in item:
                    parts.append(f"{field}: {item[field]}")
            return ", ".join(parts[:2]) if parts else str(item)
    
    def run(self):
        """Run the interactive chat interface."""
        self.display_welcome()
        
        debug_mode = False
        
        while True:
            try:
                # Get user input
                user_input = input("\n💬 You: ").strip()
                
                if not user_input:
                    continue
                
                # Handle special commands
                if user_input.lower() in ['quit', 'exit']:
                    print("\n👋 Goodbye! Thank you for using DICOM MCP + OpenAI.")
                    break
                
                elif user_input.lower() == 'help':
                    self.display_help()
                    continue
                
                elif user_input.lower() == 'clear':
                    self.conversation_history = []
                    print("🧹 Conversation history cleared.")
                    continue
                
                elif user_input.lower() == 'history':
                    if self.conversation_history:
                        print("\n📜 Conversation History:")
                        for i, msg in enumerate(self.conversation_history, 1):
                            role = msg['role'].title()
                            content = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
                            print(f"{i}. {role}: {content}")
                    else:
                        print("📜 No conversation history yet.")
                    continue
                
                elif user_input.lower() == 'status':
                    print("🔍 Checking DICOM server connection...")
                    success, message = self.client.dicom_client.verify_connection()
                    status_icon = "✅" if success else "❌"
                    print(f"{status_icon} {message}")
                    continue
                
                elif user_input.lower() == 'debug':
                    debug_mode = not debug_mode
                    level = logging.DEBUG if debug_mode else logging.INFO
                    logging.getLogger().setLevel(level)
                    status = "enabled" if debug_mode else "disabled"
                    print(f"🐛 Debug logging {status}")
                    continue
                
                # Send message to OpenAI
                print("🤖 Assistant: ", end="", flush=True)
                
                response_data = self.client.chat(user_input, self.conversation_history)
                
                if response_data['success']:
                    # Display the response
                    print(response_data['response'])
                    
                    # Display tool results if any
                    if response_data['tool_calls']:
                        tool_summary = self.format_tool_results(response_data['tool_calls'])
                        if debug_mode:
                            print(tool_summary)
                    
                    # Update conversation history
                    self.conversation_history.append({"role": "user", "content": user_input})
                    self.conversation_history.append({"role": "assistant", "content": response_data['response']})
                    
                    # Keep history manageable (last 10 exchanges)
                    if len(self.conversation_history) > 20:
                        self.conversation_history = self.conversation_history[-20:]
                
                else:
                    print(f"❌ Error: {response_data.get('error', 'Unknown error')}")
                    print(response_data['response'])
            
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye! Thank you for using DICOM MCP + OpenAI.")
                break
            
            except Exception as e:
                logger.error(f"Error in chat loop: {str(e)}")
                print(f"\n❌ An error occurred: {str(e)}")
                print("Please try again or type 'help' for assistance.")

def main():
    """Main entry point for the OpenAI chat interface."""
    if len(sys.argv) != 2:
        print("Usage: python -m dicom_mcp.openai_chat <config_path>")
        print("Example: python -m dicom_mcp.openai_chat configuration.yaml")
        sys.exit(1)
    
    config_path = sys.argv[1]
    
    # Check if config file exists
    if not Path(config_path).exists():
        print(f"❌ Configuration file not found: {config_path}")
        sys.exit(1)
    
    # Check for OpenAI API key
    import os
    from dotenv import load_dotenv
    
    # Try to load .env file
    if Path('.env').exists():
        load_dotenv('.env')
        print("✅ Loaded .env file")
    
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ OPENAI_API_KEY environment variable is required")
        print("\nTo set it up:")
        print("1. Copy .env.example to .env:")
        print("   cp .env.example .env")
        print("2. Edit .env and add your OpenAI API key:")
        print("   OPENAI_API_KEY=your-actual-api-key-here")
        print("3. Or set it directly:")
        print("   export OPENAI_API_KEY='your-api-key-here'")
        sys.exit(1)
    
    try:
        chat_interface = OpenAIChatInterface(config_path)
        chat_interface.run()
    except Exception as e:
        logger.error(f"Failed to start chat interface: {str(e)}")
        print(f"❌ Failed to start: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
