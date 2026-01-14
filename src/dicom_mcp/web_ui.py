"""
Custom Web UI for DICOM MCP Server.
Self-contained web interface with prompts, tools, and interactive chat.
"""
import asyncio
import copy
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Any, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager

from .server import create_dicom_mcp_server
from .config import load_config
from .dicom_client import DicomClient
from .fhir_client import FhirClient
from .mysql_client import MiniRisClient, MiniRisConnectionSettings
from .resources import load_resource_catalog
from mcp.server.fastmcp import Context

logger = logging.getLogger(__name__)

# LLM integration
try:
    from openai import OpenAI
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    logger.warning("OpenAI not available. LLM features will be disabled.")

# OpenAI model selection
DEFAULT_OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_MODEL_OVERRIDE: Optional[str] = None

# Keep this list small + practical; allow custom model via dropdown "Custom…"
OPENAI_MODEL_OPTIONS = [
    "gpt-4o-mini",
    "gpt-4o",
]


def get_openai_model() -> str:
    return OPENAI_MODEL_OVERRIDE or os.getenv("OPENAI_MODEL") or DEFAULT_OPENAI_MODEL


def to_json_safe(value: Any) -> Any:
    """Convert tool results to JSON-serializable structures (dates, datetimes, decimals, etc.)."""
    return jsonable_encoder(value)


# Tools rendered as dedicated widgets (suppress assistant text)
WIDGET_ONLY_TOOLS = {
    "list_mini_ris_patients",
    "list_dicom_nodes",
    "list_saved_resources",
}


def should_suppress_response(tool_calls: List[Dict[str, Any]]) -> bool:
    """Return True if UI widgets already render the response."""
    for call in tool_calls:
        if call.get("tool") in WIDGET_ONLY_TOOLS:
            return True
    return False


# Global MCP server instance and context
mcp_server = None
mcp_lifespan_context = None
mcp_lifespan_manager = None


class ToolCallRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]


class PromptUpdateRequest(BaseModel):
    prompt: str


class ModelUpdateRequest(BaseModel):
    model: str


@asynccontextmanager
async def lifespan_manager(app: FastAPI):
    """Manage MCP server lifespan."""
    global mcp_server, mcp_lifespan_context
    
    config_path = os.getenv("MCP_CONFIG_PATH", "configuration.yaml")
    if not Path(config_path).exists():
        config_path = Path(__file__).parent.parent.parent / "configuration.yaml"
    
    if not Path(config_path).exists():
        raise RuntimeError(f"Configuration file not found: {config_path}")
    
    # Create the server - this will create the lifespan function internally
    mcp_server = create_dicom_mcp_server(str(config_path))
    
    # We need to manually create the context by calling the lifespan function
    # FastMCP stores the lifespan function, but we need to call it directly
    # Let's create the context manually by duplicating the initialization logic
    
    config_path_obj = Path(config_path).resolve()
    config = load_config(str(config_path_obj))
    current_node = config.nodes[config.current_node]
    
    client = DicomClient(
        host=current_node.host,
        port=current_node.port,
        calling_aet=config.calling_aet,
        called_aet=current_node.ae_title
    )
    
    fhir_client = None
    fhir_config = None
    
    if config.fhir_servers and config.current_fhir:
        if config.current_fhir in config.fhir_servers:
            fhir_config = config.fhir_servers[config.current_fhir]
        elif config.fhir_servers:
            config.current_fhir = list(config.fhir_servers.keys())[0]
            fhir_config = config.fhir_servers[config.current_fhir]
    elif config.fhir:
        fhir_config = config.fhir
    
    if fhir_config:
        api_key = fhir_config.api_key or os.getenv("SIIM_API_KEY")
        fhir_client = FhirClient(
            base_url=fhir_config.base_url,
            api_key=api_key
        )
    
    mini_ris_client = None
    resources_dir = config_path_obj.parent / "resources"
    resource_catalog = load_resource_catalog(resources_dir)
    if config.mini_ris:
        try:
            mini_ris_settings = MiniRisConnectionSettings(
                host=config.mini_ris.host,
                port=config.mini_ris.port,
                user=config.mini_ris.user,
                password=config.mini_ris.password,
                database=config.mini_ris.database,
                pool_size=config.mini_ris.pool_size,
            )
            mini_ris_client = MiniRisClient(mini_ris_settings)
            mini_ris_client.ping()
        except Exception:
            pass  # Optional, continue without mini-RIS
    
    from .server import DicomContext
    mcp_lifespan_context = DicomContext(
        config=config,
        client=client,
        fhir_client=fhir_client,
        mini_ris_client=mini_ris_client,
        resources=resource_catalog,
    )
    
    yield
    
    mcp_lifespan_context = None


app = FastAPI(
    title="MCP-FHIR-Orthanc",
    version="1.0.0",
    lifespan=lifespan_manager
)


