// Agent pipeline definition (6 nodes: loader + 4 analysts + synthesizer)
window.AGENTS = [
  { id: 'load_context',      name: 'Context',     role: 'Loader',        icon: 'database' },
  { id: 'news_analyst',      name: 'News',         role: 'Sentiment',     icon: 'doc' },
  { id: 'technical_analyst', name: 'Technical',    role: 'Charts',        icon: 'accuracy' },
  { id: 'portfolio_risk',    name: 'Portfolio',    role: 'Risk',          icon: 'portfolio' },
  { id: 'options_analyst',   name: 'Options',      role: 'Flow',          icon: 'graph' },
  { id: 'synthesize',        name: 'Orchestrator', role: 'Synthesizer',   icon: 'sparkle' },
];

const _json = (r) => { if (!r.ok) throw new Error(r.status); return r.json(); };

window.API = {
  fetchHistory:         () => fetch('/api/history').then(_json),
  fetchAccuracy:        () => fetch('/api/accuracy').then(_json),
  fetchUsage:           () => fetch('/api/usage').then(_json),
  fetchPortfolio:       () => fetch('/api/portfolio').then(_json),
  fetchPredictionsToday:() => fetch('/api/predictions/today').then(_json),
  fetchHypotheses:      (s) => fetch(`/api/hypotheses${s ? '?status=' + s : ''}`).then(_json),
  createHypothesis:     (d) => fetch('/api/hypotheses', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(d) }).then(_json),
  updateHypothesis:     (id, d) => fetch(`/api/hypotheses/${id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(d) }).then(_json),
  deleteHypothesis:     (id) => fetch(`/api/hypotheses/${id}`, { method: 'DELETE' }).then(_json),
  fetchFeedback:        () => fetch('/api/feedback').then(_json),
  fetchPremarket:       () => fetch('/api/market/premarket').then(_json),
  fetchConfig:          () => fetch('/api/config').then(_json),
  triggerRun:           (type, body = {}) => fetch(`/run/${type}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(_json),

  streamRun(runId, handlers) {
    const es = new EventSource(`/stream/${runId}`);
    const on = (evt, fn) => es.addEventListener(evt, (e) => { try { fn(JSON.parse(e.data)); } catch(_) {} });
    on('agent_start',  (d) => handlers.onAgentStart?.(d));
    on('agent_end',    (d) => handlers.onAgentEnd?.(d));
    on('tool_start',   (d) => handlers.onToolStart?.(d));
    on('tool_end',     (d) => handlers.onToolEnd?.(d));
    on('llm_stream',   (d) => handlers.onToken?.(d));
    on('error',        (d) => handlers.onRunError?.(d));
    on('run_complete', (d) => { handlers.onComplete?.(d); es.close(); });
    es.onerror = () => { handlers.onError?.(); es.close(); };
    return es;
  },
};
