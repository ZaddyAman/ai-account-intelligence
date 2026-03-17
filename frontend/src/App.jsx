import { useState, useEffect } from 'react';
import { fetchVisitors, analyzeVisitor, analyzeCompany, analyzeBatch, fetchHistory, clearHistory } from './api/client';

/* ═══════════════════════════════════════════════════════
   App — AI Account Intelligence Dashboard
   ═══════════════════════════════════════════════════════ */

export default function App() {
  const [mode, setMode] = useState('visitor');
  const [visitors, setVisitors] = useState(() => []);
  const [selectedVisitor, setSelectedVisitor] = useState(null);
  const [companyText, setCompanyText] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [history, setHistory] = useState(() => []);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchVisitors()
      .then(setVisitors)
      .catch(() => setVisitors([]));

    refreshHistory();
  }, []);

  const refreshHistory = async () => {
    try {
      const h = await fetchHistory(15);
      setHistory(h);
    } catch (e) {
      console.error(e);
    }
  };

  const handleClearHistory = async () => {
    if (window.confirm('Clear all analysis history?')) {
      await clearHistory();
      setHistory([]);
    }
  };

  const handleAnalyze = async () => {
    setLoading(true);
    setError('');
    setResults(null);
    try {
      if (mode === 'visitor' && selectedVisitor) {
        const res = await analyzeVisitor(selectedVisitor);
        setResults(res);
      } else if (mode === 'company' && companyText.trim()) {
        const lines = companyText.trim().split('\n').filter(l => l.trim());
        if (lines.length === 1) {
          const res = await analyzeCompany(lines[0].trim());
          setResults(res);
        } else {
          const res = await analyzeBatch(lines);
          setResults(res);
        }
      }
    } catch (e) {
      setError(e.message || 'Something went wrong');
    } finally {
      setLoading(false);
      refreshHistory();
    }
  };

  const canAnalyze = mode === 'visitor' ? !!selectedVisitor : companyText.trim().length > 0;

  return (
    <main className="app-container">
      {/* Header */}
      <header className="header" role="banner">
        <div className="header-brand">
          <div className="header-logo" aria-hidden="true">IQ</div>
          <div>
            <h1>AccountIQ</h1>
            <div className="header-subtitle">AI Account Intelligence & Enrichment</div>
          </div>
        </div>
        <div className="header-badge" aria-label="AI Powered Feature">⚡ AI-Powered</div>
      </header>

      {/* Input Panel */}
      <section className="input-panel" aria-labelledby="input-panel-heading">
        <h2 id="input-panel-heading" className="sr-only">Input Panel</h2>
        <div className="input-tabs" role="tablist" aria-label="Analysis mode">
          <button
            className={`input-tab ${mode === 'visitor' ? 'active' : ''}`}
            onClick={() => { setMode('visitor'); setResults(null); }}
            role="tab"
            aria-selected={mode === 'visitor'}
            aria-controls="visitor-panel"
          >
            [1] Visitors
          </button>
          <button
            className={`input-tab ${mode === 'company' ? 'active' : ''}`}
            onClick={() => { setMode('company'); setResults(null); }}
            role="tab"
            aria-selected={mode === 'company'}
            aria-controls="company-panel"
          >
            [2] Companies
          </button>
          <button
            className={`input-tab ${mode === 'history' ? 'active' : ''}`}
            onClick={() => { setMode('history'); setResults(null); }}
            role="tab"
            aria-selected={mode === 'history'}
            aria-controls="history-panel"
          >
            [3] History
          </button>
        </div>

        <div id={mode === 'visitor' ? 'visitor-panel' : mode === 'company' ? 'company-panel' : 'history-panel'} role="tabpanel">

          {mode === 'visitor' && (
            <>
              <div className="visitor-grid">
                {visitors.map(v => (
                  <button
                    key={v.visitor_id}
                    className={`visitor-card ${selectedVisitor?.visitor_id === v.visitor_id ? 'selected' : ''}`}
                    onClick={() => setSelectedVisitor(v)}
                    aria-label={`Select visitor ${v.visitor_id}`}
                  >
                    <div className="visitor-card-id">{v.visitor_id}</div>
                    <div className="visitor-card-meta">
                      <span>● {v.location}</span>
                      <span>● {v.pages_visited.length} pages</span>
                      <span>● {v.visits_this_week}x this week</span>
                    </div>
                  </button>
                ))}
              </div>
            </>
          )}

          {mode === 'company' && (
            <div className="company-input-area">
              <label htmlFor="company-input" className="sr-only">Company names</label>
              <textarea
                id="company-input"
                value={companyText}
                onChange={e => setCompanyText(e.target.value)}
                placeholder={"Enter company names (one per line):\n\nRocket Mortgage\nRedfin\nCompass Real Estate"}
                aria-describedby="company-input-hint"
              />
              <div id="company-input-hint" className="company-input-hint">
                Enter one company per line. Batch analysis supports up to 10 companies.
              </div>
            </div>
          )}

          {mode === 'history' && (
            <div className="history-grid">
              {history.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)', gridColumn: '1/-1' }}>
                  No history yet. Start analyzing companies!
                </div>
              ) : (
                history.map((h, i) => (
                  <button
                    key={i}
                    className="history-card"
                    onClick={() => { setResults(h); window.scrollTo({ top: 600, behavior: 'smooth' }); }}
                    aria-label={`View analysis for ${h.company_identification?.company_name}`}
                  >
                    <div className="history-card-id">◆ {h.company_identification?.company_name}</div>
                    <div className="history-meta">
                      <span>{h.company_profile?.industry}</span>
                      <span>{new Date(h.analyzed_at).toLocaleDateString()}</span>
                    </div>
                  </button>
                ))
              )}
              {history.length > 0 && <button className="copy-btn" onClick={handleClearHistory} style={{ gridColumn: '1/-1', width: 'fit-content' }}>Clear History</button>}
            </div>
          )}

          {mode !== 'history' && (
            <button
              className="analyze-btn"
              onClick={handleAnalyze}
              disabled={!canAnalyze || loading}
              aria-label={loading ? 'Analyzing company data' : 'Analyze company data'}
            >
              <span>{loading ? '◉ Processing...' : '▶ Execute Analysis'}</span>
            </button>
          )}
        </div>
      </section>

      {/* Loading State */}
      {loading && <LoadingState />}

      {/* Error */}
      {error && (
        <div style={{ color: 'var(--accent-rose)', textAlign: 'center', padding: '20px', fontSize: '0.9rem' }}>
          ❌ {error}
        </div>
      )}

      {/* Results */}
      {results && !loading && (
        <section aria-labelledby="results-heading">
          <h2 id="results-heading" className="sr-only">Analysis Results</h2>
          {Array.isArray(results)
            ? results.map((r, i) => <ResultsDashboard key={i} data={r} />)
            : <ResultsDashboard data={results} />
          }
        </section>
      )}
    </main>
  );
}