@app.get("/", response_class=HTMLResponse)
async def get_ui():
    """Serve the main web UI."""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MCP-FHIR-Orthanc</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #0d1117;
            color: #e6edf3;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        
        .header {
            background: #161b22;
            border-bottom: 1px solid #30363d;
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        a[target=_blank] {
            color: yellow;
        }
        
        .header h1 {
            font-size: 1.5rem;
            color: #58a6ff;
        }
        
        .header .status {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .status-indicator {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #238636;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .container {
            display: grid;
            grid-template-columns: 300px 1fr 400px;
            height: calc(100vh - 70px);
            gap: 1px;
            background: #30363d;
        }
        
        .sidebar {
            background: #161b22;
            padding: 1rem;
            overflow-y: auto;
        }
        
        .sidebar h2 {
            font-size: 1rem;
            margin-bottom: 1rem;
            color: #58a6ff;
            border-bottom: 1px solid #30363d;
            padding-bottom: 0.5rem;
        }
        
        .sidebar-section {
            margin-bottom: 2rem;
        }
        
        .sidebar-button {
            width: 100%;
            padding: 0.75rem;
            margin-bottom: 0.5rem;
            background: #21262d;
            border: 1px solid #30363d;
            border-radius: 6px;
            color: #e6edf3;
            cursor: pointer;
            text-align: left;
            transition: all 0.2s;
        }
        
        .sidebar-button:hover {
            background: #30363d;
            border-color: #58a6ff;
        }
        
        .sidebar-button.active {
            background: #1f6feb;
            border-color: #58a6ff;
        }
        
        .main-content {
            background: #0d1117;
            display: flex;
            flex-direction: column;
            padding: 1rem;
            overflow-y: auto;
        }
        
        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 1rem;
            margin-bottom: 1rem;
        }
        
        .message {
            margin-bottom: 1.5rem;
            padding: 1rem;
            border-radius: 8px;
            background: #161b22;
            border: 1px solid #30363d;
        }
        
        .message.user {
            background: #1f6feb;
            border-color: #58a6ff;
        }
        
        .message.assistant {
            background: #161b22;
        }
        
        .message-tool {
            background: #21262d;
            border-left: 3px solid #f85149;
            padding: 0.75rem;
            margin-top: 0.5rem;
            font-family: 'Courier New', monospace;
            font-size: 0.9rem;
        }
        
        .chat-input-container {
            display: flex;
            gap: 0.5rem;
            padding: 1rem;
            background: #161b22;
            border-top: 1px solid #30363d;
        }
        
        .chat-input {
            flex: 1;
            padding: 0.75rem;
            background: #0d1117;
            border: 1px solid #30363d;
            border-radius: 6px;
            color: #e6edf3;
            font-size: 1rem;
            font-family: inherit;
        }
        
        .chat-input:focus {
            outline: none;
            border-color: #58a6ff;
        }
        
        .send-button {
            padding: 0.75rem 1.5rem;
            background: #238636;
            border: none;
            border-radius: 6px;
            color: white;
            cursor: pointer;
            font-weight: 500;
            transition: background 0.2s;
        }
        
        .send-button:hover {
            background: #2ea043;
        }
        
        .send-button:disabled {
            background: #30363d;
            cursor: not-allowed;
        }
        
        .right-panel {
            background: #161b22;
            padding: 1rem;
            overflow-y: auto;
            border-left: 1px solid #30363d;
        }
        
        .panel-content {
            display: none;
        }
        
        .panel-content.active {
            display: block;
        }
        
        .tool-item {
            padding: 0.75rem;
            margin-bottom: 0.5rem;
            background: #21262d;
            border: 1px solid #30363d;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .tool-item:hover {
            background: #30363d;
            border-color: #58a6ff;
        }
        
        .tool-name {
            font-weight: 600;
            color: #58a6ff;
            margin-bottom: 0.25rem;
        }
        
        .tool-description {
            font-size: 0.85rem;
            color: #8b949e;
        }
        
        textarea {
            width: 100%;
            min-height: 300px;
            padding: 0.75rem;
            background: #0d1117;
            border: 1px solid #30363d;
            border-radius: 6px;
            color: #e6edf3;
            font-family: 'Courier New', monospace;
            font-size: 0.9rem;
            resize: vertical;
        }
        
        textarea:focus {
            outline: none;
            border-color: #58a6ff;
        }
        
        .save-button {
            margin-top: 1rem;
            padding: 0.75rem 1.5rem;
            background: #238636;
            border: none;
            border-radius: 6px;
            color: white;
            cursor: pointer;
            font-weight: 500;
        }
        
        .save-button:hover {
            background: #2ea043;
        }
        
        .json-display {
            background: #0d1117;
            border: 1px solid #30363d;
            border-radius: 6px;
            padding: 1rem;
            font-family: 'Courier New', monospace;
            font-size: 0.85rem;
            white-space: pre-wrap;
            word-wrap: break-word;
            max-height: 400px;
            overflow-y: auto;
        }
        
        .loading {
            display: inline-block;
            width: 12px;
            height: 12px;
            border: 2px solid #30363d;
            border-top-color: #58a6ff;
            border-radius: 50%;
            animation: spin 0.6s linear infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .llm-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.25rem 0.6rem;
            border-radius: 999px;
            border: 1px solid #30363d;
            background: #0d1117;
            font-weight: 600;
            font-size: 0.95rem;
            color: #e6edf3;
            margin-left: 0.75rem;
        }

        .llm-pill.ok {
            border-color: rgba(88, 166, 255, 0.6);
            box-shadow: 0 0 0 2px rgba(88, 166, 255, 0.15);
        }

        .llm-pill.warn {
            border-color: rgba(248, 81, 73, 0.6);
            box-shadow: 0 0 0 2px rgba(248, 81, 73, 0.15);
        }

        .llm-model-select {
            margin-left: 0.5rem;
            background: #21262d;
            border: 1px solid #30363d;
            color: #e6edf3;
            padding: 0.35rem 0.5rem;
            border-radius: 6px;
            font-size: 0.9rem;
        }

        .llm-model-select:focus {
            outline: none;
            border-color: #58a6ff;
        }

        .processing-indicator {
            display: none;
            margin-bottom: 0.75rem;
            padding: 0.75rem 1rem;
            border: 1px solid #30363d;
            border-radius: 8px;
            background: #161b22;
            color: #8b949e;
            font-size: 0.9rem;
            align-items: center;
            gap: 0.5rem;
        }

        .modal-backdrop {
            position: fixed;
            inset: 0;
            background: rgba(13, 17, 23, 0.75);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 999;
        }

        .modal-content {
            background: #0d1117;
            border: 1px solid #30363d;
            border-radius: 12px;
            width: min(900px, 90vw);
            max-height: 85vh;
            padding: 1.25rem;
            display: flex;
            flex-direction: column;
        }

        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.75rem;
        }

        .modal-header h3 {
            margin: 0;
            font-size: 1.1rem;
            color: #58a6ff;
        }

        .modal-close {
            cursor: pointer;
            background: none;
            border: none;
            color: #8b949e;
            font-size: 1.1rem;
        }

        .modal-body {
            flex: 1;
            overflow: auto;
        }

        .table-card {
            margin-top: 0.75rem;
            border: 1px solid #30363d;
            border-radius: 8px;
            overflow: auto;
            max-height: 320px;
        }

        .table-card table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
        }

        .table-card th, .table-card td {
            border-bottom: 1px solid #30363d;
            padding: 0.65rem 0.75rem;
            text-align: left;
        }

        .table-card th {
            background: #161b22;
            font-weight: 600;
        }

        .table-card tr:nth-child(even) td {
            background: #0f141c;
        }

        .result-toolbar {
            margin-top: 0.5rem;
            display: flex;
            gap: 0.5rem;
        }

        .toolbar-button {
            padding: 0.35rem 0.75rem;
            background: #21262d;
            border: 1px solid #30363d;
            border-radius: 6px;
            color: #e6edf3;
            cursor: pointer;
            font-size: 0.85rem;
        }

        .toolbar-button:hover {
            border-color: #58a6ff;
        }

        .resource-card {
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 0.85rem;
            margin-bottom: 0.75rem;
            background: #0f141c;
        }

        .resource-card h3 {
            margin: 0;
            font-size: 1rem;
            color: #58a6ff;
        }

        .resource-meta {
            font-size: 0.8rem;
            color: #8b949e;
            margin: 0.4rem 0;
        }

        .resource-actions {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
            margin-top: 0.5rem;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🏥 MCP-FHIR-Orthanc</h1>
        <div class="status">
            <div class="status-indicator" id="connection-status"></div>
            <span id="connection-text">Connected</span>
            <span class="llm-pill" id="llm-pill">
                <span id="llm-indicator">🤖</span>
                <span id="llm-text">LLM: Checking…</span>
            </span>
            <select class="llm-model-select" id="llm-model-select" title="Select OpenAI model">
                <option value="" disabled selected>Model…</option>
            </select>
        </div>
    </div>
    
    <div class="modal-backdrop" id="json-modal">
        <div class="modal-content">
            <div class="modal-header">
                <h3 id="json-modal-title">JSON Output</h3>
                <button class="modal-close" onclick="closeJsonModal()">✕</button>
            </div>
            <div class="modal-body">
                <pre class="json-display" id="json-modal-content"></pre>
            </div>
        </div>
    </div>
    
    <div class="container">
        <div class="sidebar">
            <div class="sidebar-section">
                <h2>Views</h2>
                <button class="sidebar-button active" onclick="showPanel('chat')">💬 Chat</button>
                <button class="sidebar-button" onclick="showPanel('tools')">🛠️ Tools</button>
                <button class="sidebar-button" onclick="showPanel('prompts')">📝 Prompts</button>
                <button class="sidebar-button" onclick="showPanel('resources')">📦 Resources</button>
            </div>
        </div>
        
        <div class="main-content">
            <div id="chat-panel" class="panel-content active">
                <div class="processing-indicator" id="processing-indicator">
                    <span class="loading"></span>
                    <span>Processing...</span>
                </div>
                <div class="chat-messages" id="chat-messages"></div>
                <div class="chat-input-container">
                    <input type="text" class="chat-input" id="chat-input" placeholder="Ask about DICOM data, query patients, extract reports..." onkeypress="handleKeyPress(event)">
                    <button class="send-button" onclick="sendMessage()">Send</button>
                </div>
            </div>
        </div>
        
        <div class="right-panel">
            <div id="tools-panel" class="panel-content">
                <h2>Available Tools</h2>
                <div id="tools-list"></div>
            </div>
            
            <div id="prompts-panel" class="panel-content">
                <h2>System Prompt</h2>
                <textarea id="prompt-editor"></textarea>
                <button class="save-button" onclick="savePrompt()">Save Prompt</button>
            </div>
            
            <div id="resources-panel" class="panel-content">
                <h2>Resources</h2>
                <div id="resources-list"></div>
            </div>
        </div>
    </div>
    
    <script>
        let currentPanel = 'chat';
        
        function showPanel(panel) {
            // Update sidebar buttons
            document.querySelectorAll('.sidebar-button').forEach(btn => {
                btn.classList.remove('active');
            });
            event.target.classList.add('active');
            
            // Update panel visibility
            document.querySelectorAll('.panel-content').forEach(p => {
                p.classList.remove('active');
            });
            
            currentPanel = panel;
            
            if (panel === 'chat') {
                document.getElementById('chat-panel').classList.add('active');
            } else {
                document.getElementById(panel + '-panel').classList.add('active');
                if (panel === 'tools') {
                    loadTools();
                } else if (panel === 'prompts') {
                    loadPrompt();
                } else if (panel === 'resources') {
                    loadResources();
                }
            }
        }
        
        async function loadTools() {
            try {
                const response = await fetch('/api/tools');
                const tools = await response.json();
                const toolsList = document.getElementById('tools-list');
                toolsList.innerHTML = '';
                
                tools.forEach(tool => {
                    const toolDiv = document.createElement('div');
                    toolDiv.className = 'tool-item';
                    toolDiv.innerHTML = `
                        <div class="tool-name">${tool.name}</div>
                        <div class="tool-description">${tool.description || 'No description'}</div>
                    `;
                    toolDiv.onclick = () => showToolDetails(tool);
                    toolsList.appendChild(toolDiv);
                });
            } catch (error) {
                console.error('Error loading tools:', error);
            }
        }
        
        async function loadPrompt() {
            try {
                const response = await fetch('/api/prompt');
                const data = await response.json();
                document.getElementById('prompt-editor').value = data.prompt || '';
            } catch (error) {
                console.error('Error loading prompt:', error);
            }
        }
        
        async function savePrompt() {
            const prompt = document.getElementById('prompt-editor').value;
            try {
                const response = await fetch('/api/prompt', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt })
                });
                if (response.ok) {
                    alert('Prompt saved successfully!');
                }
            } catch (error) {
                console.error('Error saving prompt:', error);
                alert('Error saving prompt');
            }
        }
        
        async function loadResources() {
            const container = document.getElementById('resources-list');
            container.innerHTML = '<p>Loading resources...</p>';
            try {
                const response = await fetch('/api/resources');
                const data = await response.json();
                const resources = data.resources || [];
                if (resources.length === 0) {
                    container.innerHTML = '<p>No saved resources yet.</p>';
                    return;
                }
                container.innerHTML = '';
                resources.forEach(res => {
                    const card = document.createElement('div');
                    card.className = 'resource-card';
                    const tags = (res.tags || []).map(tag => `<span class="chat-tag">${tag}</span>`).join(' ');
                    const hasLocal = res.has_local_content;
                    const tagsHtml = (res.tags || []).map(tag => `<span class="chat-tag">${tag}</span>`).join(' ');
                    card.innerHTML = `
                        <h3>${res.name}</h3>
                        <div class="resource-meta">${res.description || ''}</div>
                        <div class="resource-meta">Media type: ${res.media_type || 'text/plain'} • Size: ${formatBytes(res.size_bytes || 0)}</div>
                        ${res.homepage ? `<div class="resource-meta">Homepage: <a href="${res.homepage}" target="_blank">${res.homepage}</a></div>` : ''}
                        <div class="resource-meta">${tagsHtml}</div>
                        <div class="resource-actions">
                            ${hasLocal ? `<button class="toolbar-button" onclick="viewResource('${res.id}')">View</button>` : ''}
                            ${hasLocal ? `<button class="toolbar-button" onclick="downloadResource('${res.id}')">Download</button>` : ''}
                            ${!hasLocal && res.homepage ? `<button class="toolbar-button" onclick="openResourceLink('${res.homepage}')">Open Site</button>` : ''}
                        </div>
                    `;
                    container.appendChild(card);
                });
            } catch (error) {
                container.innerHTML = `<p>Error loading resources: ${error.message}</p>`;
            }
        }
        
        function showToolDetails(tool) {
            // Could open a modal or show in chat
            addMessage('assistant', `Tool: ${tool.name}\\n${tool.description}`);
            showPanel('chat');
        }
        
        function handleKeyPress(event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                sendMessage();
            }
        }
        
        async function sendMessage() {
            const input = document.getElementById('chat-input');
            const message = input.value.trim();
            if (!message) return;
            
            input.value = '';
            addMessage('user', message);
            
            const processingIndicator = document.getElementById('processing-indicator');
            if (processingIndicator) processingIndicator.style.display = 'flex';
            
            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message })
                });
                
                const data = await response.json();
                
                if (data.tool_calls && data.tool_calls.length > 0) {
                    data.tool_calls.forEach(toolCall => {
                        addToolCall(toolCall.tool, toolCall.arguments, toolCall.result);
                    });
                }
                
                if (data.response && data.response.trim().length > 0) {
                    addMessage('assistant', data.response);
                }
            } catch (error) {
                addMessage('assistant', `Error: ${error.message}`);
            } finally {
                if (processingIndicator) processingIndicator.style.display = 'none';
            }
        }
        
        function addMessage(role, content) {
            const messagesDiv = document.getElementById('chat-messages');
            const messageId = 'msg-' + Date.now();
            const messageDiv = document.createElement('div');
            messageDiv.id = messageId;
            messageDiv.className = `message ${role}`;
            messageDiv.innerHTML = content;
            messagesDiv.appendChild(messageDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
            return messageId;
        }
        
        function addToolCall(toolName, arguments_, result) {
            const messagesDiv = document.getElementById('chat-messages');
            const toolDiv = document.createElement('div');
            toolDiv.className = 'message-tool';
            const formatted = renderToolResult(toolName, result);
            toolDiv.innerHTML = `
                <strong>Tool: ${toolName}</strong><br>
                <strong>Arguments:</strong> <pre>${JSON.stringify(arguments_, null, 2)}</pre><br>
                ${formatted}
            `;
            messagesDiv.appendChild(toolDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
        
        async function checkLLMStatus() {
            try {
                const response = await fetch('/api/llm-status');
                const status = await response.json();
                const indicator = document.getElementById('llm-indicator');
                const text = document.getElementById('llm-text');
                const pill = document.getElementById('llm-pill');
                const select = document.getElementById('llm-model-select');
                
                if (status.available) {
                    indicator.textContent = '🤖';
                    text.textContent = `LLM: ${status.model || 'Ready'}`;
                    pill.classList.remove('warn');
                    pill.classList.add('ok');
                    if (select) select.disabled = false;
                } else {
                    indicator.textContent = '⚠️';
                    if (!status.llm_available) {
                        text.textContent = 'LLM: Not installed';
                    } else if (!status.api_key_set) {
                        text.textContent = 'LLM: No API key (set OPENAI_API_KEY)';
                    } else {
                        text.textContent = 'LLM: Not available';
                    }
                    pill.classList.remove('ok');
                    pill.classList.add('warn');
                    if (select) select.disabled = true;
                }
            } catch (error) {
                console.error('Error checking LLM status:', error);
                document.getElementById('llm-text').textContent = 'LLM: Unknown';
            }
        }

        async function loadModelOptions() {
            try {
                const response = await fetch('/api/llm-model');
                const data = await response.json();
                const select = document.getElementById('llm-model-select');
                if (!select) return;

                // Populate
                select.innerHTML = '';
                (data.options || []).forEach(m => {
                    const opt = document.createElement('option');
                    opt.value = m;
                    opt.textContent = m;
                    select.appendChild(opt);
                });

                // Custom option
                const customOpt = document.createElement('option');
                customOpt.value = '__custom__';
                customOpt.textContent = 'Custom…';
                select.appendChild(customOpt);

                // Select current
                if (data.current) {
                    const exists = (data.options || []).includes(data.current);
                    select.value = exists ? data.current : '__custom__';
                }

                // Persist selection in localStorage
                const saved = localStorage.getItem('openai_model');
                if (saved && saved !== data.current) {
                    await setModel(saved);
                }

                select.onchange = async () => {
                    if (select.value === '__custom__') {
                        const custom = prompt('Enter OpenAI model name:', data.current || '');
                        if (custom && custom.trim()) {
                            await setModel(custom.trim());
                            localStorage.setItem('openai_model', custom.trim());
                        } else {
                            // revert
                            await loadModelOptions();
                        }
                        return;
                    }
                    await setModel(select.value);
                    localStorage.setItem('openai_model', select.value);
                };
            } catch (error) {
                console.error('Error loading model options:', error);
            }
        }

        async function setModel(model) {
            const response = await fetch('/api/llm-model', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model })
            });
            if (!response.ok) {
                const msg = await response.text();
                alert('Failed to set model: ' + msg);
            }
            await checkLLMStatus();
            await loadModelOptions();
        }

        function renderToolResult(toolName, result) {
    if (!result) {
        return '<strong>Result:</strong> <em>No data</em>';
    }
    if (toolName === 'list_mini_ris_patients' && result.patients) {
        return renderPatientTable(result);
    }
    if (toolName === 'list_dicom_nodes' && result.nodes) {
        return renderDicomNodesTable(result);
    }
    if (toolName === 'list_saved_resources' && result.resources) {
        return renderSavedResourcesTable(result);
    }
    return `
        <strong>Result:</strong>
        <pre>${JSON.stringify(result, null, 2)}</pre>
        ${jsonToolbar(toolName, result)}
    `;
}

