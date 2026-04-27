import { useEffect, useMemo, useState } from "react";
import { api, fetchJson } from "../lib/api";
import "../styles/daily-programming-agi.css";

const DEFAULT_REQUEST = "create a full stack application for a webshop that sell phones. Create the roadmap first, then implement it in a sandbox, verify it, create preview instructions, and give me the zip file.";

function Badge({ children, tone = "neutral" }) {
  return <span className={`dp-badge dp-badge--${tone}`}>{children}</span>;
}

function statusTone(status) {
  if (status === "completed") return "success";
  if (status === "failed" || status === "blocked") return "danger";
  if (status === "running") return "warn";
  return "neutral";
}

function StepCard({ step }) {
  return (
    <article className={`dp-step dp-step--${step.status}`}>
      <div className="dp-step__top">
        <div>
          <strong>{step.title}</strong>
          <span>{step.agent}</span>
        </div>
        <Badge tone={statusTone(step.status)}>{step.status}</Badge>
      </div>
      {step.command ? <code>{step.command}</code> : null}
      {step.error ? <p className="dp-error-text">{step.error}</p> : null}
      {step.evidence?.length ? (
        <div className="dp-evidence-row">
          {step.evidence.map((item) => <span key={item}>{item}</span>)}
        </div>
      ) : null}
      {step.files?.length ? <small>{step.files.length} file(s): {step.files.slice(0, 4).join(", ")}</small> : null}
    </article>
  );
}

function EventList({ events = [] }) {
  if (!events.length) return <p className="dp-muted">No execution events yet.</p>;
  return (
    <div className="dp-event-list">
      {events.slice().reverse().slice(0, 12).map((event, index) => (
        <div key={`${event.time}-${index}`} className="dp-event-line">
          <Badge tone={statusTone(event.status)}>{event.status}</Badge>
          <strong>{event.agent}</strong>
          <span>{event.message}</span>
        </div>
      ))}
    </div>
  );
}

function ValidationPanel({ validation }) {
  if (!validation || !Object.keys(validation).length) return null;
  const checks = validation.checks || {};
  return (
    <article className="dp-panel dp-validation">
      <div className="dp-panel-heading">
        <div>
          <p className="dp-eyebrow">Verification</p>
          <h3>{validation.passed ? "Export gates passed" : "Export gates need repair"}</h3>
        </div>
        <div className={`dp-score ${validation.passed ? "pass" : "fail"}`}>{validation.score ?? 0}/100</div>
      </div>
      <div className="dp-check-grid">
        {Object.entries(checks).map(([key, ok]) => (
          <div key={key} className={`dp-check ${ok ? "pass" : "fail"}`}>
            <span>{ok ? "✓" : "!"}</span>
            <strong>{key.replaceAll("_", " ")}</strong>
          </div>
        ))}
      </div>
      {validation.failed?.length ? <p className="dp-error-text">Failed: {validation.failed.join(", ")}</p> : null}
    </article>
  );
}

