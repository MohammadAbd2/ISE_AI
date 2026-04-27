import { useEffect, useMemo, useState } from "react";
import { api, fetchJson } from "../lib/api";
import "../styles/agi-v4.css";

const DEFAULT_TASK = "Build a grounded, verified, outcome-first autonomous engineering workflow.";

function Badge({ children, tone = "neutral" }) {
  return <span className={`v4-badge v4-badge--${tone}`}>{children}</span>;
}

function Metric({ label, value, detail }) {
  return (
    <div className="v4-metric">
      <span>{label}</span>
      <strong>{value}</strong>
      {detail ? <small>{detail}</small> : null}
    </div>
  );
}

export default function AGISystemV4Panel() {
  const [task, setTask] = useState(DEFAULT_TASK);
  const [roadmap, setRoadmap] = useState(null);
  const [result, setResult] = useState(null);
  const [mode, setMode] = useState("Developer");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function loadRoadmap() {
    try {
      setRoadmap(await fetchJson(api.agiV4Roadmap));
    } catch (err) {
      setError(err.message || "Could not load AGI v4 roadmap.");
    }
  }

  async function run() {
    setBusy(true);
    setError("");
    try {
      const data = await fetchJson(api.agiV4Run, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task, context: { files: ["frontend/src/App.jsx", "backend/app/main.py"], ui_mode: mode } }),
      });
      setResult(data);
    } catch (err) {
      setError(err.message || "AGI v4 run failed.");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    loadRoadmap();
    run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const phases = roadmap?.phases || [];
  const card = result?.ui_card || {};
  const trust = card.trust || {};
  const selectedSkills = result?.skills?.selected || [];
  const trace = result?.trace || {};
  const evaluation = result?.evaluation || {};
  const certification = result?.certification || {};

  const visibleDetails = useMemo(() => {
    if (mode === "Beginner") return phases.slice(0, 4);
    if (mode === "Developer") return phases.slice(0, 8);
    return phases;
  }, [mode, phases]);

  return (
    <section className="agi-v4-panel" aria-label="AGI System v4 truth and reliability panel">
      <div className="v4-hero">
        <div>
          <Badge tone="success">AGI System v4</Badge>
          <h2>Truth, reliability, and real-world impact</h2>
          <p>
            Outcome-first control plane for grounded claims, replayable traces, continuous evaluation,
            domain skills, adaptive execution, trust certification, and autonomous project ownership.
          </p>
        </div>
        <div className="v4-mode-switcher" role="group" aria-label="UI complexity mode">
          {["Beginner", "Developer", "Admin"].map((item) => (
            <button key={item} className={mode === item ? "active" : ""} onClick={() => setMode(item)}>{item}</button>
          ))}
        </div>
      </div>

      <div className="v4-command-card">
        <label htmlFor="agi-v4-task">Outcome to verify</label>
        <textarea id="agi-v4-task" value={task} onChange={(event) => setTask(event.target.value)} />
        <button onClick={run} disabled={busy}>{busy ? "Certifying…" : "Run v4 certification"}</button>
      </div>

      {error ? <div className="v4-error">{error}</div> : null}

      <div className="v4-outcome-grid">
        <article className="v4-outcome-card primary">
          <div className="v4-card-heading">
            <Badge tone={trust.risk === "low" ? "success" : trust.risk === "high" ? "danger" : "warn"}>{trust.risk || "medium"} risk</Badge>
            <span>{certification.safe_to_export ? "Safe to export" : "Needs review"}</span>
          </div>
          <h3>{card.outcome || "Waiting for certified outcome…"}</h3>
          <div className="v4-proof-list">{(card.proof || []).map((item) => <span key={item}>{item}</span>)}</div>
        </article>
        <Metric label="Confidence" value={`${trust.confidence ?? 0}%`} detail="evidence + trace + evaluation" />
        <Metric label="Evaluation" value={evaluation.overall ?? "—"} detail={evaluation.passed ? "passed" : "review required"} />
        <Metric label="Trace" value={trace.event_count ?? 0} detail={trace.trace_checksum || "not generated"} />
      </div>

      <div className="v4-sections">
        <article className="v4-section">
          <h3>Specialist skill packs</h3>
          <div className="v4-chip-row">{selectedSkills.map((skill) => <Badge key={skill}>{skill}</Badge>)}</div>
        </article>
        <article className="v4-section">
          <h3>Roadmap implemented</h3>
          <div className="v4-phase-list">
            {visibleDetails.map((phase) => (
              <div className="v4-phase" key={phase.id}>
                <strong>{phase.id}</strong>
                <span>{phase.title}</span>
                <Badge tone="success">{phase.status}</Badge>
              </div>
            ))}
          </div>
        </article>
        {mode === "Admin" ? (
          <article className="v4-section wide">
            <h3>Admin proof and governance</h3>
            <pre>{JSON.stringify({ certification, trace, evidence: result?.evidence, owner: result?.owner }, null, 2)}</pre>
          </article>
        ) : null}
      </div>
    </section>
  );
}