function renderSavedResourcesTable(data) {
    const resources = data.resources || [];
    const rows = resources.map(r => `
        <tr>
            <td>${r.name}</td>
            <td>${r.media_type || ''}</td>
            <td>${(r.tags||[]).map(t=>`<span class='chat-tag'>${t}</span>`).join(' ')}</td>
            <td>${r.homepage ? `<a href='${r.homepage}' target='_blank'>Open</a>` : (r.relative_path || '')}</td>
        </tr>
    `).join('') || '<tr><td colspan="4"><em>No resources found</em></td></tr>';
    return `
        <div class='table-card'>
            <table>
                <thead>
                    <tr><th>Name</th><th>Type</th><th>Tags</th><th>Link</th></tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        </div>
        ${jsonToolbar('Saved Resources', data)}
    `;
}

function renderDicomNodesTable(data) {
    const nodes = data.nodes || [];
    const current = data.current_node;
    const rows = nodes.map(n => `
        <tr>
            <td>${n}</td>
            <td>${n === current ? `<span style='color:#58a6ff;font-weight:bold'>Current</span>` : ''}</td>
        </tr>`).join('') || '<tr><td colspan="2"><em>No nodes found</em></td></tr>';
    return `
        <div class="table-card">
            <table>
                <thead>
                    <tr><th>Node Name</th><th>Status</th></tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        </div>
        ${jsonToolbar('DICOM Nodes JSON', data)}
    `;
}

        function renderPatientTable(data) {
            const rows = (data.patients || []).map(p => `
                <tr>
                    <td>${p.patient_id}</td>
                    <td>${p.mrn}</td>
                    <td>${p.given_name || ''} ${p.family_name || ''}</td>
                    <td>${p.date_of_birth || ''}</td>
                    <td>${p.sex || ''}</td>
                    <td>${p.city || ''}, ${p.state || ''}</td>
                    <td>${p.phone || ''}</td>
                    <td>${p.email || ''}</td>
                </tr>
            `).join('') || '<tr><td colspan="8"><em>No patients found</em></td></tr>';

            return `
                <div class="table-card">
                    <table>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>MRN</th>
                                <th>Name</th>
                                <th>DOB</th>
                                <th>Sex</th>
                                <th>Location</th>
                                <th>Phone</th>
                                <th>Email</th>
                            </tr>
                        </thead>
                        <tbody>${rows}</tbody>
                    </table>
                </div>
                ${jsonToolbar('Patients JSON', data)}
            `;
        }

        function formatBytes(bytes) {
            if (!bytes) return '0 B';
            const units = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(1024));
            return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
        }

        function jsonToolbar(label, data) {
            const encoded = encodeURIComponent(JSON.stringify(data, null, 2));
            return `
                <div class="result-toolbar">
                    <button class="toolbar-button" onclick="showJsonModal('${label}', decodeURIComponent('${encoded}'))">View JSON</button>
                    <button class="toolbar-button" onclick="copyJson('${encoded}')">Copy JSON</button>
                </div>
            `;
        }

        function showJsonModal(title, jsonText) {
            const modal = document.getElementById('json-modal');
            document.getElementById('json-modal-title').textContent = title;
            document.getElementById('json-modal-content').textContent = jsonText;
            modal.style.display = 'flex';
        }

        function closeJsonModal() {
            document.getElementById('json-modal').style.display = 'none';
        }

        function copyJson(encoded) {
            const text = decodeURIComponent(encoded);
            navigator.clipboard.writeText(text).then(() => {
                alert('JSON copied to clipboard');
            });
        }

        async function viewResource(resourceId) {
            try {
                const response = await fetch(`/api/resources/${resourceId}?include_content=true`);
                const data = await response.json();
                if (!data.success) {
                    alert(data.message || 'Resource not found');
                    return;
                }
                if (!data.has_local_content) {
                    const message = data.homepage
                        ? `This resource is hosted externally. Open: ${data.homepage}`
                        : 'No inline content available for this resource.';
                    showJsonModal(data.name, message);
                    return;
                }
                const content = typeof data.content === 'object'
                    ? JSON.stringify(data.content, null, 2)
                    : (data.content || '');
                showJsonModal(`${data.name} (${data.media_type})`, content);
            } catch (error) {
                alert('Failed to load resource: ' + error.message);
            }
        }

        async function downloadResource(resourceId) {
            try {
                const response = await fetch(`/api/resources/${resourceId}?include_content=true`);
                const data = await response.json();
                if (!data.success) {
                    alert(data.message || 'Resource not found');
                    return;
                }
                if (!data.has_local_content) {
                    if (data.homepage) {
                        window.open(data.homepage, '_blank');
                        return;
                    }
                    alert('No downloadable content for this resource.');
                    return;
                }
                const content = typeof data.content === 'object'
                    ? JSON.stringify(data.content, null, 2)
                    : (data.content || '');
                const blob = new Blob([content], { type: data.media_type || 'text/plain' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = data.relative_path || `${resourceId}.txt`;
                document.body.appendChild(a);
                a.click();
                a.remove();
                URL.revokeObjectURL(url);
            } catch (error) {
                alert('Failed to download resource: ' + error.message);
            }
        }

        function openResourceLink(url) {
            window.open(url, '_blank');
        }
        
        // Load tools and check LLM status on page load
        window.onload = () => {
            loadTools();
            checkLLMStatus();
            loadModelOptions();
        };
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)


@app.get("/api/tools")
async def list_tools():
    """List all available MCP tools."""
    if not mcp_server:
        raise HTTPException(status_code=500, detail="MCP server not initialized")
    
    tools = []
    try:
        # Use FastMCP's tool manager to list tools
        if hasattr(mcp_server, '_tool_manager'):
            tool_list = mcp_server._tool_manager.list_tools()
            for tool in tool_list:
                description = tool.description or "No description available"
                tools.append({
                    "name": tool.name,
                    "description": description,
                    "full_description": description
                })
        else:
            # Fallback: check _tools in tool_manager
            if hasattr(mcp_server, '_tool_manager') and hasattr(mcp_server._tool_manager, '_tools'):
                for tool_name, tool_info in mcp_server._tool_manager._tools.items():
                    description = getattr(tool_info, 'description', '') or tool_name
                    tools.append({
                        "name": tool_name,
                        "description": description.split('\n')[0].strip() if description else "No description",
                        "full_description": description
                    })
    except Exception as e:
        logger.error(f"Error listing tools: {e}")
        # Fallback to hardcoded list if we can't introspect
        tools = [
            {"name": "list_dicom_nodes", "description": "List all configured DICOM nodes"},
            {"name": "query_patients", "description": "Search for patients by criteria"},
            {"name": "query_studies", "description": "Find studies by criteria"},
            {"name": "get_system_prompt", "description": "Get the recommended system prompt"},
        ]
    
    return JSONResponse(content=tools)


@app.get("/api/llm-status")
async def get_llm_status():
    """Get LLM integration status."""
    api_key = os.getenv("OPENAI_API_KEY")
    return JSONResponse(content={
        "available": LLM_AVAILABLE and api_key is not None,
        "llm_available": LLM_AVAILABLE,
        "api_key_set": api_key is not None,
        "model": get_openai_model() if api_key else None
    })


@app.get("/api/llm-model")
async def get_llm_model():
    """Get current model selection + options."""
    return JSONResponse(content={
        "current": get_openai_model(),
        "options": OPENAI_MODEL_OPTIONS,
    })


@app.post("/api/llm-model")
async def set_llm_model(request: ModelUpdateRequest):
    """Set model override for this Web UI process."""
    global OPENAI_MODEL_OVERRIDE
    model = (request.model or "").strip()
    if not model:
        raise HTTPException(status_code=400, detail="Model must be a non-empty string")
    OPENAI_MODEL_OVERRIDE = model
    return JSONResponse(content={"success": True, "current": get_openai_model()})


@app.get("/api/prompt")
async def get_prompt():
    """Get the current system prompt."""
    prompt_path = Path(__file__).parent.parent.parent / "system_prompt.txt"
    if prompt_path.exists():
        with open(prompt_path, 'r') as f:
            prompt = f.read()
        return JSONResponse(content={"prompt": prompt})
    return JSONResponse(content={"prompt": ""})


@app.post("/api/prompt")
async def update_prompt(request: PromptUpdateRequest):
    """Update the system prompt."""
    prompt_path = Path(__file__).parent.parent.parent / "system_prompt.txt"
    with open(prompt_path, 'w') as f:
        f.write(request.prompt)
    return JSONResponse(content={"success": True})


@app.get("/api/resources")
async def list_resources_api():
    """List saved resources bundled with the server."""
    if not mcp_lifespan_context or not getattr(mcp_lifespan_context, "resources", None):
        return JSONResponse(content={"count": 0, "resources": []})
    resources = [
        res.to_dict(include_content=False)
        for res in mcp_lifespan_context.resources.values()
    ]
    return JSONResponse(content=to_json_safe({
        "count": len(resources),
        "resources": resources,
    }))


@app.get("/api/resources/{resource_id}")
async def get_resource_api(resource_id: str, include_content: bool = True):
    """Fetch a single resource (optionally with content)."""
    if not mcp_lifespan_context or not getattr(mcp_lifespan_context, "resources", None):
        raise HTTPException(status_code=404, detail="Resource catalog not available")
    resource = mcp_lifespan_context.resources.get(resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    return JSONResponse(content=to_json_safe(resource.to_dict(include_content=include_content)))


async def get_system_prompt_text() -> str:
    """Load the system prompt from file."""
    prompt_path = Path(__file__).parent.parent.parent / "system_prompt.txt"
    if prompt_path.exists():
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return """You are a medical imaging assistant specialized in DICOM and FHIR workflows. Help users query, analyze, and manage medical imaging data efficiently."""


async def get_available_tools_for_llm() -> List[Dict[str, Any]]:
    """Get available tools formatted for LLM function calling."""
    if not mcp_server or not hasattr(mcp_server, '_tool_manager'):
        return []
    
    tools_response = await list_tools()
    tools_data = json.loads(tools_response.body)
    
    # Format tools for OpenAI function calling
    formatted_tools = []
    for tool in tools_data:
        tool_info = mcp_server._tool_manager.get_tool(tool["name"])
        if not tool_info:
            continue

        parameters = {}
        if hasattr(tool_info, "parameters") and tool_info.parameters:
            parameters = copy.deepcopy(tool_info.parameters)

        formatted_tool = {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"] or tool.get("full_description", ""),
                "parameters": parameters,
            },
        }

        if tool["name"] == "create_synthetic_cr_study":
            props = parameters.setdefault("properties", {})
            required = parameters.setdefault("required", ["accession_number"])
            if "accession_number" not in required:
                required.append("accession_number")

            image_mode_prop = props.setdefault("image_mode", {})
            image_mode_prop.update({
                "type": "string",
                "description": "Image generation mode (default 'auto')",
                "enum": ["auto", "ai", "simple", "sample"],
                "default": image_mode_prop.get("default", "auto"),
            })

            image_desc_prop = props.setdefault("image_description", {})
            image_desc_prop.setdefault("type", "string")
            image_desc_prop["description"] = "Optional description for AI prompt (default 'normal')"
            image_desc_prop.setdefault("default", "normal")

            send_prop = props.setdefault("send_to_pacs", {})
            send_prop.setdefault("type", "boolean")
            send_prop["description"] = "Send generated images to PACS (default true)"
            send_prop.setdefault("default", True)

            formatted_tool["function"]["description"] = (
                (formatted_tool["function"]["description"] or "").rstrip(".")
                + " Defaults: image_mode='auto', image_description='normal', send_to_pacs=true."
            )

        formatted_tools.append(formatted_tool)
    
    return formatted_tools


@app.post("/api/chat")
async def chat(request: Dict[str, Any]):
    """Handle chat messages with LLM integration for medical imaging."""
    use_llm = request.get("use_llm", True)  # Can be disabled for fallback
    message = request.get("message", "").strip()
    
    if not message:
        return JSONResponse(content={
            "response": "Please enter a message.",
            "tool_calls": []
        })
    
    response_text = ""
    tool_calls = []
    
    # Try LLM integration if available and enabled
    if use_llm and LLM_AVAILABLE:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            # Fall through to pattern matching
            logger.warning("OPENAI_API_KEY not set, using pattern matching fallback")
            use_llm = False
        else:
            try:
                client = OpenAI(api_key=api_key)
                
                # Load system prompt
                system_prompt = await get_system_prompt_text()
                
                # Get available tools
                tools = await get_available_tools_for_llm()
                
                # Build messages for LLM
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ]
                
                # Call LLM with function calling
                response = client.chat.completions.create(
                    model=get_openai_model(),
                    messages=messages,
                    tools=tools if tools else None,
                    tool_choice="auto"
                )
                
                # Process LLM response
                assistant_message = response.choices[0].message
                
                # Check if LLM wants to call tools
                if assistant_message.tool_calls:
                    # Execute tool calls
                    tool_results = []
                    for tool_call in assistant_message.tool_calls:
                        tool_name = tool_call.function.name
                        try:
                            # Parse tool arguments
                            tool_args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
                            
                            # Execute tool
                            result = await call_tool(tool_name, tool_args)
                            safe_result = to_json_safe(result)
                            tool_results.append({
                                "tool_call_id": tool_call.id,
                                "role": "tool",
                                "name": tool_name,
                                "content": json.dumps(safe_result) if not isinstance(safe_result, str) else safe_result
                            })
                            tool_calls.append({
                                "tool": tool_name,
                                "arguments": tool_args,
                                "result": safe_result
                            })
                        except Exception as e:
                            logger.error(f"Error executing tool {tool_name}: {e}")
                            tool_results.append({
                                "tool_call_id": tool_call.id,
                                "role": "tool",
                                "name": tool_name,
                                "content": f"Error: {str(e)}"
                            })
                    
                    # Get final response from LLM with tool results
                    messages.append(assistant_message)
                    messages.extend(tool_results)
                    
                    final_response = client.chat.completions.create(
                        model=get_openai_model(),
                        messages=messages
                    )
                    response_text = final_response.choices[0].message.content
                else:
                    # LLM provided direct response
                    response_text = assistant_message.content or "I understand. How can I help you with medical imaging data?"
                    
            except Exception as e:
                logger.error(f"LLM error: {e}")
                # Fall through to pattern matching
                use_llm = False
    
    # Fallback to pattern matching if LLM not available or failed
    if not use_llm or not response_text:
        message_lower = message.lower()
        
        # Pattern matching for common tool calls
        if any(word in message_lower for word in ["list", "show", "get"]) and any(word in message_lower for word in ["node", "nodes", "server", "servers"]):
            try:
                result = await call_tool("list_dicom_nodes", {})
                tool_calls.append({
                    "tool": "list_dicom_nodes",
                    "arguments": {},
                    "result": result
                })
                nodes = result.get("nodes", [])
                current = result.get("current_node", "unknown")
                response_text = f"**Current DICOM Node:** {current}\n**Available Nodes:** {', '.join(nodes)}"
            except Exception as e:
                response_text = f"Error listing nodes: {str(e)}"
        
        elif any(word in message_lower for word in ["list", "show", "get"]) and "patient" in message_lower:
            try:
                result = await call_tool("list_mini_ris_patients", {})
                tool_calls.append({
                    "tool": "list_mini_ris_patients",
                    "arguments": {},
                    "result": result
                })
                # UI renders a dedicated patient table widget, so no extra copy needed
                response_text = ""
            except Exception as e:
                response_text = f"Error listing patients: {str(e)}"
        
        elif any(word in message_lower for word in ["verify", "test", "check"]) and "connection" in message_lower:
            try:
                result = await call_tool("verify_connection", {})
                tool_calls.append({
                    "tool": "verify_connection",
                    "arguments": {},
                    "result": {"message": result}
                })
                response_text = str(result)
            except Exception as e:
                response_text = f"Error verifying connection: {str(e)}"
        
        else:
            response_text = f"I received: {message}\n\n**Try asking:**\n- \"List all nodes\"\n- \"List patients\"\n- \"Verify connection\"\n\n*Tip: Set OPENAI_API_KEY environment variable to enable LLM-powered chat.*"
    
    # Suppress redundant assistant text if widgets handle the data
    if should_suppress_response(tool_calls):
        response_text = ""
    elif not response_text:
        response_text = "No response."
    
    return JSONResponse(content={
        "response": response_text,
        "tool_calls": to_json_safe(tool_calls)
    })