export default function DailyProgrammingAGIPanel() {
  const [request, setRequest] = useState(DEFAULT_REQUEST);
  const [sourcePath, setSourcePath] = useState("");
  const [rememberLabel, setRememberLabel] = useState("default");
  const [rememberPath, setRememberPath] = useState("");
  const [roadmap, setRoadmap] = useState(null);
  const [paths, setPaths] = useState({});
  const [plan, setPlan] = useState(null);
  const [run, setRun] = useState(null);
  const [mergePath, setMergePath] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [memoryCleanup, setMemoryCleanup] = useState(null);

  async function loadInitial() {
    try {
      const [roadmapData, pathData] = await Promise.all([
        fetchJson(api.programmingAgiRoadmap),
        fetchJson(api.programmingAgiPaths).catch(() => ({})),
      ]);
      setRoadmap(roadmapData);
      setPaths(pathData);
    } catch (err) {
      setError(err.message || "Could not load Programming Agent roadmap.");
    }
  }

  async function rememberProjectPath() {
    setBusy(true);
    setError("");
    try {
      const data = await fetchJson(api.programmingAgiRememberPath, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ label: rememberLabel, path: rememberPath }),
      });
      setPaths(data.memory || {});
    } catch (err) {
      setError(err.message || "Could not remember path.");
    } finally {
      setBusy(false);
    }
  }

  async function createPlan() {
    setBusy(true);
    setError("");
    try {
      const data = await fetchJson(api.programmingAgiPlan, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ request, source_path: sourcePath || null }),
      });
      setPlan(data);
    } catch (err) {
      setError(err.message || "Planning failed.");
    } finally {
      setBusy(false);
    }
  }

  async function runAgent() {
    setBusy(true);
    setError("");
    try {
      const data = await fetchJson(api.programmingAgiRun, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ request, source_path: sourcePath || null, export_zip: true }),
      });
      setRun(data);
      setPlan({ contract: data.validation?.contract || data.events?.[0]?.data, steps: data.steps, roadmap: data.roadmap, source_path: data.source_path });
    } catch (err) {
      setError(err.message || "Agent run failed.");
    } finally {
      setBusy(false);
    }
  }

  async function clearStaleMemory() {
    setBusy(true);
    setError("");
    try {
      const data = await fetchJson(api.programmingAgiClearMemory, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ include_path_memory: false }),
      });
      setMemoryCleanup(data);
    } catch (err) {
      setError(err.message || "Memory cleanup failed.");
    } finally {
      setBusy(false);
    }
  }

  async function mergeRun() {
    if (!run?.run_id || !mergePath) return;
    setBusy(true);
    setError("");
    try {
      const data = await fetchJson(api.programmingAgiMerge, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ run_id: run.run_id, target_path: mergePath }),
      });
      setRun((current) => ({ ...current, merge: data }));
    } catch (err) {
      setError(err.message || "Merge failed.");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    loadInitial();
  }, []);

  const contract = plan?.contract || run?.validation?.contract || {};
  const phases = roadmap?.phases || [];
  const completed = useMemo(() => (run?.steps || []).filter((step) => step.status === "completed").length, [run]);

  return (
    <section className="daily-agi-shell" aria-label="Daily Programming Agent workspace">
      <div className="dp-hero">
        <div>
          <Badge tone="success">Dynamic Programming Agent</Badge>
          <h2>No templates. No fake completion. Real sandbox workflow.</h2>
          <p>
            This workspace routes every task through planning, sandbox ingestion, implementation, terminal verification,
            repair, preview, export, and optional merge. Full-stack requests must produce full-stack artifacts.
          </p>
        </div>
        <div className="dp-hero-stats">
          <strong>{run ? `${run.progress}%` : "0%"}</strong>
          <span>{run ? `${completed}/${run.steps?.length || 0} steps complete` : "ready"}</span>
        </div>
      </div>

      <div className="dp-command-grid">
        <article className="dp-panel wide">
          <label htmlFor="programming-agi-request">Programming task</label>
          <textarea id="programming-agi-request" value={request} onChange={(event) => setRequest(event.target.value)} />
          <label htmlFor="programming-agi-source">Optional source project path</label>
          <input id="programming-agi-source" placeholder="Current folder, e.g. ~/Desktop/Easv/" value={sourcePath} onChange={(event) => setSourcePath(event.target.value)} />
          <div className="dp-actions">
            <button onClick={createPlan} disabled={busy}>Create roadmap</button>
            <button className="primary" onClick={runAgent} disabled={busy}>{busy ? "Running agents…" : "Run in sandbox"}</button>
          </div>
        </article>
        <article className="dp-panel">
          <h3>Remember project path</h3>
          <input value={rememberLabel} onChange={(event) => setRememberLabel(event.target.value)} placeholder="default" />
          <input value={rememberPath} onChange={(event) => setRememberPath(event.target.value)} placeholder="Current folder, e.g. ~/Desktop/Easv/" />
          <button onClick={rememberProjectPath} disabled={busy || !rememberPath}>Remember path</button>
          <button onClick={clearStaleMemory} disabled={busy}>Clear stale memory/vector files</button>
          {memoryCleanup ? <small>{memoryCleanup.count} stale file(s) removed; path memory preserved.</small> : null}
          <div className="dp-path-list">
            {Object.entries(paths || {}).map(([label, item]) => (
              <button key={label} onClick={() => setSourcePath(item.path)}>
                <strong>{label}</strong><span>{item.path}</span>
              </button>
            ))}
          </div>
        </article>
      </div>

      {error ? <div className="dp-error">{error}</div> : null}

      <div className="dp-outcome-grid">
        <article className="dp-panel">
          <p className="dp-eyebrow">Contract</p>
          <h3>{contract.intent || "Waiting for plan"}</h3>
          <div className="dp-chip-row">
            {(contract.stacks || []).map((item) => <Badge key={item}>{item}</Badge>)}
            {contract.domain ? <Badge tone="success">{contract.domain}</Badge> : null}
          </div>
          <p>{contract.required_files?.length ? `${contract.required_files.length} required files derived from task.` : "Create a roadmap to see required files."}</p>
        </article>
        <article className="dp-panel">
          <p className="dp-eyebrow">Preview</p>
          <h3>{run?.preview?.available ? "Preview available" : "Preview pending"}</h3>
          {run?.preview?.command ? <code>{run.preview.command}</code> : <p className="dp-muted">Run the sandbox to generate preview instructions.</p>}
          {run?.preview?.url ? <a href={run.preview.url} target="_blank" rel="noreferrer">Open preview target</a> : null}
        </article>
        <article className="dp-panel">
          <p className="dp-eyebrow">Export</p>
          <h3>{run?.export?.filename || "No ZIP yet"}</h3>
          {run?.export?.path ? <code>{run.export.path}</code> : <p className="dp-muted">ZIP is created only after validation passes.</p>}
          {run?.export?.file_count ? <Badge tone="success">{run.export.file_count} files</Badge> : null}
        </article>
      </div>

      <ValidationPanel validation={run?.validation} />

      <div className="dp-main-grid">
        <article className="dp-panel wide">
          <div className="dp-panel-heading">
            <div>
              <p className="dp-eyebrow">Execution plan</p>
              <h3>Stateful agent workflow</h3>
            </div>
            <Badge>{run?.status || "not started"}</Badge>
          </div>
          <div className="dp-step-list">
            {(run?.steps || plan?.steps || []).map((step) => <StepCard key={step.id} step={step} />)}
          </div>
        </article>
        <article className="dp-panel">
          <div className="dp-panel-heading">
            <div>
              <p className="dp-eyebrow">Events</p>
              <h3>Real agent evidence</h3>
            </div>
          </div>
          <EventList events={run?.events || []} />
        </article>
      </div>

      {run?.run_id ? (
        <article className="dp-panel dp-merge-panel">
          <div>
            <p className="dp-eyebrow">Merge after review</p>
            <h3>Copy sandbox result to another folder</h3>
            <p>Example: ~/Desktop/Easv/programming/new_ise_ai</p>
          </div>
          <input value={mergePath} onChange={(event) => setMergePath(event.target.value)} placeholder="~/Desktop/Easv/programming/new_ise_ai" />
          <button onClick={mergeRun} disabled={busy || !mergePath}>Merge run</button>
          {run.merge ? <Badge tone="success">Merged {run.merge.copied_files?.length || 0} files</Badge> : null}
        </article>
      ) : null}

      <article className="dp-panel">
        <p className="dp-eyebrow">Roadmap</p>
        <h3>{roadmap?.title || "Customer-grade roadmap"}</h3>
        <div className="dp-roadmap-grid">
          {phases.map((phase) => (
            <div key={phase.id}>
              <Badge>{phase.id}</Badge>
              <strong>{phase.name}</strong>
              <p>{phase.goal}</p>
            </div>
          ))}
        </div>
      </article>
    </section>
  );
}
