function useData(fetchFn, deps = []) {
  const [data, setData] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState(null);
  React.useEffect(() => {
    setLoading(true);
    fetchFn().then(d => { setData(d); setLoading(false); }).catch(e => { setError(String(e)); setLoading(false); });
  }, deps);
  return { data, loading, error, reload: () => fetchFn().then(setData).catch(() => {}) };
}

function Loading() {
  return <div style={{ padding: 40, textAlign: 'center', color: 'var(--muted)', fontSize: 13 }}>Loading…</div>;
}

function Err({ msg }) {
  return <div style={{ padding: 24, color: 'var(--danger)', fontSize: 12.5 }}>{msg || 'Error loading data.'}</div>;
}

// ---------- HISTORY ----------

function HistoryView() {
  const [filter, setFilter] = React.useState('all');
  const { data: runs, loading, error, reload } = useData(() => API.fetchHistory());

  const filtered = React.useMemo(() => {
    if (!runs) return [];
    return filter === 'all' ? runs : runs.filter(r => r.run_type === filter);
  }, [runs, filter]);

  const statusDot = (r) => {
    if (r.status === 'completed') return 'ok';
    if (r.status === 'error') return 'err';
    if (r.status === 'running') return 'run';
    return 'ok';
  };

  return (
    <>
      <div className="page-title-row">
        <div>
          <div className="page-title">Run history</div>
          <div className="page-sub">{runs ? `${runs.length} runs` : '…'} · cron triggers, manual runs, and weekly feedback</div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <div className="seg">
            {['all', 'morning', 'midday', 'evening', 'weekly'].map(t => (
              <button key={t} className={filter === t ? 'on' : ''} onClick={() => setFilter(t)}>
                {t[0].toUpperCase() + t.slice(1)}
              </button>
            ))}
          </div>
          <button className="btn btn-ghost btn-sm" onClick={reload}><Icon name="refresh" size={12} /></button>
        </div>
      </div>

      <div className="card">
        <div className="card-hd">
          <Icon name="history" size={14} style={{ color: 'var(--muted)' }} />
          <div className="ttl">Runs</div>
          <div className="sub">click a row to view details</div>
        </div>
        {loading && <Loading />}
        {error && <Err msg={error} />}
        {!loading && !error && (
          <div className="runs-list">
            <div className="run-row" style={{ borderTop: 'none', background: 'var(--surface-2)', fontSize: 10.5, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--muted)', fontWeight: 500, cursor: 'default' }}>
              <span></span><span>Date</span><span>Type</span><span>Summary</span><span style={{ textAlign: 'right' }}>Status</span><span style={{ textAlign: 'right' }}>Finished</span><span></span>
            </div>
            {filtered.length === 0 && <div style={{ padding: '24px 14px', color: 'var(--muted)', fontSize: 12.5 }}>No runs yet.</div>}
            {filtered.map(r => (
              <div key={r.run_id} className="run-row">
                <span className={`dot ${statusDot(r)}`}></span>
                <span className="date">{(r.started_at || '').slice(0, 10)}</span>
                <span className="type">{(r.run_type || '').charAt(0).toUpperCase() + (r.run_type || '').slice(1)}</span>
                <span className="summary">{(r.report_text || '').slice(0, 80) || '—'}</span>
                <span className="acc" style={{ textAlign: 'right' }}>{r.status}</span>
                <span className="dur" style={{ textAlign: 'right' }}>{(r.finished_at || '').slice(11, 16) || '—'}</span>
                <span>
                  {r.status === 'completed' && <span className="pill" style={{ background: 'var(--success-soft)', borderColor: 'rgba(47,125,82,.25)', color: '#1f5a37', fontSize: 10.5 }}>ok</span>}
                  {r.status === 'error' && <span className="pill error" style={{ fontSize: 10.5 }}>err</span>}
                  {r.status === 'running' && <span className="pill live" style={{ fontSize: 10.5 }}><span className="dot"></span>live</span>}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );
}

// ---------- PORTFOLIO ----------

function Spark({ pct }) {
  const n = 14;
  const pts = Array.from({ length: n }, (_, i) => {
    const v = pct + Math.sin(i * 0.9) * 4;
    return [i / (n - 1) * 60, 22 - (v - pct + 8) * 1.2];
  });
  const d = 'M' + pts.map(p => p.join(',')).join(' L');
  return (
    <svg className="spark" viewBox="0 0 60 22">
      <path d={d} fill="none" stroke={pct >= 0 ? 'var(--success)' : 'var(--danger)'} strokeWidth="1.4" />
    </svg>
  );
}

function PortfolioView() {
  const { data: portfolio, loading, error, reload } = useData(() => API.fetchPortfolio());

  return (
    <>
      <div className="page-title-row">
        <div>
          <div className="page-title">Portfolio</div>
          <div className="page-sub">Connected to Zerodha Kite · live P&L</div>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <span className="pill"><span className="dot" style={{ width: 6, height: 6, borderRadius: 99, background: 'var(--success)' }}></span>kite</span>
          <button className="btn" onClick={reload}><Icon name="refresh" size={12} /> Refresh</button>
        </div>
      </div>

      <div className="card">
        <div className="card-hd">
          <Icon name="portfolio" size={14} style={{ color: 'var(--muted)' }} />
          <div className="ttl">Holdings & P&L</div>
        </div>
        {loading && <Loading />}
        {error && <Err msg={error} />}
        {!loading && !error && (
          <div className="card-bd">
            <pre style={{ fontFamily: 'Geist Mono, monospace', fontSize: 12, whiteSpace: 'pre-wrap', wordBreak: 'break-word', color: 'var(--ink-2)', margin: 0 }}>
              {portfolio?.pnl || portfolio?.holdings || 'No portfolio data available. Check Kite token.'}
            </pre>
          </div>
        )}
      </div>
    </>
  );
}

// ---------- ACCURACY ----------

function AccuracyView() {
  const [period, setPeriod] = React.useState('30d');
  const { data: acc, loading, error } = useData(() => API.fetchAccuracy());

  const byTicker = React.useMemo(() => {
    if (!acc?.by_ticker) return [];
    return Object.entries(acc.by_ticker).map(([tk, v]) => ({
      tk,
      v: v.total > 0 ? Math.round((v.correct / v.total) * 100) : 0,
      correct: v.correct,
      total: v.total,
    })).sort((a, b) => b.v - a.v);
  }, [acc]);

  const overall = React.useMemo(() => {
    if (!acc?.by_ticker) return { pct: 0, correct: 0, total: 0 };
    let c = 0, t = 0;
    Object.values(acc.by_ticker).forEach(v => { c += v.correct; t += v.total; });
    return { pct: t > 0 ? Math.round((c / t) * 100) : 0, correct: c, total: t };
  }, [acc]);

  return (
    <>
      <div className="page-title-row">
        <div>
          <div className="page-title">Accuracy</div>
          <div className="page-sub">30-day rolling hit-rate · computed from SQLite predictions × actuals</div>
        </div>
        <div className="seg">
          {['7d', '30d', '90d'].map(p => (
            <button key={p} className={period === p ? 'on' : ''} onClick={() => setPeriod(p)}>{p}</button>
          ))}
        </div>
      </div>

      <div className="kpis" style={{ gridTemplateColumns: 'repeat(4, 1fr)', marginBottom: 14 }}>
        <div className="kpi"><div className="lbl">Overall</div><div className="val">{overall.pct}%</div><div className="sub">{overall.total} evaluated calls</div></div>
        <div className="kpi"><div className="lbl">Tickers tracked</div><div className="val">{byTicker.length}</div><div className="sub">with actuals data</div></div>
        <div className="kpi"><div className="lbl">Correct calls</div><div className="val up">{overall.correct}</div><div className="sub">of {overall.total} total</div></div>
        <div className="kpi"><div className="lbl">Total predictions</div><div className="val">{acc?.total_predictions || 0}</div><div className="sub">30-day window</div></div>
      </div>

      <div className="card">
        <div className="card-hd">
          <Icon name="accuracy" size={14} style={{ color: 'var(--muted)' }} />
          <div className="ttl">By ticker</div>
          <div className="sub">hit-rate per symbol — where the model has edge</div>
        </div>
        {loading && <Loading />}
        {error && <Err msg={error} />}
        {!loading && !error && (
          <div className="card-bd">
            {byTicker.length === 0
              ? <div style={{ color: 'var(--muted)', fontSize: 12.5 }}>No accuracy data yet. Predictions need actuals data to compute accuracy.</div>
              : (
                <div className="barchart">
                  {byTicker.map(t => (
                    <div key={t.tk} className="row">
                      <span className="tk">{t.tk}</span>
                      <div className="track">
                        <div className={`fill ${t.v >= 70 ? 'good' : t.v >= 55 ? '' : 'bad'}`} style={{ width: `${t.v}%` }}></div>
                      </div>
                      <span className="v">{t.v}% <span style={{ color: 'var(--muted)', fontSize: 10.5 }}>({t.correct}/{t.total})</span></span>
                    </div>
                  ))}
                </div>
              )}
          </div>
        )}
      </div>
    </>
  );
}

// ---------- HYPOTHESES ----------

function HypothesisForm({ onSave, onCancel, config }) {
  const [form, setForm] = React.useState({ ticker: '', thesis: '', evidence: '', entry_price: '', stop_loss: '', target: '', expiry: '', ...config });
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));
  const submit = () => {
    if (!form.ticker || !form.thesis) return;
    onSave({
      ticker: form.ticker.toUpperCase(),
      thesis: form.thesis,
      evidence: form.evidence,
      entry_price: form.entry_price ? Number(form.entry_price) : null,
      stop_loss: form.stop_loss ? Number(form.stop_loss) : null,
      target: form.target ? Number(form.target) : null,
      expiry: form.expiry || null,
    });
  };
  const inp = { border: '1px solid var(--line)', borderRadius: 6, padding: '6px 10px', background: 'var(--surface-2)', font: 'inherit', color: 'var(--ink)', outline: 'none', width: '100%' };
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
        <div>
          <div className="field-lbl">Ticker *</div>
          <input style={inp} value={form.ticker} onChange={e => set('ticker', e.target.value)} placeholder="e.g. TCS" />
        </div>
        <div>
          <div className="field-lbl">Expiry</div>
          <input style={inp} type="date" value={form.expiry || ''} onChange={e => set('expiry', e.target.value)} />
        </div>
      </div>
      <div>
        <div className="field-lbl">Thesis *</div>
        <textarea style={{ ...inp, minHeight: 60, resize: 'vertical' }} value={form.thesis} onChange={e => set('thesis', e.target.value)} placeholder="Your hypothesis…" />
      </div>
      <div>
        <div className="field-lbl">Evidence</div>
        <input style={inp} value={form.evidence} onChange={e => set('evidence', e.target.value)} placeholder="Supporting signals…" />
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
        <div><div className="field-lbl">Entry ₹</div><input style={inp} type="number" value={form.entry_price} onChange={e => set('entry_price', e.target.value)} placeholder="0.00" /></div>
        <div><div className="field-lbl">Stop ₹</div><input style={inp} type="number" value={form.stop_loss} onChange={e => set('stop_loss', e.target.value)} placeholder="0.00" /></div>
        <div><div className="field-lbl">Target ₹</div><input style={inp} type="number" value={form.target} onChange={e => set('target', e.target.value)} placeholder="0.00" /></div>
      </div>
      <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 4 }}>
        <button className="btn" onClick={onCancel}>Cancel</button>
        <button className="btn btn-accent" onClick={submit}><Icon name="check" size={11} /> Save</button>
      </div>
    </div>
  );
}

function HypothesesView() {
  const [filter, setFilter] = React.useState('all');
  const [hyps, setHyps] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  const [showCreate, setShowCreate] = React.useState(false);
  const [editId, setEditId] = React.useState(null);

  const load = () => { setLoading(true); API.fetchHypotheses().then(d => { setHyps(d); setLoading(false); }).catch(() => setLoading(false)); };
  React.useEffect(load, []);

  const filtered = React.useMemo(() => {
    if (!hyps) return [];
    return filter === 'all' ? hyps : hyps.filter(h => h.status === filter);
  }, [hyps, filter]);

  const counts = React.useMemo(() => ({
    all: (hyps || []).length,
    open: (hyps || []).filter(h => h.status === 'open').length,
    won: (hyps || []).filter(h => h.status === 'won').length,
    lost: (hyps || []).filter(h => h.status === 'lost').length,
  }), [hyps]);

  const create = (data) => API.createHypothesis(data).then(() => { setShowCreate(false); load(); });
  const closeHyp = (id, status) => API.updateHypothesis(id, { status, closed_at: new Date().toISOString() }).then(load);
  const del = (id) => { if (confirm('Delete this hypothesis?')) API.deleteHypothesis(id).then(load); };

  return (
    <>
      <div className="page-title-row">
        <div>
          <div className="page-title">Hypothesis ledger</div>
          <div className="page-sub">Open bets and closed outcomes · {counts.all} total</div>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <div className="seg">
            {[['all', 'All'], ['open', 'Open'], ['won', 'Won'], ['lost', 'Lost']].map(([k, l]) => (
              <button key={k} className={filter === k ? 'on' : ''} onClick={() => setFilter(k)}>
                {l} <span style={{ opacity: .6, marginLeft: 4 }}>{counts[k]}</span>
              </button>
            ))}
          </div>
          <button className="btn btn-accent btn-sm" onClick={() => setShowCreate(true)}>
            <Icon name="plus" size={11} /> New
          </button>
        </div>
      </div>

      {showCreate && (
        <div className="card" style={{ padding: 16, marginBottom: 14 }}>
          <div className="card-hd" style={{ marginBottom: 12 }}>
            <div className="ttl">New hypothesis</div>
          </div>
          <div className="card-bd">
            <HypothesisForm onSave={create} onCancel={() => setShowCreate(false)} config={{}} />
          </div>
        </div>
      )}

      <div className="kpis" style={{ gridTemplateColumns: 'repeat(4, 1fr)', marginBottom: 14 }}>
        <div className="kpi"><div className="lbl">Open</div><div className="val">{counts.open}</div></div>
        <div className="kpi"><div className="lbl">Won</div><div className="val up">{counts.won}</div></div>
        <div className="kpi"><div className="lbl">Lost</div><div className="val dn">{counts.lost}</div></div>
        <div className="kpi"><div className="lbl">Win rate</div><div className="val">{counts.won + counts.lost > 0 ? Math.round(counts.won / (counts.won + counts.lost) * 100) : '—'}%</div></div>
      </div>

      {loading && <Loading />}
      {!loading && (
        <div className="hyp-grid">
          {filtered.length === 0 && <div style={{ color: 'var(--muted)', fontSize: 12.5, gridColumn: '1/-1', padding: 24 }}>No hypotheses found. Create one above.</div>}
          {filtered.map(h => (
            editId === h.id
              ? (
                <div key={h.id} className="card" style={{ padding: 14, gridColumn: 'span 2' }}>
                  <HypothesisForm
                    config={h}
                    onSave={(data) => API.updateHypothesis(h.id, data).then(() => { setEditId(null); load(); })}
                    onCancel={() => setEditId(null)}
                  />
                </div>
              )
              : (
                <div key={h.id} className="hyp">
                  <div className="hd">
                    <span className="tk">{h.ticker}</span>
                    <span className={`stat ${h.status || 'open'}`}>{(h.status || 'open').toUpperCase()}</span>
                    <span style={{ flex: 1 }}></span>
                    <span style={{ fontSize: 11, color: 'var(--muted)', fontFamily: 'Geist Mono' }}>{(h.date || '').slice(0, 10)}</span>
                  </div>
                  <div className="thesis">{h.thesis}</div>
                  {h.evidence && <div className="ev"><b>Evidence:</b> {h.evidence}</div>}
                  {(h.entry_price || h.target) && (
                    <div className="ft">
                      {h.entry_price && <span>entry {fmtINR(h.entry_price)}</span>}
                      {h.target && <><span>·</span><span>target {fmtINR(h.target)}</span></>}
                      {h.expiry && <><span>·</span><span>expiry {h.expiry}</span></>}
                    </div>
                  )}
                  <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
                    <button className="btn btn-ghost btn-sm" onClick={() => setEditId(h.id)}><Icon name="wrench" size={11} /></button>
                    {h.status === 'open' && <>
                      <button className="btn btn-sm" style={{ color: '#1f5a37' }} onClick={() => closeHyp(h.id, 'won')}>Won</button>
                      <button className="btn btn-sm" style={{ color: '#7a2918' }} onClick={() => closeHyp(h.id, 'lost')}>Lost</button>
                    </>}
                    <button className="btn btn-ghost btn-sm" style={{ marginLeft: 'auto', color: 'var(--danger)' }} onClick={() => del(h.id)}><Icon name="x" size={11} /></button>
                  </div>
                </div>
              )
          ))}
        </div>
      )}
    </>
  );
}

// ---------- FEEDBACK ----------

function FeedbackView() {
  const { data: fb, loading, error } = useData(() => API.fetchFeedback());

  return (
    <>
      <div className="page-title-row">
        <div>
          <div className="page-title">Weekly feedback</div>
          <div className="page-sub">Latest weekly self-review · from SQLite runs</div>
        </div>
      </div>

      {loading && <Loading />}
      {error && <Err msg={error} />}
      {!loading && !error && (
        fb?.report
          ? (
            <div className="card">
              <div className="card-hd">
                <Icon name="feedback" size={14} style={{ color: 'var(--muted)' }} />
                <div className="ttl">Latest weekly report</div>
                <div className="sub">{fb.date ? fb.date.slice(0, 10) : 'No date'}</div>
              </div>
              <div className="card-bd">
                <pre style={{ fontFamily: 'Geist, sans-serif', fontSize: 13.5, lineHeight: 1.6, whiteSpace: 'pre-wrap', wordBreak: 'break-word', color: 'var(--ink-2)', margin: 0 }}>
                  {fb.report}
                </pre>
              </div>
            </div>
          )
          : (
            <div className="card">
              <div className="card-bd" style={{ display: 'grid', placeItems: 'center', minHeight: 260 }}>
                <div style={{ textAlign: 'center', color: 'var(--muted)' }}>
                  <div className="serif" style={{ fontSize: 40, fontStyle: 'italic', color: 'var(--muted-2)', marginBottom: 10 }}>no data</div>
                  <div style={{ fontSize: 13 }}>No weekly feedback run yet. Trigger a <strong>Weekly</strong> run from the Run Now modal.</div>
                </div>
              </div>
            </div>
          )
      )}
    </>
  );
}

// ---------- USAGE ----------

function UsageView() {
  const [period, setPeriod] = React.useState('today');
  const { data: usage, loading, error } = useData(() => API.fetchUsage());

  const rows = React.useMemo(() => {
    if (!usage) return [];
    return period === 'today' ? (usage.today || []) : (usage.month || []);
  }, [usage, period]);

  const totals = React.useMemo(() => rows.reduce((s, r) => ({
    input: s.input + (r.input_tokens || 0),
    output: s.output + (r.output_tokens || 0),
    cost: s.cost + (r.cost_usd || 0),
    calls: s.calls + (r.calls || 0),
  }), { input: 0, output: 0, cost: 0, calls: 0 }), [rows]);

  const maxCost = Math.max(...rows.map(r => r.cost_usd || 0), 0.001);

  return (
    <>
      <div className="page-title-row">
        <div>
          <div className="page-title">API usage</div>
          <div className="page-sub">Gemini tokens & cost · from SQLite usage_log table</div>
        </div>
        <div className="seg">
          {[['today', 'Today'], ['month', 'This month']].map(([k, l]) => (
            <button key={k} className={period === k ? 'on' : ''} onClick={() => setPeriod(k)}>{l}</button>
          ))}
        </div>
      </div>

      <div className="kpis" style={{ gridTemplateColumns: 'repeat(4, 1fr)', marginBottom: 14 }}>
        <div className="kpi"><div className="lbl">Input tokens</div><div className="val">{totals.input.toLocaleString()}</div></div>
        <div className="kpi"><div className="lbl">Output tokens</div><div className="val">{totals.output.toLocaleString()}</div></div>
        <div className="kpi"><div className="lbl">API calls</div><div className="val">{totals.calls}</div></div>
        <div className="kpi"><div className="lbl">Cost (USD)</div><div className="val">${totals.cost.toFixed(4)}</div></div>
      </div>

      <div className="card">
        <div className="card-hd">
          <Icon name="usage" size={14} style={{ color: 'var(--muted)' }} />
          <div className="ttl">By agent · {period}</div>
          <div className="sub">model usage and cost attribution</div>
        </div>
        {loading && <Loading />}
        {error && <Err msg={error} />}
        {!loading && !error && (
          <div className="card-bd">
            {rows.length === 0
              ? <div style={{ color: 'var(--muted)', fontSize: 12.5 }}>No usage data recorded yet.</div>
              : rows.map((r, i) => {
                const pct = maxCost > 0 ? (r.cost_usd / maxCost) * 100 : 0;
                return (
                  <div key={i} className="usage-row" style={{ gridTemplateColumns: '160px 130px 1fr 100px 80px' }}>
                    <span style={{ fontWeight: 500, fontSize: 13 }}>{r.agent || '—'}</span>
                    <span className="nm">{r.model || '—'}</span>
                    <div className="track"><div className="fill" style={{ width: `${pct}%`, background: 'var(--accent)' }}></div></div>
                    <span className="nm" style={{ textAlign: 'right' }}>{((r.input_tokens || 0) + (r.output_tokens || 0)).toLocaleString()}</span>
                    <span className="nm" style={{ textAlign: 'right', fontWeight: 500 }}>${(r.cost_usd || 0).toFixed(4)}</span>
                  </div>
                );
              })}
          </div>
        )}
      </div>
    </>
  );
}

// ---------- RUN NOW MODAL ----------

function RunNowModal({ onClose, onStart }) {
  const [runType, setRunType] = React.useState('morning');
  const [watchlist, setWatchlist] = React.useState([]);
  const [adding, setAdding] = React.useState('');
  const [note, setNote] = React.useState('');
  const [model, setModel] = React.useState('gemini-2.0-flash');

  React.useEffect(() => {
    API.fetchConfig().then(d => setWatchlist(d.watchlist || [])).catch(() => {});
  }, []);

  const remove = (t) => setWatchlist(watchlist.filter(x => x !== t));
  const add = () => {
    const v = adding.trim().toUpperCase();
    if (v && !watchlist.includes(v)) { setWatchlist([...watchlist, v]); setAdding(''); }
  };

  return (
    <div className="modal-scrim" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-hd">
          <Icon name="play" size={14} style={{ color: 'var(--accent)' }} />
          <div>
            <div className="ttl">Run now</div>
            <div className="sub">Trigger an ad-hoc run · POST /run/{runType}</div>
          </div>
          <div style={{ flex: 1 }}></div>
          <button className="btn btn-icon btn-ghost" onClick={onClose}><Icon name="x" size={12} /></button>
        </div>

        <div className="modal-bd">
          <div style={{ marginBottom: 16 }}>
            <div className="field-lbl">Run type</div>
            <div className="seg">
              {['morning', 'midday', 'evening', 'weekly'].map(t => (
                <button key={t} className={runType === t ? 'on' : ''} onClick={() => setRunType(t)}>
                  {t[0].toUpperCase() + t.slice(1)}
                </button>
              ))}
            </div>
            <div style={{ fontSize: 11.5, color: 'var(--muted)', marginTop: 8 }}>
              {runType === 'morning' && 'Pre-market context, sentiment scan, EOD setup → full daily graph.'}
              {runType === 'midday' && 'Lighter scan during the session; focuses on intraday tools.'}
              {runType === 'evening' && 'Post-close: extract actuals, mark predictions, update accuracy.'}
              {runType === 'weekly' && 'Feedback graph: reviews predictions vs. actuals, embeds lessons in ChromaDB.'}
            </div>
          </div>

          <div style={{ marginBottom: 16 }}>
            <div className="field-lbl">Watchlist override · {watchlist.length} tickers</div>
            <div className="chips">
              {watchlist.map(t => (
                <span key={t} className="chip">
                  {t}<span className="x" onClick={() => remove(t)}><Icon name="x" size={10} /></span>
                </span>
              ))}
              <span className="chip-add">
                <Icon name="plus" size={10} style={{ color: 'var(--muted)' }} />
                <input
                  placeholder="add ticker"
                  value={adding}
                  onChange={e => setAdding(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') add(); }}
                />
              </span>
            </div>
          </div>

          <div style={{ marginBottom: 16 }}>
            <div className="field-lbl">Model</div>
            <div className="seg">
              {['gemini-2.0-flash', 'gemini-2.5-flash', 'gemini-2.5-pro'].map(m => (
                <button key={m} className={model === m ? 'on' : ''} onClick={() => setModel(m)}>{m}</button>
              ))}
            </div>
          </div>

          <div>
            <div className="field-lbl">Notes</div>
            <input
              value={note}
              onChange={e => setNote(e.target.value)}
              placeholder="e.g. testing options sentiment flag"
              style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--line)', borderRadius: 8, background: 'var(--surface-2)', font: 'inherit', color: 'var(--ink)', outline: 'none' }}
            />
          </div>
        </div>

        <div className="modal-ft">
          <div style={{ fontSize: 12, color: 'var(--muted)' }}>Watchlist from config.yaml — can be overridden above.</div>
          <div className="grow"></div>
          <button className="btn" onClick={onClose}>Cancel</button>
          <button className="btn btn-accent" onClick={() => { onStart({ runType, watchlist, model, note }); onClose(); }}>
            <Icon name="play" size={11} /> Start run
          </button>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { HistoryView, PortfolioView, AccuracyView, HypothesesView, FeedbackView, UsageView, RunNowModal });
