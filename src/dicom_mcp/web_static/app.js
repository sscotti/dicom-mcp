/* MCP-FHIR-Orthanc Web UI (frontend) */

let currentPanel = 'chat';
let currentJsonModalPayload = null;
let currentJsonModalTitle = 'JSON';

function $(id) {
  return document.getElementById(id);
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function formatMultilineText(str) {
  return escapeHtml(str).replace(/\n/g, '<br>');
}

function showPanel(panel, btnEl) {
  document.querySelectorAll('.sidebar-button').forEach(btn => btn.classList.remove('active'));
  if (btnEl) btnEl.classList.add('active');

  document.querySelectorAll('.panel-content').forEach(p => p.classList.remove('active'));

  currentPanel = panel;

  if (panel === 'chat') {
    $('chat-panel').classList.add('active');
  } else {
    $(panel + '-panel').classList.add('active');
    if (panel === 'tools') loadTools();
    if (panel === 'prompts') loadPrompt();
    if (panel === 'resources') loadResources();
  }
}

async function loadTools() {
  try {
    const response = await fetch('/api/tools');
    const tools = await response.json();
    const toolsList = $('tools-list');
    toolsList.innerHTML = '';

    tools.forEach(tool => {
      const toolDiv = document.createElement('div');
      toolDiv.className = 'tool-item';
      toolDiv.innerHTML = `
        <div class="tool-name">${escapeHtml(tool.name)}</div>
        <div class="tool-description">${formatMultilineText(tool.description || 'No description')}</div>
      `;
      toolDiv.onclick = () => {
        addMessage('assistant', `Tool: <strong>${escapeHtml(tool.name)}</strong><br>${formatMultilineText(tool.full_description || tool.description || '')}`);
        showPanel('chat', document.querySelector('.sidebar-button'));
      };
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
    $('prompt-editor').value = data.prompt || '';
  } catch (error) {
    console.error('Error loading prompt:', error);
  }
}

async function savePrompt() {
  const prompt = $('prompt-editor').value;
  try {
    const response = await fetch('/api/prompt', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt })
    });
    if (response.ok) alert('Prompt saved successfully!');
  } catch (error) {
    console.error('Error saving prompt:', error);
    alert('Error saving prompt');
  }
}

async function loadResources() {
  $('resources-list').innerHTML = '<p class="cell-muted">Resources UI coming soon (next: show config + key resources).</p>';
}

function handleKeyPress(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
}

async function sendMessage() {
  const input = $('chat-input');
  const message = input.value.trim();
  if (!message) return;

  input.value = '';
  addMessage('user', escapeHtml(message));

  const loadingId = addMessage('assistant', '<span class="loading"></span> Processing...');

  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message })
    });

    const data = await response.json();

    const loadingMsg = document.getElementById(loadingId);
    if (loadingMsg) loadingMsg.remove();

    if (data.tool_calls && data.tool_calls.length > 0) {
      data.tool_calls.forEach(tc => addToolCall(tc.tool, tc.arguments, tc.result));
    }

    // Render assistant response
    addMessage('assistant', formatMultilineText(data.response || ''));
  } catch (error) {
    const loadingMsg = document.getElementById(loadingId);
    if (loadingMsg) loadingMsg.remove();
    addMessage('assistant', `Error: ${escapeHtml(error.message)}`);
  }
}

function addMessage(role, contentHtml) {
  const messagesDiv = $('chat-messages');
  const messageId = 'msg-' + Date.now() + '-' + Math.floor(Math.random() * 1000);
  const messageDiv = document.createElement('div');
  messageDiv.id = messageId;
  messageDiv.className = `message ${role}`;
  messageDiv.innerHTML = contentHtml;
  messagesDiv.appendChild(messageDiv);
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
  return messageId;
}

/* -------------------------
 * Widget system (extensible)
 * ------------------------- */