async def call_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Call an MCP tool."""
    if not mcp_server or not mcp_lifespan_context:
        raise HTTPException(status_code=500, detail="MCP server not initialized")
    
    try:
        # Use tool_manager to get and call the tool
        if not hasattr(mcp_server, '_tool_manager'):
            raise HTTPException(status_code=500, detail="MCP server doesn't have tool_manager")
        
        tool_manager = mcp_server._tool_manager
        
        # Get the tool
        if not hasattr(tool_manager, 'get_tool'):
            raise HTTPException(status_code=500, detail="Tool manager doesn't have get_tool method")
        
        tool_info = tool_manager.get_tool(tool_name)
        if not tool_info:
            # List available tools for error message
            try:
                available = [t.name for t in tool_manager.list_tools()]
            except:
                available = []
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found. Available tools: {available}")
        
        # Call the tool function directly with the proper context
        # The tool's fn is the actual function, which we can call with context
        tool_func = tool_info.fn
        
        # Create a mock Context-like object for the tool
        # Tools access ctx.request_context.lifespan_context
        class RequestContext:
            def __init__(self):
                self.lifespan_context = mcp_lifespan_context
        
        # Check if tool accepts context parameter
        import inspect
        sig = inspect.signature(tool_func)
        params = list(sig.parameters.keys())
        
        # Prepare arguments
        call_kwargs = arguments.copy()
        if "ctx" in params:
            # Create a minimal context-like object
            from mcp.server.fastmcp import Context
            # Try using get_context if available, otherwise create a simple wrapper
            if hasattr(mcp_server, 'get_context'):
                try:
                    tool_ctx = mcp_server.get_context()
                    # Try to set the lifespan_context
                    if hasattr(tool_ctx, 'request_context'):
                        # If request_context is a property, we need a different approach
                        # Let's create a simple object that mimics the structure
                        class SimpleContext:
                            def __init__(self):
                                self.request_context = RequestContext()
                        tool_ctx = SimpleContext()
                    else:
                        tool_ctx.request_context = RequestContext()
                except:
                    class SimpleContext:
                        def __init__(self):
                            self.request_context = RequestContext()
                    tool_ctx = SimpleContext()
            else:
                class SimpleContext:
                    def __init__(self):
                        self.request_context = RequestContext()
                tool_ctx = SimpleContext()
            
            call_kwargs["ctx"] = tool_ctx
        
        # Call the tool function directly
        result = tool_func(**call_kwargs)
        
        # Handle async results
        if asyncio.iscoroutine(result):
            result = await result
        
        return to_json_safe(result)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Tool execution error for {tool_name}: {error_details}")
        raise HTTPException(status_code=500, detail=f"Tool execution error: {str(e)}")


@app.post("/api/tools/call")
async def call_tool_endpoint(request: ToolCallRequest):
    """Call a specific MCP tool."""
    try:
        result = await call_tool(request.tool_name, request.arguments)
        return JSONResponse(content=to_json_safe(result))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080)