/* ─── Loading Component ─────────────────────────────────────────── */
function LoadingState() {
  const agents = [
    'Company Identification', 'Profile Enrichment', 'Tech Stack Detection',
    'Business Signals', 'Leadership Discovery', 'Persona Inference',
    'Intent Scoring', 'AI Summary Generation'
  ];
  return (
    <div className="loading-container" role="status" aria-live="polite" aria-label="Loading analysis">
      <div className="loading-spinner" aria-hidden="true" />
      <div className="loading-text">◉ Executing AI Agents…</div>
      <div className="loading-agents" aria-label="Active agents">
        {agents.map(a => <span key={a} className="loading-agent-chip">{a}</span>)}
      </div>
    </div>
  );
}


/* ─── Results Dashboard ─────────────────────────────────────────── */
function ResultsDashboard({ data }) {
  const conf = data.overall_confidence;
  const confLevel = conf >= 0.7 ? 'high' : conf >= 0.4 ? 'mid' : 'low';

  const handleExportJSON = () => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${data.company_profile?.company_name || 'report'}.json`;
    a.click();
  };

  const handleExportCSV = () => {
    const csv = `Field,Value\nName,${data.company_profile?.company_name}\nIndustry,${data.company_profile?.industry}\nSize,${data.company_profile?.company_size}\nIntent,${data.intent?.score}/10\nPersona,${data.persona?.likely_persona}`;
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${data.company_profile?.company_name || 'report'}.csv`;
    a.click();
  };

  return (
    <div style={{ marginBottom: '40px' }}>
      <div className="results-header">
        <h2>▸ {data.company_profile?.company_name || data.company_identification?.company_name || 'Account Intelligence'}</h2>
        <div className="confidence-badge">
          <div className={`confidence-dot confidence-${confLevel}`} />
          {Math.round(conf * 100)}% overall confidence
        </div>
        <div className="results-actions">
          <button className="action-btn" onClick={handleExportJSON}>↓ Export JSON</button>
          <button className="action-btn" onClick={handleExportCSV}>↓ Export CSV</button>
        </div>
      </div>

      {/* AI Summary (full width, top) */}
      {data.ai_summary ? (
        <div className="card summary-card" style={{ marginBottom: '20px' }}>
          <div className="card-header">
            <div className="card-icon indigo" aria-hidden="true">◈</div>
            <div>
              <div className="card-title">AI Intelligence Summary</div>
              <div className="card-subtitle">Generated by multi-agent analysis</div>
            </div>
          </div>
          <div className="summary-text">{data.ai_summary}</div>
        </div>
      ) : null}

      <div className="results-grid">
        {/* Company Profile */}
        <CompanyProfileCard profile={data.company_profile} />

        {/* Intent Score */}
        <IntentCard intent={data.intent} />

        {/* Persona */}
        <PersonaCard persona={data.persona} />

        {/* Tech Stack */}
        <TechStackCard techStack={data.tech_stack} />

        {/* Competitors & ICP */}
        <CompetitorsCard icp={data.icp_score} />

        {/* Outreach Drafts */}
        <OutreachCard outreach={data.outreach} />

        {/* Leadership */}
        <LeadershipCard leadership={data.leadership} />

        {/* Business Signals */}
        <BusinessSignalsCard signals={data.business_signals} />
      </div>

      {/* Sales Actions (full width, bottom) */}
      {data.recommended_actions?.length > 0 ? (
        <SalesActionsCard actions={data.recommended_actions} />
      ) : null}
    </div>
  );
}


