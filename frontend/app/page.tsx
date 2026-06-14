"use client";
import "./globals.css";
import { useState, useRef, useCallback } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/* ── Types ── */
interface Score {
  overall_match: number;
  skill_score: number;
  tfidf_score: number;
  semantic_score: number;
  matched_skills: string[];
  missing_skills: string[];
  matched_count: number;
  missing_count: number;
  label: string;
}
interface Candidate {
  rank: number;
  name: string;
  filename: string;
  skills: string[];
  skills_detail: {
    education?: string[];
    experience_years?: number | null;
    email?: string | null;
    phone?: string | null;
  };
  score: Score;
}
interface AnalyzeResult {
  ranked: Candidate[];
  jd_skills: string[];
  total_candidates: number;
  errors?: { filename: string; error: string }[];
}

/* ── Helpers ── */
function matchClass(pct: number) {
  if (pct >= 65) return "match-strong";
  if (pct >= 50) return "match-good";
  return "match-low";
}
function rankBadgeClass(rank: number) {
  if (rank === 1) return "rank-1";
  if (rank === 2) return "rank-2";
  if (rank === 3) return "rank-3";
  return "rank-n";
}
function barClass(v: number) {
  if (v >= 65) return "bar-fill-orange";
  if (v >= 50) return "bar-fill-mid";
  return "bar-fill-low";
}
function emoji(pct: number) {
  if (pct >= 65) return "🟢";
  if (pct >= 50) return "🟡";
  return "🔴";
}

/* ── GitHubIcon ── */
const GitHubIcon = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
    <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38
    0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13
    -.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66
    .07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15
    -.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0
    1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82
    1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01
    1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
  </svg>
);

