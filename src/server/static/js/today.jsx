const { useState, useEffect, useRef, useMemo } = React;

const fmtINR = (n) => n == null ? '—' : '₹' + Number(n).toLocaleString('en-IN');
const fmtPct = (n) => n == null ? '—' : (n > 0 ? '+' : '') + Number(n).toFixed(2) + '%';

function PipelineNode({ agent, idx, state, selected, onClick, progress }) {
  const cls = `pipe-node ${state} ${selected ? 'selected' : ''}`;
  return (
    <div className={cls} onClick={onClick}>
      <div className="top">
        <span>{String(idx + 1).padStart(2, '0')}</span>
        <span style={{ flex: 1 }}></span>
        {state === 'done' && <Icon name="check" size={11} stroke={2} />}
        {state === 'running' && <span style={{ display: 'inline-block', width: 6, height: 6, borderRadius: 99, background: 'var(--accent)', animation: 'pulse 1.4s infinite' }}></span>}
      </div>
      <div className="name">{agent.name}</div>
      <div className="meta"><span>{agent.role}</span></div>
      <div className="bar"><i style={{ width: state === 'done' ? '100%' : state === 'running' ? `${progress}%` : '0%' }}></i></div>
    </div>
  );
}

function ToolCallRow({ tc, idx, expanded, onToggle }) {
  const state = tc.done ? 'done' : tc.running ? 'running' : 'pending';
  return (
    <div className={`tc ${state}`}>
      <div className="tc-row" onClick={onToggle}>
        <span className="status"></span>
        <span style={{ color: 'var(--muted)', fontSize: 10.5, fontFamily: 'Geist Mono' }}>{String(idx + 1).padStart(2, '0')}</span>
        <span className="nm">
          <Icon name="wrench" size={11} style={{ marginRight: 6, opacity: .6 }} />
          {tc.name}
          <span className="args"> ({tc.input ? tc.input.slice(0, 60) : ''})</span>
        </span>
        <span className="dur">{tc.done ? '✓' : tc.running ? '…' : '—'}</span>
        <Icon name={expanded ? 'chevron-down' : 'chevron-right'} size={12} style={{ color: 'var(--muted)' }} />
      </div>
      {expanded && (
        <div className="tc-body">
          <div className="kv"><div className="k">input</div><pre>{tc.input || '—'}</pre></div>
          <div className="kv"><div className="k">output</div><pre>{tc.done ? (tc.output || '—') : tc.running ? '… streaming …' : '— awaiting —'}</pre></div>
        </div>
      )}
    </div>
  );
}