/* ─── Company Profile Card ──────────────────────────────────────── */
function CompanyProfileCard({ profile }) {
  if (!profile) return null;
  return (
    <div className="card">
      <div className="card-header">
        <div className="card-icon purple" aria-hidden="true">◈</div>
        <div>
          <div className="card-title">Company Profile</div>
          <div className="card-subtitle">{Math.round(profile.confidence * 100)}% confidence</div>
        </div>
      </div>
      <div className="info-row"><span className="info-label">Industry</span><span className="info-value">{profile.industry || '—'}</span></div>
      <div className="info-row"><span className="info-label">Size</span><span className="info-value">{profile.company_size || '—'}</span></div>
      <div className="info-row"><span className="info-label">HQ</span><span className="info-value">{profile.headquarters || '—'}</span></div>
      <div className="info-row"><span className="info-label">Founded</span><span className="info-value">{profile.founding_year || '—'}</span></div>
      <div className="info-row"><span className="info-label">Website</span><span className="info-value">{profile.domain || '—'}</span></div>
      {profile.description && (
        <div style={{ marginTop: '12px', fontSize: '0.82rem', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
          {profile.description}
        </div>
      )}
    </div>
  );
}


/* ─── Intent Gauge Card ─────────────────────────────────────────── */
function IntentCard({ intent }) {
  if (!intent) return null;
  const score = intent.score || 0;
  const circumference = 2 * Math.PI * 54;
  const offset = circumference - (score / 10) * circumference;
  const color = score >= 7 ? 'var(--accent-emerald)' : score >= 4 ? 'var(--accent-amber)' : 'var(--accent-rose)';
  const stageColor = score >= 7 ? 'rgba(16,185,129,0.15)' : score >= 4 ? 'rgba(245,158,11,0.15)' : 'rgba(244,63,94,0.15)';

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-icon emerald" aria-hidden="true">⌖</div>
        <div>
          <div className="card-title">Intent Score</div>
          <div className="card-subtitle">{intent.stage}</div>
        </div>
      </div>
      <div className="intent-gauge-container">
        <div className="intent-gauge">
          <svg viewBox="0 0 120 120">
            <circle className="intent-gauge-bg" cx="60" cy="60" r="54" />
            <circle
              className="intent-gauge-fill"
              cx="60" cy="60" r="54"
              stroke={color}
              strokeDasharray={circumference}
              strokeDashoffset={offset}
            />
          </svg>
          <div className="intent-gauge-score">
            <div className="intent-gauge-number" style={{ color }}>{score}</div>
            <div className="intent-gauge-label">/ 10</div>
          </div>
        </div>
        <div className="intent-stage-badge" style={{ background: stageColor, color }}>
          {intent.stage}
        </div>
        {intent.signals?.length > 0 ? (
          <div className="intent-signals">
            {intent.signals.map((s, i) => (
              <div key={i} className="intent-signal-item">
                <div className="intent-signal-dot" />
                {s}
              </div>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}


/* ─── Persona Card ──────────────────────────────────────────────── */
function PersonaCard({ persona }) {
  if (!persona) return null;
  return (
    <div className="card">
      <div className="card-header">
        <div className="card-icon cyan" aria-hidden="true">◉</div>
        <div>
          <div className="card-title">Persona Inference</div>
          <div className="card-subtitle">{Math.round(persona.confidence * 100)}% confidence</div>
        </div>
      </div>
      <div className="info-row"><span className="info-label">Likely Persona</span><span className="info-value">{persona.likely_persona || '—'}</span></div>
      <div className="info-row"><span className="info-label">Department</span><span className="info-value">{persona.department || '—'}</span></div>
      <div className="info-row"><span className="info-label">Seniority</span><span className="info-value">{persona.seniority || '—'}</span></div>
      {persona.reasoning && (
        <div style={{ marginTop: '12px', fontSize: '0.78rem', color: 'var(--text-muted)', lineHeight: '1.5' }}>
          💡 {persona.reasoning}
        </div>
      )}
    </div>
  );
}


/* ─── Tech Stack Card ───────────────────────────────────────────── */
function TechStackCard({ techStack }) {
  if (!techStack?.items?.length) return null;
  return (
    <div className="card">
      <div className="card-header">
        <div className="card-icon amber" aria-hidden="true">⚙</div>
        <div>
          <div className="card-title">Technology Stack</div>
          <div className="card-subtitle">{techStack.items.length} technologies detected</div>
        </div>
      </div>
      <div className="tech-grid">
        {techStack.items.map((t, i) => (
          <div key={i} className="tech-badge">
            <span className="tech-category">{t.category}</span>
            <span className="tech-name">{t.technology}</span>
          </div>
        ))}
      </div>
    </div>
  );
}


/* ─── Leadership Card ───────────────────────────────────────────── */
function LeadershipCard({ leadership }) {
  if (!leadership?.leaders?.length) return null;
  return (
    <div className="card">
      <div className="card-header">
        <div className="card-icon rose" aria-hidden="true">⬡</div>
        <div>
          <div className="card-title">Key Decision Makers</div>
          <div className="card-subtitle">{leadership.leaders.length} leaders identified</div>
        </div>
      </div>
      {leadership.leaders.map((l, i) => (
        <div key={i} className="leader-item">
          <div className="leader-avatar">
            {(l.name || '??').split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()}
          </div>
          <div className="leader-info">
            <div className="leader-name">{l.name || 'Unknown'}</div>
            <div className="leader-title">{l.title} · {l.department}</div>
          </div>
        </div>
      ))}
    </div>
  );
}


/* ─── Business Signals Card ─────────────────────────────────────── */
function BusinessSignalsCard({ signals }) {
  if (!signals?.signals?.length) return null;
  return (
    <div className="card">
      <div className="card-header">
        <div className="card-icon cyan" aria-hidden="true">◈</div>
        <div>
          <div className="card-title">Business Signals</div>
          <div className="card-subtitle">{signals.signals.length} signals detected</div>
        </div>
      </div>
      {signals.signals.map((s, i) => (
        <div key={i} className="signal-item">
          <span className={`signal-type-badge ${s.signal_type}`}>{s.signal_type}</span>
          <span className="signal-desc">{s.description}</span>
        </div>
      ))}
    </div>
  );
}


/* ─── Competitors & ICP Card ────────────────────────────────────── */
function CompetitorsCard({ icp }) {
  if (!icp || !icp.competitors?.length) return null;
  return (
    <div className="card">
      <div className="card-header">
        <div className="card-icon amber" aria-hidden="true">⦿</div>
        <div>
          <div className="card-title">Competitors & ICP Fit</div>
          <div className="card-subtitle">{icp.fit_level.toUpperCase()} fit ({Math.round(icp.score)}/10)</div>
        </div>
      </div>
      <div className="competitor-list">
        {icp.competitors.map((c, i) => (
          <div key={i} className="competitor-item">
            <span className="comp-name">{c.name}</span>
            <span className="comp-similarity">{c.similarity}</span>
          </div>
        ))}
      </div>
      <div className="icp-reasoning">
        {icp.reasoning}
      </div>
    </div>
  );
}

/* ─── Outreach Draft Card ────────────────────────────────────────── */
function OutreachCard({ outreach }) {
  if (!outreach || !outreach.email_subject) return null;
  return (
    <div className="card full-width">
      <div className="card-header">
        <div className="card-icon indigo" aria-hidden="true">✧</div>
        <div>
          <div className="card-title">Personalized Outreach Drafts</div>
          <div className="card-subtitle">AI-composed for the top decision maker</div>
        </div>
      </div>
      <div className="outreach-grid">
        <div className="outreach-section">
          <span className="outreach-label">Cold Email Draft</span>
          <div className="outreach-text">
            <strong>Subject: {outreach.email_subject}</strong><br /><br />
            {outreach.email_body}
          </div>
          <button className="copy-btn" onClick={() => navigator.clipboard.writeText(`Subject: ${outreach.email_subject}\n\n${outreach.email_body}`)}>Copy Email</button>
        </div>
        <div className="outreach-section">
          <span className="outreach-label">LinkedIn Connection Note</span>
          <div className="outreach-text">{outreach.linkedin_note}</div>
          <button className="copy-btn" onClick={() => navigator.clipboard.writeText(outreach.linkedin_note)}>Copy Note</button>
        </div>
      </div>
    </div>
  );
}

/* ─── Sales Actions Card ────────────────────────────────────────── */
function SalesActionsCard({ actions }) {
  return (
    <div className="card full-width">
      <div className="card-header">
        <div className="card-icon emerald" aria-hidden="true">▸</div>
        <div>
          <div className="card-title">Recommended Sales Actions</div>
          <div className="card-subtitle">{actions.length} actions suggested</div>
        </div>
      </div>
      {actions.map((a, i) => (
        <div key={i} className="action-item">
          <div className={`action-priority ${a.priority}`} />
          <div className="action-content">
            <div className="action-text">{a.action}</div>
            <div className="action-reasoning">{a.reasoning}</div>
          </div>
        </div>
      ))}
    </div>
  );
}