function renderWidgetForResult(result) {
  if (!result) return '';

  // common shapes
  if (result.patients && Array.isArray(result.patients)) {
    return renderTableWidget(result.patients);
  }
  if (result.nodes && Array.isArray(result.nodes)) {
    return renderListWidget(result.nodes);
  }

  // generic: if array of objects => table
  if (Array.isArray(result)) {
    if (result.length > 0 && typeof result[0] === 'object' && !Array.isArray(result[0])) {
      return renderTableWidget(result);
    }
    return renderListWidget(result);
  }

  // object => key/value grid (small)
  if (typeof result === 'object') {
    return renderKeyValueWidget(result);
  }

  return `<div class="widget">${formatMultilineText(String(result))}</div>`;
}

function guessColumns(rows) {
  const first = rows[0] || {};
  const keys = Object.keys(first);
  // Put common identifiers first
  const preferred = ['patient_id','mrn','given_name','family_name','date_of_birth','sex','study_instance_uid','accession_number','study_date'];
  const ordered = [];
  preferred.forEach(k => { if (keys.includes(k)) ordered.push(k); });
  keys.forEach(k => { if (!ordered.includes(k)) ordered.push(k); });
  // keep it manageable
  return ordered.slice(0, 12);
}

function renderTableWidget(rows) {
  if (!rows || rows.length === 0) return `<div class="widget cell-muted">No rows.</div>`;
  const cols = guessColumns(rows);
  const thead = cols.map(c => `<th>${escapeHtml(c)}</th>`).join('');
  const tbody = rows.map(r => {
    const tds = cols.map(c => `<td>${renderCell(r[c])}</td>`).join('');
    return `<tr>${tds}</tr>`;
  }).join('');

  return `
    <div class="widget">
      <div class="table-wrap">
        <table class="data-table">
          <thead><tr>${thead}</tr></thead>
          <tbody>${tbody}</tbody>
        </table>
      </div>
    </div>
  `;
}

function renderListWidget(items) {
  const safe = (items || []).map(i => `<li>${renderCell(i)}</li>`).join('');
  return `<div class="widget"><ul style="padding-left: 1.25rem; line-height: 1.6;">${safe}</ul></div>`;
}

function renderKeyValueWidget(obj) {
  const keys = Object.keys(obj || {}).slice(0, 16);
  const rows = keys.map(k => {
    return `<tr><td class="cell-muted" style="white-space:nowrap; padding-right:1rem;">${escapeHtml(k)}</td><td>${renderCell(obj[k])}</td></tr>`;
  }).join('');
  return `
    <div class="widget">
      <div class="table-wrap">
        <table class="data-table">
          <thead><tr><th>Key</th><th>Value</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    </div>
  `;
}

function renderCell(value) {
  if (value === null || value === undefined) return `<span class="cell-muted">—</span>`;
  if (typeof value === 'string') return escapeHtml(value);
  if (typeof value === 'number' || typeof value === 'boolean') return escapeHtml(String(value));
  if (Array.isArray(value)) return escapeHtml(JSON.stringify(value));
  if (typeof value === 'object') return escapeHtml(JSON.stringify(value));
  return escapeHtml(String(value));
}

/* -------------------------
 * JSON Modal
 * ------------------------- */

function openJsonModal(title, payload) {
  currentJsonModalTitle = title || 'JSON';
  currentJsonModalPayload = payload;
  $('json-modal-title').textContent = currentJsonModalTitle;
  $('json-modal-body').textContent = JSON.stringify(payload, null, 2);
  $('json-modal').classList.remove('hidden');
}

function closeJsonModal() {
  $('json-modal').classList.add('hidden');
  currentJsonModalPayload = null;
}

async function copyJsonModal() {
  try {
    await navigator.clipboard.writeText($('json-modal-body').textContent || '');
    alert('Copied JSON to clipboard');
  } catch {
    alert('Copy failed');
  }
}

/* -------------------------
 * Tool-call card rendering
 * ------------------------- */

