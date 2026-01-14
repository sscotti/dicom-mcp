# Cursor IDE Setup with DICOM MCP Server

This guide explains how to configure Cursor IDE to use your DICOM MCP server with persistent system prompts.

> **Important**: For **MCP server development and testing**, **MCP Jam is recommended** as it's specifically designed for that purpose. Cursor is better suited for general code development where you want MCP tools available in context. See "When to Use Each" section below.

## Why Use Cursor?

- ✅ **Persistent System Prompts**: System prompts are saved and persist between sessions
- ✅ **Integrated Development**: Access DICOM tools directly from your IDE while coding
- ✅ **Better Context**: Cursor understands your codebase and can use DICOM tools in context
- ✅ **No Manual Copy-Paste**: System prompts are configured once and reused
- ⚠️ **Limited MCP Features**: Not as feature-rich as MCP Jam for MCP-specific development/testing

## Setup Instructions

### 1. Configure MCP Server in Cursor

Cursor uses a configuration file at `~/.cursor/mcp.json`. Create or edit this file:

```json
{
  "mcpServers": {
    "dicom-mcp": {
      "command": "/Users/macbookpro/Desktop/dicom-mcp/venv/bin/python",
      "args": [
        "-m",
        "dicom_mcp",
        "/Users/macbookpro/Desktop/dicom-mcp/configuration.yaml"
      ],
      "env": {
        "PYTHONPATH": "/Users/macbookpro/Desktop/dicom-mcp/src"
      },
      "cwd": "/Users/macbookpro/Desktop/dicom-mcp"
    }
  }
}
```

**Note**: Update the paths to match your system. You can use `mcp-config.example.json` as a template.

### 2. Configure OpenAI API Key (Optional)

If you have your own OpenAI API key and want to use ChatGPT models directly (similar to MCP Jam):

**Getting Your API Key from .env File:**

If your OpenAI API key is stored in your project's `.env` file:

1. **Read the key from .env**:
   ```bash
   # On macOS/Linux
   grep OPENAI_API_KEY .env
   
   # Or view the .env file
   cat .env | grep OPENAI_API_KEY
   ```

2. **Copy the API key value** (everything after the `=` sign)

**Configure in Cursor:**

1. **Open Cursor Settings**:
   - Press `Cmd+Shift+J` (macOS) or `Ctrl+Shift+J` (Windows/Linux)
   - Or click the gear icon in the top right

2. **Navigate to Models Section**:
   - In the settings sidebar, select **"Models"**

3. **Enter Your OpenAI API Key**:
   - Scroll to the **"OpenAI API Key"** section
   - Paste your OpenAI API key from the `.env` file into the provided field
   - Click **"Verify"** to confirm your API key is valid
   - Click **"Save"** to apply the changes

4. **Select Model**:
   - After adding your API key, you can select which OpenAI model to use (GPT-4, GPT-4 Turbo, etc.)
   - This will allow Cursor to use your OpenAI API directly

**Benefits**:
- Use ChatGPT models (GPT-4, GPT-4 Turbo, etc.) directly in Cursor
- Similar experience to MCP Jam with ChatGPT
- Still get Cursor's integrated development features
- Your API usage will be billed to your OpenAI account

**Note**: 
- Cursor requires the API key to be entered in its settings UI - it doesn't automatically read from `.env` files
- Some Cursor features may still require Cursor Pro subscription even when using your own API key

### 3. Configure System Prompt in Cursor

Cursor allows you to set system prompts through:

**Option A: Via Cursor Settings**
1. Open Cursor Settings (Cmd/Ctrl + ,)
2. Search for "MCP" or "System Prompt"
3. Add your system prompt in the appropriate field
4. You can copy the content from `system_prompt.txt`

**Option B: Via Cursor Chat Settings**
1. Open the Cursor chat panel
2. Click on the settings/gear icon
3. Look for "System Prompt" or "Custom Instructions"
4. Paste the content from `system_prompt.txt`

**Option C: Use the get_system_prompt Tool** (Easiest!)
1. In Cursor chat, simply ask: **"Get the system prompt"** or **"Use the get_system_prompt tool"**
2. The tool will return the prompt text from `system_prompt.txt`
3. Copy the `prompt` field from the response
4. Paste it into Cursor's system prompt settings (Settings > Models > System Prompt, or Chat Settings)
5. The prompt is now configured and will persist across sessions

### 4. Verify Connection

To verify Cursor is connected to your MCP server:

1. **Check MCP Status**:
   - Open Cursor chat
   - Look for an indicator showing MCP servers are connected
   - Or check Cursor's MCP panel/settings

2. **Test a Tool**:
   - In Cursor chat, ask: "List available DICOM nodes"
   - Or: "Use the list_dicom_nodes tool"
   - You should see the tool being called and returning results

3. **Check Logs**:
   - Cursor may show MCP connection status in its output panel
   - Look for any MCP-related messages or errors

### 5. Recommended System Prompt

Use the prompt from `system_prompt.txt`:

```
You are a medical imaging assistant specialized in DICOM and FHIR workflows. Help users query, analyze, and manage medical imaging data efficiently using the available DICOM tools, including DIMSE, FHIR and DicomWeb.

Key responsibilities:
- Assist with patient, study, series, and instance queries using the DICOM tools.
- Assist with reading, writing and analyzing data using FHIR tools (work in progress).
- Extract and summarize text from DICOM-encapsulated PDF reports
- Help transfer DICOM data between nodes using C-MOVE operations
- Provide clear explanations of DICOM concepts and operations
- Always prioritize data privacy and security

Important reminders:
- This tool is for research and development purposes only
- Never make clinical diagnoses based on the data
- Verify patient information before sharing results
- Use clear, clinical language when appropriate
- Most data is retrieved as JSON, but please present the data in either JSON or a tabular form that is human readable.
- When extracting text from DICOM PDF reports, summarize findings clearly, highlight key measurements and recommendations, and maintain clinical accuracy in your summaries. Organize information in a structured format that's easy to read and understand.
```

## Using DICOM Tools in Cursor

Once configured, you can use DICOM tools naturally in Cursor chat:

**Examples:**
- "Query for patients with name pattern 'DOE*'"
- "Find all CT studies from last week"
- "Extract text from the latest chest X-ray report for patient ID MCP-MRN-0001"
- "What imaging modalities are available in the system?"
- "Move the latest chest CT to the AI analysis server"

Cursor will automatically call the appropriate DICOM MCP tools to fulfill your requests.

## Troubleshooting

### MCP Server Not Connecting

1. **Check Paths**: Verify all paths in `~/.cursor/mcp.json` are correct and use absolute paths
2. **Check Python**: Ensure the Python path points to your venv
3. **Check PYTHONPATH**: Verify the PYTHONPATH environment variable is set correctly
4. **Restart Cursor**: Restart Cursor after making configuration changes

### Tools Not Appearing

1. **Verify Server**: Check that your MCP server starts without errors
2. **Check Logs**: Look at Cursor's output/logs for MCP-related errors
3. **Test Manually**: Try running the server manually to ensure it works:
   ```bash
   cd /path/to/dicom-mcp
   source venv/bin/activate
   python -m dicom_mcp configuration.yaml
   ```

### System Prompt Not Working

1. **Verify Location**: Make sure you set the system prompt in Cursor's settings, not in the chat
2. **Check Format**: Ensure the prompt is properly formatted text
3. **Restart Chat**: Try starting a new chat session after setting the prompt

## LLM Provider Support

**OpenAI API Key Support**: You can configure Cursor to use your own OpenAI API key (see Step 2 above), which gives you:

- ✅ Direct access to ChatGPT models (GPT-4, GPT-4 Turbo, etc.)
- ✅ Similar experience to using ChatGPT in MCP Jam
- ✅ Full control over which OpenAI model to use
- ✅ Your API usage billed directly to your OpenAI account

**Provider Selection**:
- **MCP Jam**: Allows you to easily switch between multiple providers (ChatGPT, Claude, Gemini, Ollama, etc.) in the web interface
- **Cursor with OpenAI API Key**: Uses ChatGPT models directly, but doesn't have the same easy provider switching interface as MCP Jam
- **Cursor without API Key**: Uses Cursor's default AI models

**When to Use Each**:

**For MCP Development & Testing:**
- **MCP Jam is Recommended** ✅
  - Designed specifically for MCP server development and testing
  - Better tool visibility and interaction
  - Easy provider switching for testing
  - More flexible prompt and session management
  - Better debugging of MCP tools

**For General Code Development:**
- **Cursor with OpenAI API Key** ✅
  - When you want AI assistance in your IDE while coding
  - Access to MCP tools while working on code
  - Better codebase context integration
  - Persistent settings

**Best Practice:**
- **Use MCP Jam** for MCP-specific development, testing tools, and provider comparison
- **Use Cursor** for general coding tasks where you occasionally need MCP tools in context
- **Both**: Use MCP Jam to develop/test your MCP server, Cursor for everyday coding with MCP tools available

## Benefits Comparison

| Feature | Cursor | MCP Jam Guest Mode |
|---------|--------|-------------------|
| Persistent System Prompts | ✅ Yes | ❌ No |
| Integrated with Codebase | ✅ Yes | ❌ No |
| Context Awareness | ✅ Yes | ❌ Limited |
| No Account Required | ✅ Yes | ✅ Yes |
| Web Interface | ❌ No | ✅ Yes |
| Multiple LLM Provider Selection | ⚠️ Limited (OpenAI with API key) | ✅ Yes (ChatGPT, Claude, Gemini, Ollama, etc.) |
| Provider Switching | ❌ No | ✅ Yes (in Playground) |
| Use Your Own OpenAI API Key | ✅ Yes | ✅ Yes |

## See Also

- [Cursor MCP Documentation](https://cursor.com/docs/context/mcp#what-is-mcp)
- `mcp-config.example.json` - Template configuration file
- `system_prompt.txt` - Recommended system prompt
- `README.md` - Main project documentation