/* ── CandidateCard ── */
function CandidateCard({ c, onDownloadPDF, onDownloadCSV }: {
  c: Candidate;
  onDownloadPDF: (c: Candidate) => void;
  onDownloadCSV: (c: Candidate) => void;
}) {
  const [open, setOpen] = useState(false);
  const s = c.score;
  return (
    <div className="candidate-card">
      <div className="candidate-header" onClick={() => setOpen(!open)}>
        <div className="candidate-left">
          <div className={`rank-badge ${rankBadgeClass(c.rank)}`}>{c.rank}</div>
          <div>
            <div className="candidate-name">{emoji(s.overall_match)} {c.name}</div>
            <div className="candidate-file">{c.filename}</div>
          </div>
        </div>
        <div className="candidate-right">
          <span className={`match-pill ${matchClass(s.overall_match)}`}>{s.overall_match}%</span>
          <span className="label-badge">{s.label}</span>
          <span className={`chevron ${open ? "open" : ""}`}>▾</span>
        </div>
      </div>

      {open && (
        <div className="candidate-body">
          {/* Left col */}
          <div>
            <div className="card-title">Score Breakdown</div>
            {[
              { label: "Skill Overlap (40%)", val: s.skill_score },
              { label: "TF-IDF Similarity (35%)", val: s.tfidf_score },
              { label: "Semantic Similarity (25%)", val: s.semantic_score },
            ].map(({ label, val }) => (
              <div key={label}>
                <div className="score-row">
                  <span className="score-label">{label}</span>
                  <span className="score-val">{val}%</span>
                </div>
                <div className="mini-bar-track">
                  <div className="mini-bar-fill" style={{ width: `${val}%` }} />
                </div>
                <div style={{ marginBottom: 12 }} />
              </div>
            ))}

            {c.skills_detail.experience_years != null && (
              <p className="info-row">Experience: <span>~{c.skills_detail.experience_years} yrs</span></p>
            )}
            {c.skills_detail.email && (
              <p className="info-row">Email: <span>{c.skills_detail.email}</span></p>
            )}
            {(c.skills_detail.education ?? []).length > 0 && (
              <>
                <p className="info-row" style={{ marginTop: 8 }}>Education:</p>
                {c.skills_detail.education!.map((e) => (
                  <p key={e} className="info-row" style={{ marginLeft: 8 }}>• <span>{e}</span></p>
                ))}
              </>
            )}

            <div className="dl-btns">
              <button className="dl-btn" onClick={() => onDownloadPDF(c)}>📥 PDF Report</button>
              <button className="dl-btn" onClick={() => onDownloadCSV(c)}>📥 CSV</button>
            </div>
          </div>

          {/* Right col */}
          <div>
            <div className="card-title">Matched Skills</div>
            <div className="skills-cloud" style={{ marginBottom: 20 }}>
              {s.matched_skills.length > 0
                ? s.matched_skills.map((sk) => <span key={sk} className="skill-tag skill-match">{sk}</span>)
                : <span style={{ fontSize: "0.82rem", color: "var(--text-muted)" }}>None matched</span>}
            </div>

            <div className="card-title">Missing Skills</div>
            <div className="skills-cloud">
              {s.missing_skills.length > 0
                ? s.missing_skills.map((sk) => <span key={sk} className="skill-tag skill-miss">{sk}</span>)
                : <span style={{ fontSize: "0.82rem", color: "var(--green)" }}>✅ All required skills present!</span>}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ══════════════════════════════════════════
   Main Page
══════════════════════════════════════════ */
export default function Home() {
  /* State */
  const [jdTab, setJdTab] = useState<"paste" | "file">("paste");
  const [jdText, setJdText] = useState("");
  const [jdFile, setJdFile] = useState<File | null>(null);
  const [resumes, setResumes] = useState<File[]>([]);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<AnalyzeResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const resumeInputRef = useRef<HTMLInputElement>(null);
  const jdInputRef = useRef<HTMLInputElement>(null);

  const canAnalyze = (jdText.trim() || jdFile) && resumes.length > 0 && !loading;

  /* Drag handlers */
  const onDragOver = useCallback((e: React.DragEvent) => { e.preventDefault(); setDragging(true); }, []);
  const onDragLeave = useCallback(() => setDragging(false), []);
  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setDragging(false);
    const files = Array.from(e.dataTransfer.files).filter(f => f.type === "application/pdf");
    setResumes(prev => [...prev, ...files]);
  }, []);

  /* Analyze */
  const analyze = async () => {
    setLoading(true); setError(null); setResult(null); setProgress(10);
    try {
      const fd = new FormData();
      if (jdTab === "paste") fd.append("jd_text", jdText);
      else if (jdFile) fd.append("jd_file", jdFile);
      resumes.forEach(f => fd.append("resumes", f));

      setProgress(35);
      const res = await fetch(`${API}/api/analyze`, { method: "POST", body: fd });
      setProgress(80);
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Analysis failed");
      }
      const data: AnalyzeResult = await res.json();
      setProgress(100);
      setResult(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setLoading(false);
      setTimeout(() => setProgress(0), 600);
    }
  };

  /* Download PDF */
  const downloadPDF = async (c: Candidate) => {
    const res = await fetch(`${API}/api/report/pdf`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ candidate_name: c.name, score: c.score, skills: c.skills }),
    });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url;
    a.download = `report_${c.name.replace(/ /g, "_")}.pdf`; a.click();
    URL.revokeObjectURL(url);
  };

  /* Download CSV (single) */
  const downloadCSV = async (c: Candidate) => {
    const res = await fetch(`${API}/api/report/csv`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ results: [{ ...c }] }),
    });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url;
    a.download = `report_${c.name.replace(/ /g, "_")}.csv`; a.click();
    URL.revokeObjectURL(url);
  };

  /* Download all CSV */
  const downloadAllCSV = async () => {
    if (!result) return;
    const res = await fetch(`${API}/api/report/csv`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ results: result.ranked }),
    });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url;
    a.download = "all_candidates.csv"; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="page">
      {/* ── Header ── */}
      <header className="header">
        <div className="header-inner">
          <a href="/" className="logo">
            <div className="logo-icon">📄</div>
            Resume<span className="logo-dot">.</span>AI
          </a>
          <div className="header-links">
            <a href="https://github.com/httpsankuu" target="_blank" rel="noopener noreferrer" className="github-icon-btn" title="GitHub Profile — @httpsankuu">
              <GitHubIcon />
            </a>
          </div>
        </div>
      </header>

      {/* ── Hero ── */}
      <section className="hero">
        <div className="hero-badge">⚡ AI-Powered • NLP • Instant Ranking</div>
        <h1>Resume <span>Analyzer</span> AI</h1>
        <p>Upload resumes, paste a job description, and get AI-powered match scores in seconds.</p>
        <div className="hero-stats">
          <div className="hero-stat"><div className="hero-stat-value">200+</div><div className="hero-stat-label">Skills Tracked</div></div>
          <div className="hero-stat"><div className="hero-stat-value">3×</div><div className="hero-stat-label">Scoring Methods</div></div>
          <div className="hero-stat"><div className="hero-stat-value">100%</div><div className="hero-stat-label">Private & Local</div></div>
        </div>
      </section>

      {/* ── Main ── */}
      <main className="main">

        {/* Progress bar */}
        {loading && (
          <div className="progress-bar-wrap">
            <div className="progress-bar" style={{ width: `${progress}%` }} />
          </div>
        )}

        {/* Error */}
        {error && <div className="error-banner">⚠️ {error}</div>}

        {/* Input grid */}
        <div className="input-grid">
          {/* JD */}
          <div className="card">
            <div className="card-title">📋 Job Description</div>
            <div className="tab-group">
              <button className={`tab-btn ${jdTab === "paste" ? "active" : ""}`} onClick={() => setJdTab("paste")}>Paste Text</button>
              <button className={`tab-btn ${jdTab === "file" ? "active" : ""}`} onClick={() => setJdTab("file")}>Upload File</button>
            </div>
            {jdTab === "paste" ? (
              <textarea
                className="textarea"
                placeholder="Paste the full job description here — skills, qualifications, responsibilities..."
                value={jdText}
                onChange={e => setJdText(e.target.value)}
              />
            ) : (
              <div>
                <div className="dropzone" onClick={() => jdInputRef.current?.click()}>
                  <input ref={jdInputRef} type="file" accept=".txt,.pdf" onChange={e => setJdFile(e.target.files?.[0] ?? null)} />
                  <div className="dropzone-icon">📂</div>
                  <div className="dropzone-text">{jdFile ? jdFile.name : "Click to upload JD"}</div>
                  <div className="dropzone-sub">.txt or .pdf</div>
                </div>
              </div>
            )}
          </div>

          {/* Resumes */}
          <div className="card">
            <div className="card-title">📂 Upload Resumes</div>
            <div
              className={`dropzone ${dragging ? "active" : ""}`}
              onDragOver={onDragOver} onDragLeave={onDragLeave} onDrop={onDrop}
              onClick={() => resumeInputRef.current?.click()}
            >
              <input
                ref={resumeInputRef} type="file" accept=".pdf" multiple
                onChange={e => setResumes(prev => [...prev, ...Array.from(e.target.files ?? [])])}
              />
              <div className="dropzone-icon">📄</div>
              <div className="dropzone-text">Drag & drop PDFs here</div>
              <div className="dropzone-sub">or click to browse • multiple files supported</div>
            </div>
            {resumes.length > 0 && (
              <div className="file-chips">
                {resumes.map((f, i) => (
                  <div key={i} className="file-chip">
                    {f.name}
                    <button className="file-chip-remove" onClick={e => { e.stopPropagation(); setResumes(prev => prev.filter((_, j) => j !== i)); }}>×</button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Analyze button */}
        <div className="analyze-wrap">
          <button className={`analyze-btn ${loading ? "loading" : ""}`} disabled={!canAnalyze} onClick={analyze}>
            {loading ? <><div className="spinner" /> Analyzing...</> : <> 🔍 Analyze Resumes</>}
          </button>
        </div>

        {/* Results */}
        {result ? (
          <>
            <div className="results-header">
              <div className="results-title">🏆 Results</div>
              <span style={{ color: "var(--text-muted)", fontSize: "0.88rem" }}>{result.total_candidates} candidate{result.total_candidates !== 1 ? "s" : ""} ranked</span>
            </div>

            {/* JD skills warning */}
            {result.jd_skills.length === 0 && (
              <div className="warning-banner">⚠️ No skills detected in the job description. Skill Overlap score will be 0. Try including explicit skill names like Python, SQL, React.</div>
            )}

            {/* Parse errors */}
            {(result.errors ?? []).length > 0 && (
              <div className="error-banner">
                {result.errors!.map(e => <div key={e.filename}>⚠️ Skipped {e.filename}: {e.error}</div>)}
              </div>
            )}

            {/* JD skills cloud */}
            {result.jd_skills.length > 0 && (
              <div className="jd-skills-wrap">
                <div className="jd-skills-label">REQUIRED SKILLS FROM JD</div>
                <div className="skills-cloud">
                  {result.jd_skills.map(s => <span key={s} className="skill-tag skill-jd">{s}</span>)}
                </div>
              </div>
            )}

            {/* Metrics */}
            <div className="metrics-grid">
              {[
                { value: result.total_candidates, label: "Candidates" },
                { value: `${Math.max(...result.ranked.map(r => r.score.overall_match))}%`, label: "Top Match" },
                { value: `${(result.ranked.reduce((a, r) => a + r.score.overall_match, 0) / result.ranked.length).toFixed(1)}%`, label: "Avg Match" },
                { value: result.ranked.filter(r => r.score.overall_match >= 65).length, label: "Strong (65%+)" },
              ].map(({ value, label }) => (
                <div key={label} className="metric-card">
                  <div className="metric-value">{value}</div>
                  <div className="metric-label">{label}</div>
                </div>
              ))}
            </div>

            {/* Bar chart */}
            <div className="card chart-card">
              <div className="card-title">📊 Match Score Chart</div>
              <div className="bar-chart-wrap">
                {[...result.ranked].reverse().map(c => (
                  <div key={c.rank} className="bar-row">
                    <div className="bar-name">{c.name.slice(0, 18)}</div>
                    <div className="bar-track">
                      <div className={`bar-fill ${barClass(c.score.overall_match)}`} style={{ width: `${c.score.overall_match}%` }}>
                        <span className="bar-pct">{c.score.overall_match}%</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Leaderboard */}
            <div className="card leaderboard">
              <div className="card-title">🏅 Leaderboard</div>
              <table className="lb-table">
                <thead>
                  <tr>
                    <th>Rank</th><th>Candidate</th><th>Match</th><th>Label</th><th>Skills</th>
                  </tr>
                </thead>
                <tbody>
                  {result.ranked.map(c => (
                    <tr key={c.rank}>
                      <td><span className={`rank-badge ${rankBadgeClass(c.rank)}`}>{c.rank}</span></td>
                      <td><strong>{c.name}</strong></td>
                      <td><span className={`match-pill ${matchClass(c.score.overall_match)}`}>{c.score.overall_match}%</span></td>
                      <td><span className="label-badge">{c.score.label}</span></td>
                      <td style={{ color: "var(--text-muted)", fontSize: "0.82rem" }}>{c.score.matched_count} / {c.score.matched_count + c.score.missing_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Candidate cards */}
            <div className="candidates-section">
              <div className="card-title" style={{ marginBottom: 16, fontSize: "0.9rem" }}>🔎 Candidate Details</div>
              {result.ranked.map(c => (
                <CandidateCard key={c.rank} c={c} onDownloadPDF={downloadPDF} onDownloadCSV={downloadCSV} />
              ))}
            </div>

            {/* Bulk download */}
            <div className="bulk-dl">
              <button className="dl-btn" onClick={downloadAllCSV}>📊 Download All Results (CSV)</button>
            </div>
          </>
        ) : !loading && (
          <div className="empty-state">
            <div className="empty-icon">📄</div>
            <h3>Ready to analyze resumes</h3>
            <p>Enter a job description, upload resume PDFs, and click <strong>Analyze Resumes</strong> to get started.</p>
          </div>
        )}
      </main>

      {/* ── Footer ── */}
      <footer className="footer">
        Built with ❤️ by <a href="https://github.com/httpsankuu" target="_blank" rel="noopener noreferrer">Ankit Kumar Singh</a> &nbsp;|&nbsp; © 2026 Resume Analyzer AI
      </footer>
    </div>
  );
}
