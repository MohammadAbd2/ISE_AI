import { useEffect, useMemo, useState } from "react";
import { api, fetchJson } from "../lib/api";

const PHASE_LABELS = {
  9: "WebSocket streaming",
  10: "Background jobs",
  11: "Persistent workspaces",
  12: "Git controls",
  13: "Code intelligence",
  14: "Debugging",
  15: "DevTools",
  16: "Memory v2",
  17: "Collaboration",
  18: "Plugins",
  19: "Security",
  20: "Self-evolution",
};

function JsonPanel({ title, data }) {
  return (
    <details className="v4-details">
      <summary>{title}</summary>
      <pre>{JSON.stringify(data, null, 2)}</pre>
    </details>
  );
}

export default function AutonomousDevPlatformV4Panel() {
  const [roadmap, setRoadmap] = useState(null);
  const [status, setStatus] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [workspaces, setWorkspaces] = useState([]);
  const [devtools, setDevtools] = useState(null);
  const [security, setSecurity] = useState(null);
  const [task, setTask] = useState("Scan this project, explain risk, and prepare a safe implementation job");
  const [command, setCommand] = useState("pwd && ls");
  const [path, setPath] = useState("");
  const [errorText, setErrorText] = useState("Error: listen EADDRINUSE: address already in use 5173");
  const [debug, setDebug] = useState(null);
  const [commandResult, setCommandResult] = useState(null);
  const [stream, setStream] = useState([]);
  const [message, setMessage] = useState("");

  async function refresh() {
    const [nextRoadmap, nextStatus, nextJobs, nextWorkspaces, nextDevtools, nextSecurity] = await Promise.all([
      fetchJson(api.platformV4Roadmap),
      fetchJson(api.platformV4Status),
      fetchJson(api.platformV4Jobs),
      fetchJson(api.platformV4Workspaces),
      fetchJson(api.platformV4Devtools),
      fetchJson(api.platformV4Security),
    ]);
    setRoadmap(nextRoadmap);
    setStatus(nextStatus);
    setJobs(nextJobs.jobs || []);
    setWorkspaces(nextWorkspaces.workspaces || []);
    setDevtools(nextDevtools);
    setSecurity(nextSecurity);
  }

  useEffect(() => {
    refresh().catch((err) => setMessage(err.message || String(err)));
  }, []);

  async function createJob() {
    const job = await fetchJson(api.platformV4Jobs, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task }),
    });
    setJobs((current) => [job, ...current]);
    openJobStream(job.id);
  }

  function openJobStream(jobId) {
    if (!jobId || typeof window === "undefined") return;
    const root = window.location.origin.replace(/^http/, "ws");
    const ws = new WebSocket(`${root}/api/platform-v4/ws/${encodeURIComponent(jobId)}`);
    ws.onmessage = (event) => {
      try {
        setStream((current) => [...current.slice(-40), JSON.parse(event.data)]);
      } catch {
        setStream((current) => [...current.slice(-40), { type: "raw", data: event.data }]);
      }
    };
    ws.onerror = () => setStream((current) => [...current.slice(-40), { type: "error", data: "WebSocket failed. REST fallback is still available." }]);
  }

  async function runCommand() {
    const result = await fetchJson(api.platformV4TerminalRun, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ command, cwd: path || null, timeout: 30 }),
    });
    setCommandResult(result);
    await refresh();
  }

  async function rememberWorkspace() {
    const workspace = await fetchJson(api.platformV4Workspaces, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ label: path.split("/").filter(Boolean).at(-1) || "workspace", path }),
    });
    setWorkspaces((current) => [workspace, ...current.filter((item) => item.id !== workspace.id)]);
  }

  async function explainError() {
    const result = await fetchJson(api.platformV4DebugExplain, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ error_text: errorText, context: "Developer pasted terminal or app logs into the Agent console." }),
    });
    setDebug(result);
  }

  async function proposeSelfEvolution() {
    const result = await fetchJson(api.platformV4SelfEvolution, { method: "POST" });
    setMessage(`Self-evolution proposal created: ${result.title}`);
    await refresh();
  }

  const completedCount = useMemo(() => roadmap?.phases?.length || 12, [roadmap]);

  return (
    <div className="platform-v4-shell">
      <header className="platform-v4-hero">
        <div>
          <p className="eyebrow">Autonomous Dev Platform v4</p>
          <h2>Phases 9–20 implementation console</h2>
          <p>Streaming, jobs, persistent workspaces, Git, code intelligence, debugging, DevTools, memory v2, collaboration, plugins, security, and self-evolution v3.</p>
        </div>
        <div className="v4-score"><strong>{completedCount}/12</strong><span>foundations online</span></div>
      </header>

      {message ? <div className="render-card-summary success">{message}</div> : null}

      <section className="v4-grid">
        {(roadmap?.phases || Object.entries(PHASE_LABELS).map(([phase, name]) => ({ phase, name, status: "implemented_foundation" }))).map((phase) => (
          <article key={phase.id || phase.phase} className="v4-phase-card">
            <span>P{phase.phase || String(phase.id).replace("P", "")}</span>
            <strong>{phase.name}</strong>
            <small>{phase.status}</small>
          </article>
        ))}
      </section>

      <section className="v4-two-col">
        <article className="panel v4-panel">
          <h3>Real-time jobs + WebSocket stream</h3>
          <textarea value={task} onChange={(e) => setTask(e.target.value)} rows={3} />
          <div className="response-feedback-bar embedded">
            <button className="response-feedback-chip primary" onClick={createJob}>Create job + stream</button>
            <button className="response-feedback-chip" onClick={refresh}>Refresh</button>
          </div>
          <div className="v4-stream">
            {stream.map((item, index) => <code key={`${item.type}-${index}`}>{item.type}: {item.step || item.data || item.progress || "event"}</code>)}
          </div>
          <JsonPanel title="Recent jobs" data={jobs.slice(0, 5)} />
        </article>

        <article className="panel v4-panel">
          <h3>Interactive terminal with policy guard</h3>
          <input value={path} onChange={(e) => setPath(e.target.value)} placeholder="Workspace path (optional)" />
          <textarea value={command} onChange={(e) => setCommand(e.target.value)} rows={3} />
          <div className="response-feedback-bar embedded">
            <button className="response-feedback-chip primary" onClick={runCommand}>Run command</button>
            <button className="response-feedback-chip" onClick={rememberWorkspace} disabled={!path.trim()}>Remember workspace</button>
          </div>
          {commandResult ? <JsonPanel title="Command proof" data={commandResult} /> : null}
        </article>
      </section>

      <section className="v4-two-col">
        <article className="panel v4-panel">
          <h3>Smart error explainer</h3>
          <textarea value={errorText} onChange={(e) => setErrorText(e.target.value)} rows={4} />
          <button className="response-feedback-chip primary" onClick={explainError}>Explain + propose fix loop</button>
          {debug ? <JsonPanel title="Root cause analysis" data={debug} /> : null}
        </article>
        <article className="panel v4-panel">
          <h3>Self-evolution v3</h3>
          <p>Proposal-first upgrades based on failed jobs and repeated bugs. Human approval is required before merge.</p>
          <button className="response-feedback-chip primary" onClick={proposeSelfEvolution}>Create upgrade proposal</button>
          <JsonPanel title="Security report" data={security || {}} />
        </article>
      </section>

      <section className="v4-two-col">
        <JsonPanel title="Persistent workspaces" data={workspaces} />
        <JsonPanel title="DevTools snapshot" data={devtools || {}} />
      </section>
      <JsonPanel title="Platform status" data={status || {}} />
    </div>
  );
}
