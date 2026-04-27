import { useState } from "react";
import "../styles/maximum-dynamic-agent.css";
import AgentFileTree from "./AgentFileTree";
import AgentToolRoutes from "./AgentToolRoutes";
import { downloadTextFile, getFileMeta } from "../lib/fileVisuals";

const DEFAULT_PROMPT = "create a website application using React, Node and SQLite; create the roadmap first, implement it in sandbox, self-repair errors, then prepare a ZIP only after verification passes";

async function postJson(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

function statusLabel(status) {
  if (status === "done") return "Done";
  if (status === "running") return "Running";
  if (status === "failed") return "Failed";
  if (status === "blocked") return "Blocked";
  if (status === "repairing") return "Repairing";
  return "Pending";
}

export default function MaximumDynamicAgentPanel() {
  const [request, setRequest] = useState(DEFAULT_PROMPT);
  const [projectPath, setProjectPath] = useState("");
  const [maxRepairs, setMaxRepairs] = useState(5);
  const [exportRequested, setExportRequested] = useState(true);
  const [run, setRun] = useState(null);
  const [roadmap, setRoadmap] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [activeFile, setActiveFile] = useState("");

  async function loadRoadmap() {
    setError("");
    setIsLoading(true);
    try {
      const response = await fetch("/api/maximum-dynamic-agent/roadmap");
      if (!response.ok) throw new Error(await response.text());
      setRoadmap(await response.json());
    } catch (err) {
      setError(err.message || "Roadmap failed");
    } finally {
      setIsLoading(false);
    }
  }

  async function runAgent() {
    setError("");
    setIsLoading(true);
    try {
      const payload = {
        request,
        project_path: projectPath.trim() || null,
        export_requested: exportRequested,
        max_repairs: Number(maxRepairs) || 5,
      };
      setRun(await postJson("/api/maximum-dynamic-agent/run", payload));
    } catch (err) {
      setError(err.message || "Run failed");
    } finally {
      setIsLoading(false);
    }
  }

  const progress = run?.events?.at?.(-1)?.progress ?? 0;
  const failed = run?.validation?.failed || [];
  const files = run?.files || [];
  const preview = run?.preview;
  const fileContents = run?.file_contents || {};
  const currentFolder = run?.working_directory?.current || run?.workspace_resolution?.expanded || projectPath || "No folder selected";
  const workspaceWarnings = run?.workspace_resolution?.warnings || [];
  const activeFileMeta = getFileMeta(activeFile);

  return (
    <section className="maximum-agent-shell">
      <header className="maximum-agent-hero">
        <div>
          <p className="maximum-agent-kicker">Maximum Dynamic Programming Agent</p>
          <h2>Codex-style dynamic execution: plan, implement, verify, repair, preview, then export.</h2>
          <p>
            This panel routes work through a live task contract, stack-specific sub-agents, verifier gates, and a terminal-style repair loop. If a bug appears, the DebugAgent patches the failing layer and reruns verification before moving forward.
          </p>
        </div>
        <div className="maximum-agent-score">
          <span>Dynamic score</span>
          <strong>{run?.validation?.score ?? "—"}</strong>
        </div>
      </header>

      <div className="maximum-agent-controls">
        <label>
          Task prompt
          <textarea value={request} onChange={(event) => setRequest(event.target.value)} rows={5} />
        </label>
        <div className="maximum-agent-control-grid">
          <label>
            Optional project path
            <input value={projectPath} onChange={(event) => setProjectPath(event.target.value)} placeholder="Current project folder, or say: you are now in ~/Desktop/Easv/" />
          </label>
          <label>
            Repair budget
            <input value={maxRepairs} onChange={(event) => setMaxRepairs(event.target.value)} type="number" min="0" max="20" />
          </label>
          <label className="maximum-agent-check">
            <input checked={exportRequested} onChange={(event) => setExportRequested(event.target.checked)} type="checkbox" />
            ZIP only after all verification gates pass
          </label>
        </div>
        <div className="maximum-agent-actions">
          <button type="button" onClick={runAgent} disabled={isLoading}>Run dynamic agent</button>
          <button type="button" onClick={loadRoadmap} disabled={isLoading}>Show roadmap</button>
        </div>
        {error ? <strong className="maximum-agent-error">{error}</strong> : null}
      </div>

      {roadmap ? (
        <article className="maximum-agent-card">
          <h3>{roadmap.title}</h3>
          <div className="maximum-agent-roadmap">
            {roadmap.phases?.map((phase) => (
              <div key={phase.id}>
                <strong>{phase.id} · {phase.name}</strong>
                <p>{phase.goal}</p>
              </div>
            ))}
          </div>
        </article>
      ) : null}

      {run ? (
        <article className="maximum-agent-result">
          <div className="maximum-agent-result-head">
            <div>
              <p className="maximum-agent-kicker">Outcome</p>
              <h3>{run.summary}</h3>
              <p className="maximum-agent-working-dir">Current folder: <code>{currentFolder}</code></p>
              {workspaceWarnings.length ? <p className="maximum-agent-warning">{workspaceWarnings.join(" ")}</p> : null}
            </div>
            <div className={`maximum-agent-trust ${run.export_allowed ? "ready" : "blocked"}`}>
              {run.export_allowed ? "Export allowed" : "Export blocked"}
            </div>
          </div>

          <div className="maximum-agent-progress" aria-label={`Progress ${progress}%`}>
            <span style={{ width: `${progress}%` }} />
          </div>

          {failed.length ? (
            <div className="maximum-agent-blocker">
              <strong>Current blockers</strong>
              <p>{failed.join(" · ")}</p>
            </div>
          ) : (
            <div className="maximum-agent-success">All verification gates passed.</div>
          )}

          {preview ? (
            <div className={`maximum-agent-preview ${preview.available ? "ready" : "blocked"}`}>
              <div>
                <strong>{preview.available ? "Browser preview ready" : "Preview not available yet"}</strong>
                <p>{preview.message}</p>
                {preview.command ? <code>{preview.cwd ? `${preview.cwd}: ` : ""}{preview.command}</code> : null}
              </div>
              {preview.available && preview.url ? <a href={preview.url} target="_blank" rel="noreferrer">Open preview</a> : null}
            </div>
          ) : null}

          {run.capabilities?.length ? (
            <div className="maximum-agent-capability-grid">
              {run.capabilities.map((capability) => (
                <div className="maximum-agent-capability" key={`${capability.name}-${capability.trigger}`}>
                  <strong>{capability.name}</strong>
                  <span>{capability.status} · {capability.trigger}</span>
                </div>
              ))}
            </div>
          ) : null}

          <div className="maximum-agent-steps">
            {run.steps?.map((step) => (
              <div className={`maximum-agent-step ${step.status}`} key={step.id}>
                <span>{statusLabel(step.status)}</span>
                <strong>{step.agent}</strong>
                <p>{step.title}</p>
                {step.error ? <em>{step.error}</em> : null}
              </div>
            ))}
          </div>

          <div className="maximum-agent-columns">
            <section>
              <h4>Repair attempts</h4>
              {run.repairs?.length ? run.repairs.map((repair) => (
                <div className="maximum-agent-mini" key={repair.number}>
                  <strong>Attempt {repair.number}</strong>
                  <p>Changed: {repair.changed_files?.join(", ") || "none"}</p>
                  <p>Remaining: {repair.remaining_failures?.join(", ") || "none"}</p>
                </div>
              )) : <p>No repair loop was needed.</p>}
            </section>
            <section>
              <h4>Changed files</h4>
              <div className="maximum-agent-files rich">
                {files.slice(0, 24).map((file) => {
                  const meta = getFileMeta(file);
                  return (
                    <div className="maximum-agent-file-row" key={file}>
                      <span className={`agent-file-icon ${meta.className}`}>{meta.icon}</span>
                      <code>{file}</code>
                      <button type="button" onClick={() => setActiveFile(file)}>Preview</button>
                      <button type="button" onClick={() => downloadTextFile(file, fileContents[file] || "")}>Download</button>
                    </div>
                  );
                })}
              </div>
            </section>
          </div>

          <AgentToolRoutes routes={run.capabilities || []} />

          <AgentFileTree
            files={files}
            fileContents={fileContents}
            title="Generated project folders and files"
            onPreview={setActiveFile}
          />

          {activeFile ? (
            <section className="agent-file-preview">
              <div className="agent-file-preview-head">
                <strong><span className={`agent-file-icon ${activeFileMeta.className}`}>{activeFileMeta.icon}</span> {activeFile}</strong>
                <button type="button" onClick={() => downloadTextFile(activeFile, fileContents[activeFile] || "")}>Download file</button>
              </div>
              <pre>{fileContents[activeFile] || "File content is not available in this response."}</pre>
            </section>
          ) : null}

          <details className="maximum-agent-details">
            <summary>Verification evidence</summary>
            <pre>{JSON.stringify(run.validation, null, 2)}</pre>
          </details>
        </article>
      ) : null}
    </section>
  );
}
