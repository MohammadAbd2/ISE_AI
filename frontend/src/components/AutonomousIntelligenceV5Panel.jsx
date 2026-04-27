import { useEffect, useState } from "react";
import { api, fetchJson } from "../lib/api";

function PhasePill({ phase }) {
  return <article className="v5-phase-pill"><strong>{phase.id}</strong><span>{phase.name}</span><em>{phase.status}</em></article>;
}

function WorkbenchPreview({ result }) {
  if (!result) return null;
  const events = result.events || [];
  const files = result.files || [];
  const truth = result.truth || {};
  return <section className="v5-workbench-result">
    <div className="v5-result-hero">
      <div><p className="eyebrow">AI Engineer Workbench</p><h3>{result.status}</h3><p>{result.summary}</p></div>
      <div className="v5-truth-score"><strong>{truth.score || 0}</strong><span>truth score</span></div>
    </div>
    <div className="v5-lanes">
      {["PlannerAgent","ReasoningEngine","MultiAgentBrain","DesigningAgent","CodingAgent","VerifierAgent","PreviewAgent","TruthLayer"].map((agent) => {
        const agentEvents = events.filter((event) => event.agent === agent);
        return <article key={agent} className="v5-lane"><strong>{agent}</strong>{agentEvents.length ? agentEvents.map((event, index) => <p key={index}>{event.detail}</p>) : <p>Standing by</p>}</article>;
      })}
    </div>
    <div className="v5-file-strip">{files.slice(0, 10).map((file) => <span key={file.path}>{file.path}</span>)}</div>
  </section>;
}

export default function AutonomousIntelligenceV5Panel() {
  const [roadmap, setRoadmap] = useState(null);
  const [task, setTask] = useState("Build a modern SaaS dashboard with animated cards and live preview evidence");
  const [url, setUrl] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => { fetchJson(api.autonomousV5Roadmap).then(setRoadmap).catch(() => null); }, []);

  async function run() {
    setLoading(true); setError("");
    try {
      const data = await fetchJson(api.autonomousV5Run, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ task, url: url || null }) });
      setResult(data);
    } catch (err) { setError(err.message || String(err)); }
    finally { setLoading(false); }
  }

  return <section className="panel v5-panel">
    <div className="v5-panel-hero">
      <div><p className="eyebrow">v21-v30</p><h2>Autonomous Intelligence</h2><p>Truth layer, multi-agent collaboration, browser/design intelligence, and a chat UI that feels like watching an AI engineer work.</p></div>
      <button type="button" className="primary-button" onClick={run} disabled={loading}>{loading ? "Engineering…" : "Run v5 Agent"}</button>
    </div>
    {roadmap ? <div className="v5-phase-grid">{roadmap.phases.map((phase) => <PhasePill key={phase.id} phase={phase} />)}</div> : null}
    <div className="v5-run-form">
      <label>Task<textarea value={task} onChange={(event) => setTask(event.target.value)} rows={4} /></label>
      <label>Website/Figma URL optional<input value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://example.com" /></label>
    </div>
    {error ? <div className="render-card-summary warning">{error}</div> : null}
    <WorkbenchPreview result={result} />
  </section>;
}
