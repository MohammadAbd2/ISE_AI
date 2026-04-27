import { useEffect, useMemo, useState } from "react";
import { api, fetchJson } from "../lib/api";
import "../styles/agi-v3.css";

const sampleError = `Failed to resolve import "./components/GlobalErrorBoundary" from "src/main.jsx"`;

function Metric({ label, value }) {
  return <div className="agi-v3-metric"><span>{label}</span><strong>{value}</strong></div>;
}

export default function AGISystemV3Panel() {
  const [roadmap, setRoadmap] = useState(null);
  const [decision, setDecision] = useState(null);
  const [debug, setDebug] = useState(null);
  const [evaluation, setEvaluation] = useState(null);
  const [control, setControl] = useState(null);
  const [riskText, setRiskText] = useState("deploy to production");
  const [risk, setRisk] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let mounted = true;
    async function load() {
      try {
        const [nextRoadmap, nextDecision, nextDebug, nextEvaluation, nextControl] = await Promise.all([
          fetchJson(api.agiV3Roadmap),
          fetchJson(api.agiV3Reason, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              task: "Rewrite frontend and backend agent flow with real reasoning, verification, and simplified UI",
              context: { stack: ["React", "Vite", "FastAPI"] },
            }),
          }),
          fetchJson(api.agiV3Debug, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ error: sampleError }),
          }),
          fetchJson(api.agiV3Evaluate, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              files: ["backend/app/services/agi_system_v3.py", "frontend/src/components/AGISystemV3Panel.jsx"],
              verification: ["import graph validated", "build gate documented", "risk policy active"],
              risk: "medium",
            }),
          }),
          fetchJson(api.agiV3Control),
        ]);
        if (!mounted) return;
        setRoadmap(nextRoadmap);
        setDecision(nextDecision);
        setDebug(nextDebug);
        setEvaluation(nextEvaluation);
        setControl(nextControl);
      } catch (err) {
        if (mounted) setError(err.message || "AGI v3 backend unavailable");
      }
    }
    load();
    return () => { mounted = false; };
  }, []);

  async function assessRisk() {
    const nextRisk = await fetchJson(api.agiV3Risk, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: riskText, policy: { autonomy_mode: "assisted" } }),
    });
    setRisk(nextRisk);
  }

  const phases = roadmap?.phases || [];
  const score = evaluation?.scores?.overall ?? "—";
  const winner = decision?.decision?.winner;
  const graph = control?.graph || {};
  const integrations = control?.integrations || {};
  const enabledIntegrations = useMemo(() => Object.entries(integrations).filter(([, value]) => value.enabled).length, [integrations]);

  return (
    <section className="agi-v3-shell">
      <div className="agi-v3-hero">
        <div>
          <p className="eyebrow">AGI System v3 · Phases K-U</p>
          <h2>Reason deeper. Verify harder. Show less.</h2>
          <p>This panel connects the frontend to backend contracts for reasoning, multi-strategy execution, evaluation, graph memory, debugging, compression, integrations, safety, autonomy, and simplified UI.</p>
        </div>
        <div className="agi-v3-score-card"><span>Evaluation</span><strong>{score}</strong><small>{evaluation?.pass ? "Pass" : "Needs gates"}</small></div>
      </div>

      {error ? <div className="agi-v3-alert">{error}</div> : null}

      <div className="agi-v3-metrics">
        <Metric label="Implemented phases" value={phases.length || "—"} />
        <Metric label="Reasoning confidence" value={decision?.decision?.confidence ? `${decision.decision.confidence}%` : "—"} />
        <Metric label="Graph nodes" value={graph.node_count ?? "—"} />
        <Metric label="Enabled integrations" value={enabledIntegrations} />
      </div>

      <div className="agi-v3-grid">
        <article className="agi-v3-card wide">
          <header><span>K + L</span><strong>Tree reasoning and multi-strategy execution</strong></header>
          <h3>{winner?.title || "Loading decision…"}</h3>
          <p>{winner?.approach || "The backend generates competing plans, scores them, and chooses a verified path."}</p>
          <div className="agi-v3-pills">{(winner?.strengths || []).map((item) => <span key={item}>{item}</span>)}</div>
        </article>

        <article className="agi-v3-card">
          <header><span>P</span><strong>Debugging intelligence</strong></header>
          <h3>{debug?.class || "—"}</h3>
          <p>{debug?.root_cause || "Classifies root causes instead of writing unrelated files."}</p>
          <ol>{(debug?.repair_plan || []).slice(0, 4).map((step) => <li key={step}>{step}</li>)}</ol>
        </article>

        <article className="agi-v3-card">
          <header><span>S + T</span><strong>Safety and autonomy</strong></header>
          <label className="agi-v3-risk-input">Action to assess<input value={riskText} onChange={(event) => setRiskText(event.target.value)} /></label>
          <button type="button" onClick={assessRisk}>Assess risk</button>
          {risk ? <p className={`agi-v3-risk ${risk.risk}`}>{risk.risk} risk · {risk.requires_approval ? "approval required" : "allowed"}</p> : <p>Admin policy gates high-risk actions before autonomous execution.</p>}
        </article>
      </div>

      <div className="agi-v3-phase-list">
        {phases.map((phase) => (
          <article key={phase.id}>
            <span>{phase.id}</span>
            <div><strong>{phase.title}</strong><p>{phase.goal}</p></div>
            <small>{phase.status}</small>
          </article>
        ))}
      </div>
    </section>
  );
}
