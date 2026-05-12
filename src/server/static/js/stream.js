let currentEventSource = null;
let toolCallCount = 0;
let currentAgent = '';
const pendingToolCards = {};
const agentLabels = {
  load_context: 'Context Loader',
  news_analyst: 'News Analyst',
  technical_analyst: 'Technical Analyst',
  portfolio_risk: 'Portfolio Risk',
  synthesize: 'Orchestrator'
};

function showTab(name, el) {
  document.querySelectorAll('.section-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.sidebar .nav-link').forEach(l => l.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  if (el) el.classList.add('active');
  document.getElementById('page-title').textContent = {
    today: 'Live Run', history: 'History',
    portfolio: 'Portfolio', accuracy: 'Accuracy', usage: 'API Usage'
  }[name] || name;

  // Lazy-load data tabs
  if (name === 'history') loadHistory();
  if (name === 'portfolio') loadPortfolio();
  if (name === 'accuracy') loadAccuracy();
  if (name === 'usage') loadUsage();
}

function setAgentState(agentName, state) {
  const box = document.getElementById('box-' + agentName);
  if (!box) return;
  box.classList.remove('running', 'done', 'error');
  if (state) box.classList.add(state);
}

function addToolCall(toolName, input) {
  const noMsg = document.getElementById('no-tools-msg');
  if (noMsg) noMsg.remove();

  toolCallCount++;
  const id = 'tool-' + toolCallCount;
  if (!pendingToolCards[toolName]) pendingToolCards[toolName] = [];
  pendingToolCards[toolName].push(id);
  const div = document.createElement('div');
  div.className = 'tool-card pending';
  div.id = id;
  div.dataset.agent = currentAgent || '';
  div.dataset.tool = toolName;
  div.dataset.pending = 'true';
  div.innerHTML = `
    <div class="tool-card-header" onclick="toggleTool('${id}')">
      <i class="bi bi-wrench text-warning"></i>
      <span class="fw-semibold text-warning">${toolName}</span>
      <span class="tool-meta">${escapeHtml(currentAgent || 'agent')}</span>
      <span class="text-muted ms-auto"><i class="bi bi-chevron-down"></i></span>
    </div>
    <div class="tool-card-body" id="${id}-body">
      <div class="tool-input mb-2"><span class="text-muted">Input: </span>${escapeHtml(input)}</div>
      <div class="tool-output pending" id="${id}-output">Waiting for response...</div>
    </div>`;
  document.getElementById('tool-calls-container').appendChild(div);
  return id;
}

function updateToolOutput(toolName, output) {
  const queue = pendingToolCards[toolName] || [];
  const cardId = queue.shift();
  if (!cardId) return;
  const card = document.getElementById(cardId);
  if (!card) return;
  const outEl = card.querySelector('[id$="-output"]');
  if (outEl) {
    outEl.textContent = output;
    outEl.className = 'tool-output';
  }
  card.classList.remove('pending', 'resolved-fallback');
  card.dataset.pending = 'false';
}

function toggleTool(id) {
  const body = document.getElementById(id + '-body');
  if (body) body.style.display = body.style.display === 'none' ? '' : 'none';
}

function clearTools() {
  const container = document.getElementById('tool-calls-container');
  container.innerHTML = '<div class="text-muted small" id="no-tools-msg">No tool calls yet.</div>';
  toolCallCount = 0;
  Object.keys(pendingToolCards).forEach(k => delete pendingToolCards[k]);
}

function labelForAgent(agentName) {
  return agentLabels[agentName] || agentName || 'Agent';
}

function setThinkingStatus(text) {
  const el = document.getElementById('thinking-status');
  if (el) el.textContent = text;
}

function ensureThinkingSection(agentName) {
  const container = document.getElementById('llm-stream');
  let section = document.getElementById(`thinking-${agentName}`);
  if (section) return section;

  if (container.dataset.empty !== 'false') {
    container.textContent = '';
    container.dataset.empty = 'false';
  }

  section = document.createElement('div');
  section.className = 'thinking-section running';
  section.id = `thinking-${agentName}`;
  section.innerHTML = `
    <div class="thinking-section-header">
      <span>${labelForAgent(agentName)}</span>
      <span class="subtle-text small">Streaming</span>
    </div>
    <div class="thinking-section-body" id="thinking-body-${agentName}"></div>
  `;
  container.appendChild(section);
  return section;
}

function appendLLMToken(token) {
  const container = document.getElementById('llm-stream');
  if (!currentAgent) {
    if (container.textContent === 'Waiting for run...') container.textContent = '';
    container.textContent += token;
    container.scrollTop = container.scrollHeight;
    return;
  }
  const section = ensureThinkingSection(currentAgent);
  const body = section.querySelector('.thinking-section-body');
  body.textContent += token;
  container.scrollTop = container.scrollHeight;
}

function resetThinking() {
  const el = document.getElementById('llm-stream');
  el.textContent = 'Waiting for run...';
  el.dataset.empty = 'true';
  setThinkingStatus('Idle');
}

function markThinkingSectionDone(agentName) {
  const section = document.getElementById(`thinking-${agentName}`);
  if (!section) return;
  section.classList.remove('running');
  section.classList.add('done');
  const status = section.querySelector('.thinking-section-header .small');
  if (status) status.textContent = 'Completed';
}

function addAgentSummary(agentName, summary) {
  if (!summary) return;
  const section = ensureThinkingSection(agentName);
  let summaryEl = section.querySelector('.thinking-summary');
  if (!summaryEl) {
    summaryEl = document.createElement('div');
    summaryEl.className = 'thinking-summary';
    section.appendChild(summaryEl);
  }
  summaryEl.textContent = `Summary:\n${summary}`;
}

function resolvePendingToolsForAgent(agentName) {
  const cards = document.querySelectorAll(`.tool-card[data-agent="${agentName}"][data-pending="true"]`);
  cards.forEach(card => {
    const outEl = card.querySelector('[id$="-output"]');
    if (outEl && outEl.textContent.trim() === 'Waiting for response...') {
      outEl.textContent = 'Completed inside the agent run. Detailed tool output was not emitted by the stream, but the agent did finish before the graph moved on.';
      outEl.className = 'tool-output fallback';
    }
    card.classList.remove('pending');
    card.classList.add('resolved-fallback');
    card.dataset.pending = 'false';
  });
}

function showFinalReport(report) {
  const el = document.getElementById('final-report');
  el.textContent = report;
}

function setLiveBadge(live) {
  const badge = document.getElementById('live-badge');
  badge.textContent = live ? '● LIVE' : 'IDLE';
  badge.className = live ? 'live-badge' : 'idle-badge';
}

async function triggerRun(runType) {
  // Switch to live tab
  showTab('today', document.querySelector('.sidebar .nav-link'));

  // Reset UI
  clearTools();
  resetThinking();
  document.getElementById('llm-stream').textContent = `Starting ${runType} analysis...`;
  document.getElementById('llm-stream').dataset.empty = 'true';
  document.getElementById('final-report').textContent = 'Run in progress. Final synthesis will appear here when complete.';
  ['load_context','news_analyst','technical_analyst','portfolio_risk','synthesize'].forEach(a => setAgentState(a, null));
  currentAgent = '';
  setThinkingStatus(`Preparing ${runType} run`);
  setLiveBadge(true);

  // Close any existing SSE
  if (currentEventSource) { currentEventSource.close(); currentEventSource = null; }

  try {
    const resp = await fetch(`/run/${runType}`, { method: 'POST' });
    const data = await resp.json();
    if (!data.run_id) throw new Error(data.error || 'Failed to start run');

    const runId = data.run_id;
    const es = new EventSource(`/stream/${runId}`);
    currentEventSource = es;

    es.addEventListener('agent_start', e => {
      const d = JSON.parse(e.data);
      currentAgent = d.agent;
      setAgentState(d.agent, 'running');
      ensureThinkingSection(d.agent);
      setThinkingStatus(`${labelForAgent(d.agent)} is running`);
    });

    es.addEventListener('agent_end', e => {
      const d = JSON.parse(e.data);
      setAgentState(d.agent, 'done');
      markThinkingSectionDone(d.agent);
      addAgentSummary(d.agent, d.summary || '');
      resolvePendingToolsForAgent(d.agent);
      if (currentAgent === d.agent) currentAgent = '';
      setThinkingStatus(`${labelForAgent(d.agent)} finished`);
    });

    es.addEventListener('tool_start', e => {
      const d = JSON.parse(e.data);
      addToolCall(d.tool, d.input);
    });

    es.addEventListener('tool_end', e => {
      const d = JSON.parse(e.data);
      updateToolOutput(d.tool, d.output);
    });

    es.addEventListener('llm_stream', e => {
      const d = JSON.parse(e.data);
      appendLLMToken(d.token);
    });

    es.addEventListener('run_complete', e => {
      const d = JSON.parse(e.data);
      setLiveBadge(false);
      es.close();
      setThinkingStatus(d.status === 'completed' ? 'Run completed' : 'Run failed');
      if (d.status === 'completed' && d.report) {
        showFinalReport(d.report);
      } else if (d.status === 'error') {
        const el = document.getElementById('llm-stream');
        el.textContent += `\n\nError: ${d.error}`;
        ['news_analyst','technical_analyst','portfolio_risk','synthesize'].forEach(a => {
          const box = document.getElementById('box-' + a);
          if (box && box.classList.contains('running')) setAgentState(a, 'error');
        });
      }
    });

    es.onerror = () => {
      setLiveBadge(false);
      es.close();
    };

  } catch (err) {
    setLiveBadge(false);
    setThinkingStatus('Run failed');
    document.getElementById('llm-stream').textContent = 'Error: ' + err.message;
  }
}

function escapeHtml(text) {
  return String(text).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// History
async function loadHistory() {
  try {
    const resp = await fetch('/runs');
    const runs = await resp.json();
    const el = document.getElementById('history-list');
    if (!runs.length) { el.innerHTML = '<span class="text-muted small">No runs yet.</span>'; return; }
    el.innerHTML = runs.map(r => `
      <div class="run-history-item">
        <div class="d-flex justify-content-between align-items-center">
          <span class="fw-semibold text-capitalize">${r.type} run <span class="badge badge-run-type bg-secondary">${r.id}</span></span>
          <span class="badge ${r.status==='completed'?'bg-success':r.status==='error'?'bg-danger':'bg-warning'}">${r.status}</span>
        </div>
        <small class="text-muted">${r.started_at?.slice(0,19).replace('T',' ')} UTC</small>
      </div>`).join('');
  } catch(e) { document.getElementById('history-list').innerHTML = '<span class="text-danger small">Failed to load.</span>'; }
}

// Portfolio
async function loadPortfolio() {
  try {
    const resp = await fetch('/api/portfolio');
    const data = await resp.json();
    document.getElementById('portfolio-content').innerHTML = `
      <div class="mb-3"><h6 class="text-muted">P&L</h6><pre class="small">${escapeHtml(data.pnl)}</pre></div>
      <div class="mb-3"><h6 class="text-muted">Holdings</h6><pre class="small">${escapeHtml(data.holdings)}</pre></div>
      <div><h6 class="text-muted">Open Positions</h6><pre class="small">${escapeHtml(data.positions)}</pre></div>`;
  } catch(e) { document.getElementById('portfolio-content').innerHTML = '<span class="text-danger small">Failed to load.</span>'; }
}

// Accuracy
async function loadAccuracy() {
  try {
    const resp = await fetch('/api/accuracy');
    const data = await resp.json();
    const el = document.getElementById('accuracy-content');
    const tickers = Object.entries(data.by_ticker || {});
    if (!tickers.length) { el.innerHTML = '<span class="text-muted small">No predictions recorded yet.</span>'; return; }
    el.innerHTML = `<p class="text-muted small">Total predictions: ${data.total_predictions}</p>` +
      tickers.map(([ticker, stats]) => {
        const pct = stats.total ? Math.round(stats.correct / stats.total * 100) : 0;
        const color = pct >= 60 ? '#3fb950' : pct >= 40 ? '#f0a500' : '#f85149';
        return `<div class="mb-3">
          <div class="d-flex justify-content-between mb-1">
            <span class="fw-semibold">${ticker}</span>
            <span style="color:${color}">${pct}% (${stats.correct}/${stats.total})</span>
          </div>
          <div class="accuracy-bar"><div class="accuracy-fill" style="width:${pct}%;background:${color}"></div></div>
        </div>`;
      }).join('');
  } catch(e) { document.getElementById('accuracy-content').innerHTML = '<span class="text-danger small">Failed to load.</span>'; }
}

// Usage
async function loadUsage() {
  try {
    const resp = await fetch('/api/usage');
    const data = await resp.json();
    const render = (label, rows) => {
      if (!rows.length) return `<p class="text-muted small">${label}: No data.</p>`;
      const total = rows.reduce((s, r) => s + (r.cost_usd || 0), 0);
      return `<div class="mb-4">
        <h6 class="text-muted">${label} — Total: $${total.toFixed(4)}</h6>
        <table class="table table-sm usage-table" style="font-size:0.82rem">
          <thead><tr><th>Model</th><th>Agent</th><th>Calls</th><th>In Tokens</th><th>Out Tokens</th><th>Cost</th></tr></thead>
          <tbody>${rows.map(r=>`<tr>
            <td>${r.model||''}</td><td>${r.agent||''}</td><td>${r.calls||0}</td>
            <td>${(r.input_tokens||0).toLocaleString()}</td><td>${(r.output_tokens||0).toLocaleString()}</td>
            <td>$${(r.cost_usd||0).toFixed(4)}</td></tr>`).join('')}
          </tbody>
        </table></div>`;
    };
    document.getElementById('usage-content').innerHTML =
      render('Today', data.today || []) + render('This Month', data.month || []);
  } catch(e) { document.getElementById('usage-content').innerHTML = '<span class="text-danger small">Failed to load.</span>'; }
}
