const { useCallback } = React;

function App() {
  const [view, setView] = React.useState('today');
  const [runModalOpen, setRunModalOpen] = React.useState(false);

  // Run state
  const [runState, setRunState] = React.useState('idle');   // idle | running | completed | error
  const [activeIdx, setActiveIdx] = React.useState(-1);
  const [runProgress, setRunProgress] = React.useState(0);
  const [streamText, setStreamText] = React.useState('');
  const [streaming, setStreaming] = React.useState(false);
  const [completed, setCompleted] = React.useState(false);
  const [runId, setRunId] = React.useState(null);
  const [toolCallsByAgent, setToolCallsByAgent] = React.useState({});
  const [memories, setMemories] = React.useState([]);
  const [predictions, setPredictions] = React.useState([]);
  const [runError, setRunError] = React.useState('');

  const esRef = React.useRef(null);
  const activeAgentRef = React.useRef('load_context');
  const runErrorRef = React.useRef('');

  // Map agent id → index
  const agentIdx = React.useMemo(() => {
    const m = {};
    AGENTS.forEach((a, i) => { m[a.id] = i; });
    return m;
  }, []);

  const startRunWithTracking = useCallback((params) => {
    if (esRef.current) { esRef.current.close(); esRef.current = null; }

    setRunState('running');
    setActiveIdx(0);
    setRunProgress(0);
    setStreamText('');
    setStreaming(false);
    setCompleted(false);
    setToolCallsByAgent({});
    setMemories([]);
    setPredictions([]);
    setRunError('');
    runErrorRef.current = '';

    activeAgentRef.current = AGENTS[0]?.id || 'load_context';

    API.triggerRun(params.runType, {
      watchlist: params.watchlist?.length ? params.watchlist : undefined,
      model: params.model,
      notes: params.note,
    }).then(({ run_id }) => {
      setRunId(run_id);

      let prog = 0;
      const progTimer = setInterval(() => {
        prog = Math.min(prog + 1.5, 90);
        setRunProgress(prog);
      }, 250);

      esRef.current = API.streamRun(run_id, {
        onAgentStart: ({ agent }) => {
          activeAgentRef.current = agent;
          const i = agentIdx[agent] ?? 0;
          setActiveIdx(i);
          setRunProgress(0);
          prog = 0;
          setToolCallsByAgent(prev => ({ ...prev, _currentAgent: agent }));
        },
        onAgentEnd: ({ agent, report }) => {
          if (agent === 'synthesize' && report) setStreamText(report);
        },
        onToolStart: ({ tool, input }) => {
          const cur = activeAgentRef.current;
          setToolCallsByAgent(prev => {
            const existing = prev[cur] || [];
            return { ...prev, _currentAgent: cur, [cur]: [...existing, { name: tool, input: input || '', done: false, running: true }] };
          });
        },
        onToolEnd: ({ tool, output }) => {
          const cur = activeAgentRef.current;
          setToolCallsByAgent(prev => {
            const existing = [...(prev[cur] || [])];
            const idx = existing.map((t, i) => t.running && t.name === tool ? i : -1).filter(i => i >= 0).pop();
            if (idx !== undefined && idx >= 0) {
              existing[idx] = { ...existing[idx], done: true, running: false, output: output || '' };
            }
            return { ...prev, [cur]: existing };
          });
        },
        onRunError: ({ message, kind, retry_after_seconds }) => {
          const retry = retry_after_seconds ? ` Retry after about ${retry_after_seconds}s.` : '';
          const prefix = kind === 'quota' ? 'Gemini quota exhausted.' : 'Run failed.';
          const fullMessage = `${prefix} ${message}${retry}`.trim();
          runErrorRef.current = fullMessage;
          setRunError(fullMessage);
        },
        onToken: ({ token }) => {
          if (token) { setStreamText(t => t + token); setStreaming(true); }
        },
        onComplete: ({ status, report, error }) => {
          clearInterval(progTimer);
          const failed = status !== 'completed';
          setRunState(failed ? 'error' : 'completed');
          setCompleted(!failed);
          setStreaming(false);
          setRunProgress(100);
          setActiveIdx(failed ? (agentIdx[activeAgentRef.current] ?? 0) : AGENTS.length);
          if (failed) {
            const msg = runErrorRef.current || error || report || 'Run failed before the model returned a report.';
            runErrorRef.current = msg;
            setRunError(msg);
            setStreamText(msg);
            return;
          }
          if (report) setStreamText(report);
          API.fetchPredictionsToday().then(setPredictions).catch(() => {});
        },
        onError: () => {
          clearInterval(progTimer);
          const msg = runErrorRef.current || 'Stream disconnected before the run completed.';
          runErrorRef.current = msg;
          setRunState('error');
          setRunError(msg);
        },
      });
    }).catch(() => {
      setRunState('error');
      setRunError('Failed to start the run.');
    });
  }, [agentIdx]);

  React.useEffect(() => () => { if (esRef.current) esRef.current.close(); }, []);

  // Load today's predictions on mount (in case a run was done earlier)
  React.useEffect(() => {
    API.fetchPredictionsToday().then(setPredictions).catch(() => {});
  }, []);

  const nav = [
    { id: 'today',     name: 'Today',           icon: 'today',     badge: runState === 'running' ? 'LIVE' : '' },
    { id: 'history',   name: 'History',          icon: 'history' },
    { id: 'portfolio', name: 'Portfolio',         icon: 'portfolio' },
    { id: 'gold',      name: 'Gold',             icon: 'gold' },
    { id: 'accuracy',  name: 'Accuracy',          icon: 'accuracy' },
  ];
  const nav2 = [
    { id: 'hypotheses', name: 'Hypotheses',      icon: 'hyp' },
    { id: 'feedback',   name: 'Weekly feedback',  icon: 'feedback' },
    { id: 'usage',      name: 'API usage',        icon: 'usage' },
  ];

  const screenLabels = {
    today: '01 Today', history: '02 History', portfolio: '03 Portfolio',
    gold: '04 Gold', accuracy: '05 Accuracy', hypotheses: '06 Hypotheses',
    feedback: '07 Weekly feedback', usage: '08 API usage',
  };

  const now = new Date();
  const clockStr = now.toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit' }) + ' IST';
  const dateLabel = now.toLocaleDateString('en-IN', { weekday: 'short', month: 'short', day: 'numeric', timeZone: 'Asia/Kolkata' });

  const activeAgentName = AGENTS[activeIdx]?.name || '';

  return (
    <div className="app">
      {/* Logo */}
      <div className="logo-cell">
        <div className="logo">
          <div className="logo-mark">M</div>
          <div>
            <div className="logo-name">MarketCruise <span className="v">v0.4</span></div>
            <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 1 }}>NSE · BSE · Personal AI</div>
          </div>
        </div>
      </div>

      {/* Header */}
      <div className="header-cell">
        <div className="header">
          <div className="breadcrumb">
            <span>Dashboard</span>
            <span className="sep">/</span>
            <span className="cur">{[...nav, ...nav2].find(n => n.id === view)?.name}</span>
          </div>
          <div className="grow"></div>
          <div className="search">
            <Icon name="search" size={13} />
            <input placeholder="Search runs, tickers, hypotheses…" readOnly />
            <span className="kbd">⌘K</span>
          </div>
          <span className="mono" style={{ fontSize: 12, color: 'var(--muted)' }}>{dateLabel} · {clockStr}</span>
          {runState === 'running'
            ? <span className="pill live"><span className="dot"></span>LIVE run · {activeAgentName}</span>
            : <span className="pill"><span className="dot" style={{ width: 6, height: 6, borderRadius: 99, background: 'var(--success)' }}></span>server :8001 · idle</span>}
          <button className="btn btn-accent btn-sm" onClick={() => setRunModalOpen(true)}>
            <Icon name="play" size={11} /> Run now
          </button>
        </div>
      </div>

      {/* Sidebar */}
      <div className="side-cell">
        <div className="side">
          <div className="side-section">Workspace</div>
          <div className="nav">
            {nav.map(n => (
              <div key={n.id} className={`nav-item ${view === n.id ? 'active' : ''}`} onClick={() => setView(n.id)}>
                <span className="glyph"><Icon name={n.icon} size={14} /></span>
                <span>{n.name}</span>
                {n.badge && <span className="badge">{n.badge}</span>}
              </div>
            ))}
          </div>

          <div className="side-section" style={{ marginTop: 14 }}>Memory & feedback</div>
          <div className="nav">
            {nav2.map(n => (
              <div key={n.id} className={`nav-item ${view === n.id ? 'active' : ''}`} onClick={() => setView(n.id)}>
                <span className="glyph"><Icon name={n.icon} size={14} /></span>
                <span>{n.name}</span>
                {n.badge && <span className="badge">{n.badge}</span>}
              </div>
            ))}
          </div>

          <div className="side-foot">
            <div className="row">
              <span className="dot" style={{ background: 'var(--accent)' }}></span>
              <span className="label">Gemini</span>
              <span style={{ flex: 1 }}></span>
              <span className="val">2.0-flash</span>
            </div>
            <div className="row">
              <span className="dot" style={{ background: 'var(--info)' }}></span>
              <span className="label">ChromaDB</span>
              <span style={{ flex: 1 }}></span>
              <span className="val">active</span>
            </div>
            <div className="row">
              <span className="dot"></span>
              <span className="label">Kite</span>
              <span style={{ flex: 1 }}></span>
              <a href="/kite/login" style={{ fontSize: 12, color: 'var(--accent)', textDecoration: 'none' }}>connect →</a>
            </div>
          </div>
        </div>
      </div>

      {/* Main */}
      <div className="main-cell">
        <div className="main">
          {view === 'today' && (
            <TodayView
              runState={runState}
              activeIdx={activeIdx}
              runProgress={runProgress}
              streamText={streamText}
              streaming={streaming}
              completed={completed}
              runError={runError}
              onRunNow={() => setRunModalOpen(true)}
              toolCallsByAgent={toolCallsByAgent}
              memories={memories}
              predictions={predictions}
              runId={runId}
            />
          )}
          {view === 'history' && <HistoryView />}
          {view === 'portfolio' && <PortfolioView />}
          {view === 'gold' && <GoldView />}
          {view === 'accuracy' && <AccuracyView />}
          {view === 'hypotheses' && <HypothesesView />}
          {view === 'feedback' && <FeedbackView />}
          {view === 'usage' && <UsageView />}
        </div>
      </div>

      {runModalOpen && (
        <RunNowModal
          onClose={() => setRunModalOpen(false)}
          onStart={(p) => { setView('today'); startRunWithTracking(p); }}
        />
      )}
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