function addToolCall(toolName, arguments_, result) {
  const messagesDiv = $('chat-messages');
  const wrapper = document.createElement('div');
  wrapper.className = 'message-tool';

  const header = document.createElement('div');
  header.className = 'tool-header';
  header.innerHTML = `
    <div class="tool-title">Tool: ${escapeHtml(toolName)}</div>
    <div class="tool-actions">
      <button class="btn" type="button">View JSON</button>
      <button class="btn primary" type="button">Copy JSON</button>
    </div>
  `;

  const [viewBtn, copyBtn] = header.querySelectorAll('button');
  viewBtn.onclick = () => openJsonModal(toolName, { arguments: arguments_ || {}, result });
  copyBtn.onclick = async () => {
    try {
      await navigator.clipboard.writeText(JSON.stringify({ arguments: arguments_ || {}, result }, null, 2));
      alert('Copied tool result JSON');
    } catch {
      alert('Copy failed');
    }
  };

  const widgetHtml = renderWidgetForResult(result);

  const details = document.createElement('div');
  details.innerHTML = `
    <div class="cell-muted" style="margin-bottom:0.5rem;"><strong>Arguments</strong>: ${escapeHtml(JSON.stringify(arguments_ || {}))}</div>
    ${widgetHtml}
  `;

  wrapper.appendChild(header);
  wrapper.appendChild(details);

  messagesDiv.appendChild(wrapper);
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

/* -------------------------
 * LLM status + model selection
 * ------------------------- */

async function checkLLMStatus() {
  try {
    const response = await fetch('/api/llm-status');
    const status = await response.json();
    const indicator = $('llm-indicator');
    const text = $('llm-text');
    const pill = $('llm-pill');
    const select = $('llm-model-select');

    if (status.available) {
      indicator.textContent = '🤖';
      text.textContent = `LLM: ${status.model || 'Ready'}`;
      pill.classList.remove('warn');
      pill.classList.add('ok');
      if (select) select.disabled = false;
    } else {
      indicator.textContent = '⚠️';
      if (!status.llm_available) text.textContent = 'LLM: Not installed';
      else if (!status.api_key_set) text.textContent = 'LLM: No API key (set OPENAI_API_KEY)';
      else text.textContent = 'LLM: Not available';
      pill.classList.remove('ok');
      pill.classList.add('warn');
      if (select) select.disabled = true;
    }
  } catch (error) {
    console.error('Error checking LLM status:', error);
    $('llm-text').textContent = 'LLM: Unknown';
  }
}

async function loadModelOptions() {
  try {
    const response = await fetch('/api/llm-model');
    const data = await response.json();
    const select = $('llm-model-select');
    if (!select) return;

    select.innerHTML = '';
    (data.options || []).forEach(m => {
      const opt = document.createElement('option');
      opt.value = m;
      opt.textContent = m;
      select.appendChild(opt);
    });
    const customOpt = document.createElement('option');
    customOpt.value = '__custom__';
    customOpt.textContent = 'Custom…';
    select.appendChild(customOpt);

    // apply saved model
    const saved = localStorage.getItem('openai_model');
    if (saved && saved !== data.current) {
      await setModel(saved);
      return;
    }

    // select current
    if (data.current) {
      const exists = (data.options || []).includes(data.current);
      select.value = exists ? data.current : '__custom__';
    }

    select.onchange = async () => {
      if (select.value === '__custom__') {
        const custom = prompt('Enter OpenAI model name:', data.current || '');
        if (custom && custom.trim()) {
          await setModel(custom.trim());
          localStorage.setItem('openai_model', custom.trim());
        } else {
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

/* init */
window.showPanel = showPanel;
window.sendMessage = sendMessage;
window.handleKeyPress = handleKeyPress;
window.savePrompt = savePrompt;
window.closeJsonModal = closeJsonModal;
window.copyJsonModal = copyJsonModal;

window.onload = () => {
  loadTools();
  checkLLMStatus();
  loadModelOptions();
};