function AgentInspector({ agents, activeIdx, selectedIdx, setSelected, runProgress, streamText, streaming, toolCallsByAgent }) {
  const [expanded, setExpanded] = useState({});
  const agent = agents[selectedIdx];
  const agentState = selectedIdx < activeIdx ? 'done' : selectedIdx === activeIdx ? 'running' : 'pending';
  const tools = toolCallsByAgent[agent.id] || [];

  const toggleExpand = (i) => setExpanded(prev => ({ ...prev, [i]: !prev[i] }));

  return (
    <div className="card" style={{ overflow: 'hidden' }}>
      <div className="card-hd">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flex: 1 }}>
          <Icon name="wrench" size={14} style={{ color: 'var(--muted)' }} />
          <div className="ttl">Agent inspector</div>
          <div className="sub">{agentState === 'running' ? 'Live · token stream attached' : agentState === 'done' ? 'Completed' : 'Pending'}</div>
        </div>
      </div>
      <div className="inspector">
        <div className="insp-list">
          {agents.map((a, i) => {
            const st = i < activeIdx ? 'done' : i === activeIdx ? 'running' : 'pending';
            const cnt = (toolCallsByAgent[a.id] || []).length;
            return (
              <div key={a.id} className={`insp-tab ${i === selectedIdx ? 'active' : ''}`} onClick={() => setSelected(i)}>
                <span style={{
                  width: 6, height: 6, borderRadius: 99,
                  background: st === 'done' ? 'var(--success)' : st === 'running' ? 'var(--accent)' : 'var(--line-2)',
                  animation: st === 'running' ? 'pulse 1.4s infinite' : 'none',
                  flexShrink: 0,
                }}></span>
                <span>{a.name}</span>
                <span className="dur">{cnt || ''}</span>
              </div>
            );
          })}
        </div>
        <div className="insp-body">
          <div className="insp-h">
            <Icon name={agent.icon} size={16} style={{ color: 'var(--accent)' }} />
            <div>
              <div className="name">{agent.name}</div>
              <div className="role">{agent.role} · {tools.length} tool call{tools.length !== 1 ? 's' : ''}</div>
            </div>
            <div style={{ flex: 1 }}></div>
            <span className={`pill ${agentState === 'running' ? 'live' : agentState === 'done' ? '' : 'idle'}`}
              style={agentState === 'done' ? { color: '#1f5a37', background: 'var(--success-soft)', borderColor: 'rgba(47,125,82,.25)' } : {}}>
              {agentState === 'running' && <span className="dot"></span>}
              {agentState === 'pending' && <span className="dot"></span>}
              {agentState === 'done' ? 'done' : agentState === 'running' ? 'running' : 'pending'}
            </span>
          </div>

          <div style={{ fontSize: 11, color: 'var(--muted)', letterSpacing: '.06em', textTransform: 'uppercase', margin: '6px 0 8px' }}>Tool calls</div>
          <div className="toolcalls">
            {tools.length === 0 && <div style={{ fontSize: 12.5, color: 'var(--muted)', padding: '6px 0' }}>No tool calls yet.</div>}
            {tools.map((tc, i) => (
              <ToolCallRow key={i} tc={tc} idx={i} expanded={!!expanded[i]} onToggle={() => toggleExpand(i)} />
            ))}
          </div>

          {agent.id === 'synthesize' && (
            <>
              <div style={{ fontSize: 11, color: 'var(--muted)', letterSpacing: '.06em', textTransform: 'uppercase', margin: '14px 0 8px' }}>Token stream</div>
              <div className="stream">
                {streamText.split('\n').map((line, i) => (
                  <div key={i} dangerouslySetInnerHTML={{ __html: line.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>') }} />
                ))}
                {streaming && <span className="cur"></span>}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function MemoryCard({ memories }) {
  const [open, setOpen] = useState(true);
  const items = memories || [];
  return (
    <div className="card">
      <div className="card-hd" style={{ cursor: 'pointer' }} onClick={() => setOpen(!open)}>
        <Icon name="memory" size={14} style={{ color: 'var(--muted)' }} />
        <div className="ttl">Retrieved memories</div>
        <div className="sub">{items.length} from ChromaDB · injected into agent prompts</div>
        <div style={{ flex: 1 }}></div>
        <Icon name={open ? 'chevron-down' : 'chevron-right'} size={12} style={{ color: 'var(--muted)' }} />
      </div>
      {open && (
        <div className="card-bd" style={{ paddingTop: 10 }}>
          {items.length === 0
            ? <div style={{ fontSize: 12.5, color: 'var(--muted)' }}>No memories retrieved yet. Trigger a run to load context.</div>
            : (
              <div className="memory" style={{ background: 'transparent', border: 'none', padding: 0 }}>
                <div className="items">
                  {items.map((m, i) => (
                    <div key={i} className="item">
                      <span className="src">{m.src || m.source || 'mem'}</span>
                      {m.body || m.text || m.content || JSON.stringify(m)}
                    </div>
                  ))}
                </div>
              </div>
            )}
        </div>
      )}
    </div>
  );
}

function PredictionsTable({ preds, completed }) {
  return (
    <div className="card">
      <div className="card-hd">
        <Icon name="sparkle" size={14} style={{ color: 'var(--accent)' }} />
        <div className="ttl">Predictions</div>
        <div className="sub">
          {completed
            ? `${preds.length} calls · ${preds.filter(p => (p.dir || p.direction) === 'BUY').length} BUY · ${preds.filter(p => (p.dir || p.direction) === 'SELL').length} SELL`
            : 'awaiting orchestrator…'}
        </div>
        <div style={{ flex: 1 }}></div>
      </div>
      {completed ? (
        preds.length === 0
          ? <div className="card-bd" style={{ display: 'grid', placeItems: 'center', minHeight: 120, color: 'var(--muted)', fontSize: 13 }}>No predictions for today yet.</div>
          : (
            <table className="predictions">
              <thead>
                <tr>
                  <th>Ticker</th><th>Direction</th><th>Conf</th>
                  <th style={{ textAlign: 'right' }}>Entry</th>
                  <th style={{ textAlign: 'right' }}>Stop</th>
                  <th style={{ textAlign: 'right' }}>Target</th>
                  <th>R:R</th><th>Timeframe</th>
                </tr>
              </thead>
              <tbody>
                {preds.map(p => {
                  const dir = p.dir || p.direction || '';
                  const entry = p.entry || p.entry_price;
                  const stop = p.stop || p.stop_loss;
                  const target = p.target;
                  const conf = p.conf || p.confidence || '';
                  const confLevel = conf === 'High' ? 3 : conf === 'Medium' ? 2 : 1;
                  const rr = dir === 'HOLD' || !entry || !stop || !target ? '—'
                    : dir === 'BUY' ? ((target - entry) / (entry - stop)).toFixed(2)
                    : ((entry - target) / (stop - entry)).toFixed(2);
                  return (
                    <tr key={p.ticker}>
                      <td>
                        <div className="tk">{p.ticker}</div>
                        <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 1 }}>{p.reasoning || p.reason || ''}</div>
                      </td>
                      <td>
                        <span className={`dir ${dir.toLowerCase()}`}>
                          {dir === 'BUY' && <Icon name="arrow-up" size={10} stroke={2.4} />}
                          {dir === 'SELL' && <Icon name="arrow-down" size={10} stroke={2.4} />}
                          {dir}
                        </span>
                      </td>
                      <td>
                        <span className={`conf ${conf === 'High' ? 'high' : ''}`}>
                          {[1, 2, 3].map(i => <span key={i} className={`b ${i <= confLevel ? 'on' : ''}`}></span>)}
                        </span>
                        <div style={{ fontSize: 10.5, color: 'var(--muted)', marginTop: 2 }}>{conf}</div>
                      </td>
                      <td className="num" style={{ textAlign: 'right' }}>{fmtINR(entry)}</td>
                      <td className="num" style={{ textAlign: 'right', color: 'var(--danger)' }}>{fmtINR(stop)}</td>
                      <td className="num" style={{ textAlign: 'right', color: 'var(--success)' }}>{fmtINR(target)}</td>
                      <td className="num">{rr}</td>
                      <td style={{ fontSize: 11.5, color: 'var(--muted)' }}>{p.timeframe || '—'}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )
      ) : (
        <div className="card-bd" style={{ display: 'grid', placeItems: 'center', minHeight: 180, color: 'var(--muted)', fontSize: 13 }}>
          <div style={{ textAlign: 'center' }}>
            <div className="serif" style={{ fontSize: 34, fontStyle: 'italic', color: 'var(--muted-2)', marginBottom: 6 }}>waiting</div>
            <div>Predictions appear when the orchestrator finishes synthesis.</div>
          </div>
        </div>
      )}
    </div>
  );
}

function FinalAnalysisCard({ text, completed, streaming }) {
  const html = useMemo(() => {
    if (!text) return '';
    const lines = text.split('\n');
    let out = '';
    let inList = false;
    for (const ln of lines) {
      if (ln.startsWith('- ')) {
        if (!inList) { out += '<ul>'; inList = true; }
        out += '<li>' + ln.slice(2).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>') + '</li>';
      } else if (ln.trim() === '') {
        if (inList) { out += '</ul>'; inList = false; }
        out += '<div style="height:6px"></div>';
      } else if (ln.startsWith('**') && ln.includes(':**')) {
        if (inList) { out += '</ul>'; inList = false; }
        const m = ln.match(/\*\*(.+?):\*\*(.*)/);
        if (m) out += `<h4>${m[1]}</h4><div>${m[2].replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')}</div>`;
      } else {
        if (inList) { out += '</ul>'; inList = false; }
        out += '<div>' + ln.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>') + '</div>';
      }
    }
    if (inList) out += '</ul>';
    return out;
  }, [text]);

  return (
    <div className="card">
      <div className="card-hd">
        <Icon name="sparkle" size={14} style={{ color: 'var(--accent)' }} />
        <div className="ttl">Final analysis</div>
        <div className="sub">Orchestrator · gemini-2.0-flash</div>
        <div style={{ flex: 1 }}></div>
        {completed && <span className="pill" style={{ background: 'var(--success-soft)', borderColor: 'rgba(47,125,82,.25)', color: '#1f5a37' }}><Icon name="check" size={10} stroke={2.4} /> synthesized</span>}
        {streaming && <span className="pill live"><span className="dot"></span>streaming</span>}
      </div>
      <div className="card-bd">
        {text ? (
          <div className="analysis" dangerouslySetInnerHTML={{
            __html: html + (streaming ? '<span class="cur" style="display:inline-block;width:7px;height:14px;background:var(--accent);vertical-align:text-bottom;margin-left:2px;"></span>' : '')
          }} />
        ) : (
          <div style={{ minHeight: 100, display: 'grid', placeItems: 'center', color: 'var(--muted)', fontSize: 12.5 }}>Orchestrator hasn't started yet.</div>
        )}
      </div>
    </div>
  );
}

function PortfolioSnapshot() {
  const [portfolio, setPortfolio] = useState(null);
  useEffect(() => {
    API.fetchPortfolio().then(setPortfolio).catch(() => {});
  }, []);

  // Parse holdings from API response (returns {holdings: str, positions: str, pnl: str})
  const holdingsText = portfolio?.holdings || '';
  const pnlText = portfolio?.pnl || '';

  return (
    <div className="card">
      <div className="card-hd">
        <Icon name="portfolio" size={14} style={{ color: 'var(--muted)' }} />
        <div className="ttl">Portfolio</div>
        <div className="sub">Live via Kite</div>
        <div style={{ flex: 1 }}></div>
        {portfolio
          ? <span className="pill"><span className="dot" style={{ width: 6, height: 6, borderRadius: 99, background: 'var(--success)' }}></span>connected</span>
          : <span className="pill idle"><span className="dot"></span>loading</span>}
      </div>
      <div className="card-bd">
        {portfolio
          ? (
            <pre style={{ fontFamily: 'Geist Mono, monospace', fontSize: 11.5, color: 'var(--ink-2)', whiteSpace: 'pre-wrap', wordBreak: 'break-word', maxHeight: 220, overflow: 'auto', margin: 0 }}>
              {pnlText || holdingsText || 'No portfolio data.'}
            </pre>
          )
          : <div style={{ color: 'var(--muted)', fontSize: 12.5 }}>Loading portfolio…</div>}
      </div>
    </div>
  );
}

function GlobalContextStrip() {
  const [items, setItems] = useState([]);
  useEffect(() => {
    API.fetchPremarket().then(data => {
      setItems(data.map(d => ({
        lbl: d.label,
        val: d.value != null ? String(d.value) : '—',
        d: d.pct_change != null ? (d.pct_change >= 0 ? '+' : '') + d.pct_change.toFixed(2) + '%' : '—',
        up: d.positive,
      })));
    }).catch(() => {});
  }, []);

  const now = new Date().toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit' });

  return (
    <div className="card" style={{ padding: '10px 14px', display: 'flex', alignItems: 'center', gap: 18, overflowX: 'auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, paddingRight: 12, borderRight: '1px solid var(--line)' }}>
        <span className="pill live"><span className="dot"></span>live</span>
        <span style={{ fontSize: 11, color: 'var(--muted)' }}>{now} IST</span>
      </div>
      {items.length === 0
        ? <span style={{ fontSize: 12, color: 'var(--muted)' }}>Loading market data…</span>
        : items.map((it, i) => (
          <div key={i} style={{ display: 'flex', flexDirection: 'column', minWidth: 78 }}>
            <span style={{ fontSize: 10.5, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '.05em' }}>{it.lbl}</span>
            <span style={{ display: 'flex', alignItems: 'baseline', gap: 6, marginTop: 2 }}>
              <span className="mono" style={{ fontSize: 13, fontWeight: 600 }}>{it.val}</span>
              <span className="mono" style={{ fontSize: 11, color: it.d === '—' ? 'var(--muted)' : it.up ? 'var(--success)' : 'var(--danger)' }}>{it.d}</span>
            </span>
          </div>
        ))}
    </div>
  );
}

function TodayView({ runState, activeIdx, runProgress, streamText, streaming, completed, runError, onRunNow, toolCallsByAgent, memories, predictions, runId }) {
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [userPicked, setUserPicked] = useState(false);

  useEffect(() => {
    if (!userPicked && runState === 'running') setSelectedIdx(activeIdx);
  }, [activeIdx, runState, userPicked]);

  const now = new Date();
  const dateStr = now.toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long', timeZone: 'Asia/Kolkata' });
  const runTypeName = 'Run';

  return (
    <>
      <div className="page-title-row">
        <div>
          <div className="page-title">{runTypeName} · {dateStr}</div>
          <div className="page-sub">
            {runState === 'running' && <>Run active · agent {activeIdx + 1} of {AGENTS.length}</>}
            {runState === 'completed' && <>Completed · {predictions.length} predictions · dual-written to SQLite + ChromaDB</>}
            {runState === 'error' && <>Run failed · inspect the error below and fix model quota or credentials</>}
            {runState === 'idle' && <>No active run · trigger a run to begin</>}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {runState === 'running' && <span className="pill live"><span className="dot"></span>LIVE · streaming</span>}
          {runState === 'completed' && <span className="pill" style={{ background: 'var(--success-soft)', borderColor: 'rgba(47,125,82,.25)', color: '#1f5a37' }}><Icon name="check" size={10} stroke={2.4} /> completed</span>}
          {runState === 'error' && <span className="pill error"><Icon name="x" size={10} stroke={2.4} /> failed</span>}
          {runState === 'idle' && <span className="pill idle"><span className="dot"></span>idle</span>}
          <button className="btn btn-accent" onClick={onRunNow}>
            <Icon name="play" size={11} /> Run now
          </button>
        </div>
      </div>

      <div style={{ marginBottom: 14 }}>
        <GlobalContextStrip />
      </div>

      <div className="split">
        <div className="col">
          <div className="card pipeline-card">
            <div className="card-hd">
              <Icon name="graph" size={14} style={{ color: 'var(--muted)' }} />
              <div className="ttl">Execution flow</div>
              <div className="sub">load_context → news → technical → portfolio → options → synthesize</div>
              <div style={{ flex: 1 }}></div>
              {runId && <span className="mono" style={{ fontSize: 11.5, color: 'var(--muted)' }}>run: {runId}</span>}
            </div>
            <div className="card-bd">
              <div className="pipeline">
                {AGENTS.map((a, i) => {
                  const allDone = runState === 'completed' || runState === 'idle';
                  const st = allDone ? 'done' : i < activeIdx ? 'done' : i === activeIdx ? (runState === 'running' ? 'running' : 'pending') : 'pending';
                  return (
                    <PipelineNode
                      key={a.id}
                      agent={a} idx={i}
                      state={st}
                      selected={selectedIdx === i}
                      progress={i === activeIdx ? runProgress : 0}
                      onClick={() => { setSelectedIdx(i); setUserPicked(true); }}
                    />
                  );
                })}
              </div>
            </div>
          </div>

          <AgentInspector
            agents={AGENTS}
            activeIdx={runState === 'completed' || runState === 'idle' ? AGENTS.length : activeIdx}
            selectedIdx={selectedIdx}
            setSelected={(i) => { setSelectedIdx(i); setUserPicked(true); }}
            runProgress={runProgress}
            streamText={streamText}
            streaming={streaming}
            toolCallsByAgent={toolCallsByAgent}
          />

          <MemoryCard memories={memories} />
        </div>

        <div className="col">
          {runState === 'error' && (
            <div className="card">
              <div className="card-hd">
                <Icon name="x" size={14} style={{ color: 'var(--danger)' }} />
                <div className="ttl">Run error</div>
                <div className="sub">The backend ended the run with an explicit error.</div>
              </div>
              <div className="card-bd">
                <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word', color: 'var(--danger)', fontSize: 12 }}>
                  {runError || 'Run failed.'}
                </pre>
              </div>
            </div>
          )}
          <FinalAnalysisCard text={streamText} completed={completed} streaming={streaming && !completed} />
          <PredictionsTable preds={predictions} completed={completed || runState === 'idle'} />
          <PortfolioSnapshot />
        </div>
      </div>
    </>
  );
}

window.TodayView = TodayView;
