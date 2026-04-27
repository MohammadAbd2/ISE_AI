import RichMessage from "./RichMessage";
import DownloadableFileCard from "./DownloadableFileCard";
import DynamicDiagramCard from "./DynamicDiagramCard";
import { useEffect, useMemo, useState } from "react";
import DynamicVisualization from "./DynamicVisualization";
import AgentFileTree from "./AgentFileTree";
import { artifactDownloadUrl, artifactManifestUrl, readProjectFile } from "../lib/api";

function safeArtifactId(artifact) {
  if (!artifact) return "";
  if (typeof artifact === "string") return artifact;
  return artifact.artifact_id || artifact.id || artifact.uuid || "";
}

function triggerArtifactDownload(artifactId) {
  const id = safeArtifactId(artifactId);
  if (!id || typeof window === "undefined") return;
  const link = document.createElement("a");
  link.href = artifactDownloadUrl(id);
  link.download = "";
  link.rel = "noreferrer";
  document.body.appendChild(link);
  link.click();
  link.remove();
}


function normalizeRenderBlocks(blocks = []) {
  if (!Array.isArray(blocks)) return [];
  const hasTimeline = blocks.some((block) => block?.type === "agent_timeline");
  const hasDownloadArtifact = blocks.some((block) =>
    block?.type === "agent_timeline" && Array.isArray(block?.payload?.artifacts) && block.payload.artifacts.length > 0
  );
  return blocks.filter((block) => {
    if (!block || typeof block !== "object") return false;
    if (!hasTimeline) return true;
    if (block.type === "execution_packet") return false;
    if (block.type === "coding_result") return false;
    if (block.type === "plan_result") return false;
    if (block.type === "report") {
      const title = String(block.payload?.title || "").toLowerCase();
      return title.includes("roadmap") || title.includes("task");
    }
    if (block.type === "file_result") return true;
    if (block.type === "agent_timeline") return true;
    return true;
  });
}


function AIEngineerWorkbenchBlock({ payload }) {
  if (!payload || typeof payload !== "object") return null;
  const lanes = Array.isArray(payload.lanes) ? payload.lanes.filter(Boolean) : [];
  const truth = payload.truth && typeof payload.truth === "object" ? payload.truth : {};
  const safeText = (value, fallback = "") => String(value ?? fallback);
  return (
    <section className="engineer-workbench-block">
      <header className="engineer-hero">
        <div>
          <p className="eyebrow">{safeText(payload.headline, "Watching an AI engineer work")}</p>
          <h3>{safeText(payload.title, "AI Engineer Workbench")}</h3>
          <p>Thinking → building → debugging → shipping, with proof before the final result.</p>
        </div>
        <div className="truth-orb"><strong>{truth.score ?? 0}</strong><span>truth</span></div>
      </header>
      <div className="engineer-lanes">
        {lanes.map((lane, laneIndex) => {
          const laneName = safeText(lane?.name, `Engineer lane ${laneIndex + 1}`);
          const items = Array.isArray(lane?.items) ? lane.items.filter(Boolean) : [];
          return (
            <article key={`${laneName}-${laneIndex}`} className="engineer-lane">
              <strong>{laneName}</strong>
              {items.length ? items.map((item, index) => (
                <div key={`${laneName}-${index}`} className="engineer-step"><span>{safeText(item?.status, "working")}</span><p>{safeText(item?.detail || item?.action, "Collecting evidence...")}</p></div>
              )) : <div className="engineer-step muted"><span>idle</span><p>Waiting for task evidence.</p></div>}
            </article>
          );
        })}
      </div>
    </section>
  );
}

function TruthLayerCardBlock({ payload }) {
  if (!payload) return null;
  const checks = payload.checks || {};
  return <section className="render-card truth-layer-card"><div className="render-card-header"><span className="render-icon">✅</span><div><h4>Execution truth layer</h4><p>Only real files, previews, and verified checks are shown as completed.</p></div></div><div className="artifact-meta">{Object.entries(checks).map(([key, value]) => <span key={key} className={`artifact-chip ${value ? "available" : "muted"}`}>{key}: {String(value)}</span>)}</div></section>;
}

function ReasoningPathsBlock({ payload }) {
  const alternatives = Array.isArray(payload?.alternatives) ? payload.alternatives : [];
  return <section className="render-card reasoning-paths-card"><div className="render-card-header"><span className="render-icon">🧠</span><div><h4>Reasoning paths</h4><p>Selected path {payload?.selected || "A"} after comparing alternatives.</p></div></div><div className="engineer-lanes compact">{alternatives.map((alt) => <article key={alt.id} className={`engineer-lane ${payload?.selected === alt.id ? "selected" : ""}`}><strong>{alt.id}. {alt.name}</strong><p>{alt.why}</p><span>{alt.risk} risk</span></article>)}</div></section>;
}

function MultiAgentCrewBlock({ payload }) {
  const agents = Array.isArray(payload?.agents) ? payload.agents : [];
  return <section className="render-card crew-card"><div className="render-card-header"><span className="render-icon">👥</span><div><h4>Agent engineering crew</h4><p>Specialists coordinated as one brain.</p></div></div><div className="crew-grid">{agents.map((item, index) => <article key={`${item.agent}-${index}`}><strong>{item.agent}</strong><p>{item.task}</p><span>{item.status}</span></article>)}</div></section>;
}

function DesignSystemCardBlock({ payload }) {
  if (!payload) return null;
  const tokens = payload.tokens || {};
  const components = Array.isArray(payload.components) ? payload.components : [];
  return <section className="render-card design-system-card"><div className="render-card-header"><span className="render-icon">🎨</span><div><h4>Generated design system</h4><p>Tokens, components, and visual patterns generated dynamically from the task.</p></div></div><div className="artifact-meta">{Object.entries(tokens).slice(0, 8).map(([key, value]) => <span key={key} className="artifact-chip">{key}: {value}</span>)}</div><div className="crew-grid">{components.slice(0, 10).map((name) => <article key={name}><strong>{name}</strong><p>Reusable component generated for this project.</p></article>)}</div></section>;
}

function ThinkingTraceBlock({ payload }) {
  const [open, setOpen] = useState(!payload?.collapsed);
  if (!payload) return null;
  const steps = Array.isArray(payload.steps) ? payload.steps.filter(Boolean) : [];
  const commands = Array.isArray(payload.commands) ? payload.commands : [];
  const title = payload.title || "Thinking";
  return (
    <section className="thinking-trace-card">
      <button type="button" className="thinking-trace-title" onClick={() => setOpen((value) => !value)} aria-expanded={open}>
        <span className="thinking-dot" />
        <strong>{title}</strong>
        {payload.summary ? <span>{payload.summary}</span> : null}
        <span className="thinking-chevron">{open ? "▾" : "▸"}</span>
      </button>
      {open ? (
        <div className="thinking-trace-body">
          {steps.length ? (
            <ol>
              {steps.map((step, index) => <li key={`thinking-step-${index}`}>{step}</li>)}
            </ol>
          ) : <p>No detailed steps were reported.</p>}
          {commands.length ? commands.map((cmd, index) => (
            <div key={`thinking-command-${index}`} className="thinking-command">
              <code>{cmd.command || cmd}</code>
              {cmd.output ? <pre>{cmd.output}</pre> : null}
            </div>
          )) : null}
        </div>
      ) : null}
    </section>
  );
}


function LiveThinkingStreamBlock({ payload }) {
  const [open, setOpen] = useState(true);
  if (!payload) return null;
  const events = Array.isArray(payload.events) ? payload.events : [];
  return (
    <section className="dev-console-card live-thinking-card">
      <button type="button" className="dev-console-header" onClick={() => setOpen((value) => !value)} aria-expanded={open}>
        <span className="pulse-dot" />
        <div><strong>{payload.title || "Thinking"}</strong><span>{payload.summary || payload.request || "Agent is preparing the task."}</span></div>
        <em>{payload.status || "running"}</em>
      </button>
      {open ? <div className="dev-console-body event-stream-list">
        {events.length ? events.map((event, index) => <div key={`stream-event-${index}`} className={`event-stream-row ${event.status || ""}`}><span>{event.progress ?? "•"}%</span><strong>{event.label || "Agent"}</strong><p>{event.message || event.status || "Working"}</p></div>) : <p className="muted-small">Waiting for streamed events…</p>}
      </div> : null}
    </section>
  );
}

function InteractiveTerminalBlock({ payload }) {
  const [open, setOpen] = useState(true);
  const [selected, setSelected] = useState(0);
  const commands = Array.isArray(payload?.commands) ? payload.commands : [];
  const active = commands[selected] || commands[0];
  if (!payload || commands.length === 0) return null;
  async function copyCommand(command) { try { await navigator.clipboard?.writeText(command || ""); } catch { /* noop */ } }
  return (
    <section className="dev-console-card terminal-console-card">
      <button type="button" className="dev-console-header" onClick={() => setOpen((value) => !value)} aria-expanded={open}>
        <span>⌘</span><div><strong>{payload.title || "Terminal"}</strong><span>{commands.length} command/tool event{commands.length === 1 ? "" : "s"}</span></div><em>{payload.streaming ? "streaming" : "captured"}</em>
      </button>
      {open ? <div className="dev-console-body terminal-console-grid">
        <div className="terminal-command-tabs">{commands.map((cmd, index) => <button key={`cmd-tab-${index}`} type="button" className={index === selected ? "active" : ""} onClick={() => setSelected(index)}>{cmd.title || `Command ${index + 1}`}</button>)}</div>
        {active ? <div className="terminal-command-detail">
          {active.cwd ? <div className="terminal-cwd">{active.cwd}</div> : null}
          <pre className="terminal-command-line"><code>{active.command}</code></pre>
          <div className="terminal-actions"><button type="button" onClick={() => copyCommand(active.command)}>Copy</button><button type="button" disabled title="Backend rerun endpoint pending">Rerun</button><button type="button" disabled title="Backend cancel endpoint pending">Cancel</button><span>{active.status || "ready"}{Number.isFinite(active.exit_code) ? ` · exit ${active.exit_code}` : ""}</span></div>
          {active.output ? <pre className="terminal-output"><code>{active.output}</code></pre> : null}
          {active.stderr ? <pre className="terminal-output error"><code>{active.stderr}</code></pre> : null}
        </div> : null}
      </div> : null}
    </section>
  );
}

function EditableAgentPlanBlock({ payload }) {
  const [steps, setSteps] = useState(Array.isArray(payload?.steps) ? payload.steps : []);
  if (!payload) return null;
  return <section className="dev-console-card editable-plan-card"><div className="dev-console-header static"><span>🧭</span><div><strong>{payload.title || "Editable Agent plan"}</strong><span>{payload.note || "Review and refine the execution plan."}</span></div><em>{payload.readonly ? "preview" : "editable"}</em></div><div className="dev-console-body">{steps.length ? steps.map((step, index) => <label key={step.id || index} className="editable-step-row"><span>{index + 1}</span><input value={step.title || ""} readOnly={payload.readonly} onChange={(event) => setSteps((current) => current.map((item, idx) => idx === index ? { ...item, title: event.target.value } : item))} /><em>{step.status || "planned"}</em></label>) : <p className="muted-small">No plan steps were returned.</p>}</div></section>;
}

function FileExplorerBlock({ payload }) {
  const [openFile, setOpenFile] = useState(null);
  const files = Array.isArray(payload?.files) ? payload.files : [];
  if (!payload) return null;
  return <section className="dev-console-card file-explorer-card"><div className="dev-console-header static"><span>📁</span><div><strong>{payload.title || "Files"}</strong><span>{payload.root || "sandbox"}</span></div><em>{files.length} files</em></div><div className="dev-console-body file-explorer-grid"><div className="file-explorer-list">{files.length ? files.map((file, index) => <button key={`${file.path}-${index}`} type="button" onClick={() => setOpenFile(file)} className={openFile?.path === file.path ? "active" : ""}><span>{String(file.path || "file").split("/").pop()}</span><em>{file.status || "changed"}</em></button>) : <p className="muted-small">No files reported yet.</p>}</div><div className="file-explorer-preview">{openFile ? <><strong>{openFile.path}</strong><p>{openFile.summary || "Generated or touched by Agent."}</p></> : <p className="muted-small">Select a file to inspect metadata.</p>}{payload.artifact?.artifact_id ? <button type="button" onClick={() => triggerArtifactDownload(payload.artifact.artifact_id)}>Download artifact</button> : null}</div></div></section>;
}

function AgentLoopVisualizerBlock({ payload }) {
  const phases = Array.isArray(payload?.phases) ? payload.phases : [];
  if (!payload) return null;
  return <section className="dev-console-card loop-visualizer-card"><div className="dev-console-header static"><span>🔁</span><div><strong>{payload.title || "Agent loop"}</strong><span>Plan → Execute → Verify → Repair → Export</span></div><em>{payload.retry_count || 0} retries</em></div><div className="agent-loop-rail">{phases.map((phase, index) => <div key={phase.id || index} className={`loop-node ${phase.status || "pending"}`}><span>{index + 1}</span><strong>{phase.label}</strong><em>{phase.status}</em></div>)}</div></section>;
}

function SmartErrorExplainerBlock({ payload }) {
  const errors = Array.isArray(payload?.errors) ? payload.errors : [];
  if (!payload) return null;
  return <section className={`dev-console-card error-explainer-card ${errors.length ? "has-errors" : "ok"}`}><div className="dev-console-header static"><span>{errors.length ? "⚠️" : "✅"}</span><div><strong>{payload.title || "Error analysis"}</strong><span>{payload.explanation}</span></div><em>{errors.length ? `${errors.length} issue(s)` : "clean"}</em></div><div className="dev-console-body">{errors.length ? <ul>{errors.map((error, index) => <li key={`agent-error-${index}`}>{error}</li>)}</ul> : <p className="muted-small">No blocking validation errors were reported.</p>}{payload.stderr ? <pre className="terminal-output error"><code>{payload.stderr}</code></pre> : null}{payload.proposed_fix ? <p><strong>Proposed fix:</strong> {payload.proposed_fix}</p> : null}</div></section>;
}

function DeveloperControlsBlock({ payload }) {
  const [autonomy, setAutonomy] = useState(payload?.autonomy_level || "safe");
  if (!payload) return null;
  return <section className="dev-console-card developer-controls-card"><div className="dev-console-header static"><span>⚙️</span><div><strong>{payload.title || "Developer controls"}</strong><span>Control autonomy, retries, preview, export, and safety gates.</span></div><em>{autonomy}</em></div><div className="dev-console-body controls-grid"><label>Autonomy<select value={autonomy} onChange={(event) => setAutonomy(event.target.value)}><option value="safe">Safe</option><option value="assisted">Assisted</option><option value="autonomous">Autonomous</option></select></label><label>Retry limit<input type="number" min="0" max="8" defaultValue={payload.retry_limit ?? 2} /></label><label><input type="checkbox" defaultChecked={Boolean(payload.sandbox)} /> Sandbox only</label><label><input type="checkbox" defaultChecked={Boolean(payload.preview_enabled)} /> Preview enabled</label><label><input type="checkbox" defaultChecked={Boolean(payload.export_enabled)} /> Export enabled</label><label><input type="checkbox" defaultChecked={Boolean(payload.destructive_actions_require_approval)} /> Approval for destructive actions</label></div></section>;
}

function SelfImprovementPanelBlock({ payload }) {
  if (!payload) return null;
  const learned = Array.isArray(payload.learned) ? payload.learned : [];
  const upgrades = Array.isArray(payload.proposed_upgrades) ? payload.proposed_upgrades : [];
  return <section className="dev-console-card self-improvement-card"><div className="dev-console-header static"><span>🧠</span><div><strong>{payload.title || "Self-improvement"}</strong><span>Visible lessons and proposed upgrades from this run.</span></div><em>{payload.approval_required ? "approval required" : "auto"}</em></div><div className="dev-console-body self-improvement-grid"><div><strong>Learned</strong><ul>{learned.map((item, index) => <li key={`learned-${index}`}>{item}</li>)}</ul></div><div><strong>Proposed upgrades</strong><ul>{upgrades.map((item, index) => <li key={`upgrade-${index}`}>{item}</li>)}</ul></div></div></section>;
}

function VisualDataTableBlock({ payload }) {
  const rows = Array.isArray(payload?.rows) ? payload.rows : [];
  const columns = payload?.columns?.length ? payload.columns : Object.keys(rows[0] || {});
  if (!payload) return null;
  return <section className="agentic-visual-card"><header><span>📊</span><div><strong>{payload.title || "Data"}</strong><small>{rows.length} rows</small></div></header><div className="agentic-table-wrap"><table><thead><tr>{columns.map((column) => <th key={column}>{column}</th>)}</tr></thead><tbody>{rows.map((row, index) => <tr key={index}>{columns.map((column) => <td key={column}>{String(row[column] ?? "")}</td>)}</tr>)}</tbody></table></div></section>;
}
function VisualMetricGridBlock({ payload }) {
  const metrics = Array.isArray(payload?.metrics) ? payload.metrics : Array.isArray(payload?.rows) ? payload.rows : [];
  if (!payload) return null;
  return <section className="agentic-visual-card metric-grid-card"><header><span>📈</span><div><strong>{payload.title || "Metrics"}</strong><small>{metrics.length} signal{metrics.length === 1 ? "" : "s"}</small></div></header><div className="agentic-metric-grid">{metrics.map((metric, index) => <article key={`${metric.label || metric.metric || index}`}><small>{metric.label || metric.metric || `Metric ${index + 1}`}</small><strong>{metric.value ?? metric.count ?? metric.status ?? "ready"}</strong>{metric.trend ? <em>{metric.trend}</em> : null}</article>)}</div></section>;
}

function VisualJsonViewerBlock({ payload }) {
  if (!payload) return null;
  const data = payload.data ?? payload;
  return <section className="agentic-visual-card"><header><span>🧾</span><div><strong>{payload.title || "JSON"}</strong><small>structured object</small></div></header><pre>{JSON.stringify(data, null, 2)}</pre></section>;
}

function VisualImageGalleryBlock({ payload }) {
  const images = Array.isArray(payload?.images) ? payload.images : [];
  if (!payload) return null;
  return <section className="agentic-visual-card"><header><span>🖼️</span><div><strong>{payload.title || "Images"}</strong><small>{images.length} visual result{images.length === 1 ? "" : "s"}</small></div></header>{images.length ? <div className="agentic-image-grid">{images.map((image, index) => <figure key={`${image.url || image.data_url || image.name}-${index}`}><img src={image.url || image.data_url} alt={image.alt || image.caption || "Agent image"} /><figcaption>{image.caption || image.source || image.name || "Image"}</figcaption></figure>)}</div> : <p className="agentic-muted">No renderable images were returned yet.</p>}</section>;
}
function VisualFileGalleryBlock({ payload }) {
  const files = Array.isArray(payload?.files) ? payload.files : [];
  const [selected, setSelected] = useState(0);
  const file = files[selected] || files[0];
  if (!payload) return null;
  return <section className="agentic-visual-card"><header><span>📁</span><div><strong>{payload.title || "Generated files"}</strong><small>{files.length} file{files.length === 1 ? "" : "s"}</small></div></header><div className="agentic-file-grid"><div className="agentic-file-list">{files.map((item, index) => <button key={`${item.path || item.filename}-${index}`} className={index === selected ? "active" : ""} onClick={() => setSelected(index)}><strong>{item.path || item.filename || `file-${index + 1}`}</strong><small>{item.kind || item.extension || item.status || "file"}</small></button>)}</div><div className="agentic-file-preview">{file ? <><h4>{file.path || file.filename}</h4><p>{file.summary || file.preview || "Generated file preview."}</p>{file.content ? <pre>{file.content}</pre> : null}<div className="agentic-actions">{file.artifact_id ? <button type="button" onClick={() => triggerArtifactDownload(file.artifact_id)}>Download</button> : null}{file.preview_url ? <a href={file.preview_url} target="_blank" rel="noreferrer">Open preview</a> : null}</div></> : <p className="agentic-muted">No files returned.</p>}</div></div></section>;
}
function VisualDesignBriefBlock({ payload }) {
  if (!payload) return null;
  return <section className="agentic-visual-card design-brief-card"><header><span>🎨</span><div><strong>{payload.site_name || "Website design brief"}</strong><small>{payload.source_url || "DesigningAgent"}</small></div></header>{payload.safety_note ? <p>{payload.safety_note}</p> : null}<div className="agentic-token-row">{Object.entries(payload.design_tokens || {}).map(([key, value]) => <span key={key}><b>{key}</b>{String(value)}</span>)}</div><ol>{(payload.implementation_plan || []).map((step) => <li key={step}>{step}</li>)}</ol></section>;
}
function VisualRepairLoopBlock({ payload }) {
  const attempts = Array.isArray(payload?.attempts) ? payload.attempts : [];
  if (!payload) return null;
  return <section className="agentic-visual-card repair-loop-card"><header><span>🛠️</span><div><strong>{payload.title || "Repair loop"}</strong><small>{payload.policy || "analyze → patch → rerun"}</small></div></header>{payload.error ? <pre className="agentic-error">{payload.error}</pre> : null}<div className="agentic-repair-steps">{attempts.map((attempt) => <article key={attempt.step}><span>{attempt.step}</span><strong>{attempt.action}</strong><small>{attempt.status}</small></article>)}</div></section>;
}


function FigmaDesignBriefBlock({ payload }) {
  if (!payload) return null;
  const source = payload.source || {};
  const frames = Array.isArray(payload.frames) ? payload.frames : [];
  const plan = Array.isArray(payload.component_plan) ? payload.component_plan : [];
  return <section className="agentic-visual-card figma-design-card"><header><span>🎛️</span><div><strong>{source.file_name || "Figma design brief"}</strong><small>{source.url || "FigmaDesignAgent"}</small></div></header><div className="agentic-token-row">{Object.entries(payload.design_tokens || {}).map(([key, value]) => <span key={key}><b>{key}</b>{String(value)}</span>)}</div>{frames.length ? <div className="agentic-repair-steps">{frames.map((frame, index) => <article key={`${frame.name}-${index}`}><span>{index + 1}</span><strong>{frame.name}</strong><small>{frame.layout || frame.role}</small></article>)}</div> : null}{plan.length ? <ol>{plan.map((step) => <li key={step}>{step}</li>)}</ol> : null}<p className="agentic-muted">{payload.note}</p></section>;
}
function FigmaPrototypePreviewBlock({ payload }) {
  if (!payload) return null;
  const html = payload.html || "";
  return <section className="agentic-visual-card figma-prototype-card"><header><span>🧪</span><div><strong>{payload.title || "Browser prototype"}</strong><small>Prompt-to-prototype preview</small></div></header><iframe title={payload.title || "Prototype preview"} sandbox="allow-same-origin" srcDoc={html} style={{ width: "100%", minHeight: 420, border: "1px solid rgba(148,163,184,.25)", borderRadius: 18, background: "white" }} /><details className="agentic-visual-details"><summary>Show generated HTML</summary><pre>{html}</pre></details></section>;
}

function AttachmentList({ attachments }) {
  if (!attachments || attachments.length === 0) {
    return null;
  }

  return (
    <div className="message-attachments">
      {attachments.map((attachment) => (
        <span key={attachment.id} className="message-attachment-chip">
          {attachment.kind.toUpperCase()} · {attachment.name}
        </span>
      ))}
    </div>
  );
}

function ResearchProgressLog({ payload }) {
  if (!payload) return null;
  
  const { steps, latest_message, is_complete, is_error } = payload;
  
  if (!steps || steps.length === 0) return null;

  return (
    <div className={`research-progress-log ${is_complete ? 'complete' : ''} ${is_error ? 'error' : ''}`}>
      <div className="research-progress-header">
        <span className="research-progress-icon">
          {is_complete ? '✓' : is_error ? '❌' : '🔍'}
        </span>
        <span className="research-progress-status">{latest_message}</span>
      </div>
      <div className="research-progress-steps">
        {steps.map((step, index) => (
          <div key={index} className={`research-progress-step ${step.step}`}>
            <span className="step-icon">
              {step.is_complete ? '✓' : step.is_error ? '❌' : '•'}
            </span>
            <span className="step-message">{step.message}</span>
            {step.details && !step.is_complete && (
              <span className="step-details">{step.details}</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function CodingProgressLog({ payload }) {
  if (!payload) return null;

  const { steps, latest_message, is_complete, is_error } = payload;
  if (!steps || steps.length === 0) return null;

  return (
    <div className={`research-progress-log coding-progress-log ${is_complete ? 'complete' : ''} ${is_error ? 'error' : ''}`}>
      <div className="research-progress-header">
        <span className="research-progress-icon">
          {is_complete ? '✓' : is_error ? '❌' : '🤖'}
        </span>
        <span className="research-progress-status">{latest_message}</span>
      </div>
      <div className="research-progress-steps">
        {steps.map((step, index) => (
          <div key={index} className={`research-progress-step ${step.step}`}>
            <span className="step-icon">
              {step.is_complete ? '✓' : step.is_error ? '❌' : '•'}
            </span>
            <div className="coding-progress-step-body">
              <span className="step-message">{step.message}</span>
              {step.details ? (
                <span className="step-details">{step.details}</span>
              ) : null}
              {step.output ? (
                <pre className="coding-progress-output">{step.output}</pre>
              ) : null}
              {step.diff ? (
                <pre className="coding-progress-output diff">{step.diff}</pre>
              ) : null}
              {step.error ? (
                <pre className="coding-progress-output error">{step.error}</pre>
              ) : null}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}


function DownloadCardBlock({ payload }) {
  if (!payload) return null;
  const artifactId = payload.artifact_id;
  const href = artifactId ? artifactDownloadUrl(artifactId) : payload.download_url;
  if (!href && !payload.title) return null;
  return (
    <section className="render-card download-result-card">
      <div className="render-card-header">
        <span className="render-icon">{payload.icon || (payload.extension === ".pdf" ? "📕" : "📦")}</span>
        <div>
          <h4>{payload.title || "Download result"}</h4>
          <p>{payload.file_count === 1 ? "1 file" : payload.file_count ? `${payload.file_count} files` : "Downloadable artifact"}{payload.extension ? ` · ${payload.extension}` : ""}{payload.size_bytes ? ` · ${(payload.size_bytes / 1024).toFixed(1)} KB` : ""}</p>
        </div>
      </div>
      {payload.sha256 ? <code className="render-card-summary">sha256: {payload.sha256}</code> : null}
      {payload.write_verified !== undefined ? <span className={payload.write_verified ? "artifact-chip available" : "artifact-chip muted"}>{payload.write_verified ? "content verified" : "verification missing"}</span> : null}
      {href ? (
        <a className="response-feedback-chip primary" href={href} target="_blank" rel="noreferrer">
          Download {payload.extension ? payload.extension.replace(".", "").toUpperCase() : "file"}
        </a>
      ) : null}
    </section>
  );
}

function FolderListingBlock({ payload }) {
  const files = Array.isArray(payload?.files) ? payload.files : [];
  if (!files.length) return null;
  return (
    <section className="render-card folder-listing-card">
      <div className="render-card-header">
        <span className="render-icon">🗂️</span>
        <div>
          <h4>{payload.title || "Folder contents"}</h4>
          <p>{files.length} file{files.length === 1 ? "" : "s"} in the isolated environment</p>
        </div>
      </div>
      <div className="agent-run-command-list">
        {files.map((file) => (
          <code key={file.path}>{file.path} · {file.bytes || 0} bytes{file.preview ? ` · ${file.preview}` : ""}</code>
        ))}
      </div>
    </section>
  );
}

function FilePreviewBlock({ payload }) {
  if (payload?.content === undefined || payload?.content === null) return null;
  return (
    <section className="render-card file-preview-card">
      <div className="render-card-header">
        <span className="render-icon">📄</span>
        <div>
          <h4>{payload.title || "File content"}</h4>
        </div>
      </div>
      <pre className="coding-progress-output">{String(payload.content)}</pre>
    </section>
  );
}

function ResourceList({ payload }) {
  if (!payload || !payload.resources || payload.resources.length === 0) {
    return null;
  }

  const { title } = payload;
  const resources = uniqueBy(payload.resources, (resource) => normalizeUrlKey(resource?.url || resource?.image_url)).slice(0, 12);
  const imageResources = resources.filter((resource) => resource?.image_url).slice(0, 6);
  const webResources = resources.filter((resource) => resource?.kind !== "image" || !resource?.image_url);

  return (
    <div className="resource-list">
      <div className="resource-list-header">
        <span className="resource-list-icon">📚</span>
        <h4 className="resource-list-title">{title || 'Sources'}</h4>
        <span className="resource-count">{resources.length} unique</span>
      </div>
      {imageResources.length > 0 ? (
        <div className="resource-image-strip">
          {imageResources.map((resource, index) => (
            <a key={`image-${index}-${resource.image_url}`} href={resource.url || resource.image_url} target="_blank" rel="noreferrer" className="resource-image-tile">
              <img
                src={resource.image_url}
                alt={resource.title || resource.domain || "Internet image"}
                loading="lazy"
                onError={(e) => { e.currentTarget.closest('a')?.remove(); }}
              />
              <span>{resource.title || resource.domain || "Image"}</span>
            </a>
          ))}
        </div>
      ) : null}
      <div className="resource-grid">
        {webResources.map((resource, index) => (
          <a
            key={`${resource.url || resource.image_url}-${index}`}
            href={resource.url || resource.image_url}
            target="_blank"
            rel="noreferrer"
            className="resource-card"
            title={`${resource.title || resource.domain || 'Resource'}\n${resource.url || resource.image_url}`}
          >
            <div className="resource-card-content">
              <div className="resource-header">
                {resource.favicon_url ? (
                  <img
                    src={resource.favicon_url}
                    alt=""
                    className="resource-favicon"
                    onError={(e) => { e.currentTarget.style.display = 'none'; }}
                  />
                ) : null}
                <span className="resource-domain">{resource.domain || resource.kind || "source"}</span>
              </div>
              <div className="resource-title">{resource.title || resource.url}</div>
              {resource.snippet ? <div className="resource-snippet">{resource.snippet}</div> : null}
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}

function AgentProgressLog({ content }) {
  // Detect agent progress logs in content
  // Format: 🔧 **Task** followed by action items with ✅ 🔄 ⏳ ❌
  
  const agentLogPattern = /🔧\s+\*\*(.+?)\*\*/;
  const actionPattern = /(✅|🔄|⏳|❌)\s+\*\*(\w+):\*\*\s+(.+?)(?=\n(?:✅|🔄|⏳|❌|$))/gs;
  
  const isAgentLog = agentLogPattern.test(content);
  
  if (!isAgentLog) {
    return null;
  }
  
  const match = content.match(agentLogPattern);
  const taskName = match ? match[1] : "Agent Task";
  
  const actions = [];
  let actionMatch;
  while ((actionMatch = actionPattern.exec(content)) !== null) {
    const iconMap = {
      "✅": "completed",
      "🔄": "in-progress",
      "⏳": "pending",
      "❌": "failed",
    };
    
    actions.push({
      icon: actionMatch[1],
      status: iconMap[actionMatch[1]] || "pending",
      actionType: actionMatch[2],
      description: actionMatch[3].trim(),
    });
  }
  
  return (
    <div className="agent-progress-log">
      <div className="agent-progress-header">
        <span className="agent-progress-icon">🤖</span>
        <span className="agent-progress-title">Agent Mode: {taskName}</span>
      </div>
      <div className="agent-progress-actions">
        {actions.map((action, index) => (
          <div
            key={index}
            className={`agent-progress-action ${action.status}`}
          >
            <span className="agent-progress-action-icon">{action.icon}</span>
            <div className="agent-progress-action-content">
              <span className="agent-progress-action-type">{action.actionType}</span>
              <span className="agent-progress-action-desc">{action.description}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function uniqueBy(items, keyFn) {
  const seen = new Set();
  return (items || []).filter((item) => {
    const key = keyFn(item);
    if (!key) return true;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function normalizeUrlKey(value = "") {
  try {
    const url = new URL(value);
    url.hash = "";
    url.search = "";
    return url.toString().replace(/\/$/, "");
  } catch {
    return String(value || "").trim().toLowerCase();
  }
}

function ImageIntelLogList({ imageLogs }) {
  if (!imageLogs || imageLogs.length === 0) {
    return null;
  }
  const compactLogs = uniqueBy(imageLogs, (log) => `${log.kind || "search"}:${log.query || ""}:${log.searched_at || ""}`);

  return (
    <section className="image-intel-list">
      {compactLogs.map((log, index) => (
        <article
          key={`${log.kind}-${log.query || index}-${log.searched_at || index}`}
          className={`image-intel-card ${log.status === "failed" ? "failed" : ""}`}
        >
          <div className="image-intel-header">
            <span className="image-intel-badge">
              {log.kind === "generation"
                ? log.status === "failed"
                  ? "Image generation failed"
                  : "Generated image"
                : log.status === "failed"
                  ? "Image search failed"
                  : "Image search"}
            </span>
            <span className="image-intel-provider">{log.provider || "images"}</span>
          </div>
          {log.query ? <p className="image-intel-query">{log.query}</p> : null}
          {log.summary ? <p className="image-intel-summary">{log.summary}</p> : null}
          {log.error ? <p className="image-intel-error">{log.error}</p> : null}
          {Array.isArray(log.images) && log.images.length > 0 ? (
            <div className="image-intel-grid">
              {uniqueBy(log.images, (hit) => normalizeUrlKey(hit.image_url || hit.thumbnail_url || hit.page_url)).slice(0, 8).map((hit, hi) => {
                const href = hit.page_url || hit.image_url || "#";
                const src = hit.thumbnail_url || hit.image_url;
                return (
                  <a
                    key={`${hi}-${src?.slice(0, 48) || hi}`}
                    className="image-intel-cell"
                    href={href}
                    target="_blank"
                    rel="noreferrer"
                    onClick={(e) => {
                      // Prevent navigation if clicking on image
                      if (e.target.tagName === 'IMG') {
                        e.preventDefault();
                        // Open image in new tab
                        window.open(src, '_blank');
                      }
                    }}
                  >
                    {src ? (
                      <img 
                        src={src} 
                        alt={hit.title || "Image result"} 
                        loading="lazy"
                        style={{ cursor: 'pointer' }}
                        onError={(e) => {
                          // Handle broken images gracefully
                          e.target.style.display = 'none';
                          e.target.parentElement.innerHTML = '<div class="image-broken">Image unavailable</div>';
                        }}
                      />
                    ) : null}
                    <span className="image-intel-caption">
                      {hit.title || hit.source_name || "Image"}
                      {hit.source_name && <small style={{ display: 'block', opacity: 0.7, marginTop: '2px' }}>Source: {hit.source_name}</small>}
                    </span>
                  </a>
                );
              })}
            </div>
          ) : (
            <div className="image-intel-empty">
              <p>No images available. Try a different search query.</p>
            </div>
          )}
        </article>
      ))}
    </section>
  );
}

function SearchLogList({ searchLogs }) {
  if (!searchLogs || searchLogs.length === 0) {
    return null;
  }
  const compactLogs = uniqueBy(searchLogs, (log) => `${log.provider || "web"}:${log.query || ""}`);

  return (
    <section className="search-log-list">
      {compactLogs.map((log, index) => (
        <article
          key={`${log.query}-${log.searched_at || index}`}
          className={`search-log-card ${log.status === "failed" ? "failed" : ""}`}
        >
          <div className="search-log-header">
            <span className="search-log-badge">
              {log.status === "failed" ? "Web search failed" : "Web search"}
            </span>
            <span className="search-log-provider">{log.provider || "web"}</span>
          </div>
          <p className="search-log-query">
            <strong>Query:</strong> {log.query}
          </p>
          {log.summary ? (
            <p className="search-log-summary">
              <strong>Summary:</strong> {log.summary}
            </p>
          ) : null}
          {log.error ? <p className="search-log-error">Error: {log.error}</p> : null}
          {Array.isArray(log.sources) && log.sources.length > 0 ? (
            <div className="search-source-list">
              <h4 style={{ marginTop: "12px", marginBottom: "8px" }}>Sources ({log.sources.length})</h4>
              {uniqueBy(log.sources, (source) => normalizeUrlKey(source.url)).slice(0, 6).map((source, idx) => (
                <a
                  key={`${source.url}-${idx}`}
                  className="search-source-card"
                  href={source.url}
                  target="_blank"
                  rel="noreferrer"
                  style={{ display: "block", marginBottom: "12px", padding: "10px", borderLeft: "3px solid #0066cc" }}
                >
                  <strong style={{ display: "block", marginBottom: "4px" }}>{source.title || source.url}</strong>
                  <span style={{ display: "block", fontSize: "0.85em", color: "#666", marginBottom: "4px" }}>
                    {source.domain || source.url}
                  </span>
                  {source.snippet ? (
                    <small style={{ display: "block", marginBottom: "4px", color: "#555" }}>
                      {source.snippet}
                    </small>
                  ) : null}
                  {source.page_excerpt ? (
                    <small
                      className="search-source-page-excerpt"
                      style={{ display: "block", color: "#666", lineHeight: "1.4" }}
                    >
                      {source.page_excerpt.length > 300
                        ? `${source.page_excerpt.slice(0, 300)}…`
                        : source.page_excerpt}
                    </small>
                  ) : null}
                </a>
              ))}
            </div>
          ) : null}
        </article>
      ))}
    </section>
  );
}



function tokenizePreviewLine(line) {
  const pattern = /(#[^\n]*|\/\/[^\n]*|"(?:\\.|[^"])*"|'(?:\\.|[^'])*'|`(?:\\.|[^`])*`|\b(?:const|let|var|function|return|if|else|for|while|switch|case|break|continue|try|catch|finally|class|new|import|from|export|default|async|await|useState|useMemo|type|interface|def|pass|raise|yield|lambda|None|True|False|null|true|false|display|grid|flex|animation|background|color|padding|margin|border|transform|transition)\b|\b\d+(?:\.\d+)?(?:px|rem|em|%)?\b)/g;
  const pieces = [];
  let lastIndex = 0;
  let match;
  while ((match = pattern.exec(line)) !== null) {
    if (match.index > lastIndex) pieces.push({ type: "plain", value: line.slice(lastIndex, match.index) });
    const token = match[0];
    let type = "keyword";
    if (token.startsWith("#") || token.startsWith("//")) type = "comment";
    else if (token.startsWith("\"") || token.startsWith("'") || token.startsWith("`")) type = "string";
    else if (/^\d/.test(token)) type = "number";
    pieces.push({ type, value: token });
    lastIndex = pattern.lastIndex;
  }
  if (lastIndex < line.length) pieces.push({ type: "plain", value: line.slice(lastIndex) });
  return pieces;
}

function inferLanguageFromPath(path = "") {
  const safePath = typeof path === "string" ? path : String(path?.path || path?.filename || path?.name || "");
  const suffix = (safePath.split('.').pop() || "").toLowerCase();
  return ({ js: 'javascript', jsx: 'jsx', ts: 'typescript', tsx: 'tsx', py: 'python', css: 'css', html: 'html', json: 'json', md: 'markdown' })[suffix] || 'text';
}

function formatDuration(seconds = 0) {
  const value = Math.max(0, Math.floor(Number(seconds) || 0));
  const minutes = String(Math.floor(value / 60)).padStart(2, "0");
  const secs = String(value % 60).padStart(2, "0");
  return `${minutes}:${secs}`;
}

function useRunningElapsed(timing = {}, isRunning = false) {
  const initialElapsed = Math.max(0, Number(timing?.elapsed_seconds || 0));
  const [startedAt, setStartedAt] = useState(() => Date.now() - initialElapsed * 1000);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    setStartedAt(Date.now() - initialElapsed * 1000);
  }, [initialElapsed, isRunning]);

  useEffect(() => {
    if (!isRunning) return undefined;
    const id = setInterval(() => setTick((value) => value + 1), 1000);
    return () => clearInterval(id);
  }, [isRunning]);

  if (!isRunning) return initialElapsed;
  return Math.max(initialElapsed, Math.floor((Date.now() - startedAt) / 1000), tick);
}

function CodePreview({ language = 'text', code = '' }) {
  const lines = String(code || '').replace(/\n$/, '').split('\n');
  const [copied, setCopied] = useState(false);
  async function copyCode() {
    try {
      await navigator.clipboard.writeText(String(code || ''));
      setCopied(true);
      setTimeout(() => setCopied(false), 1400);
    } catch {
      setCopied(false);
    }
  }
  return (
    <div className="code-shell inline-preview rich-code-preview">
      <div className="code-shell-header">
        <div className="code-shell-lights"><span /><span /><span /></div>
        <div className="code-shell-language">{language}</div>
        <button type="button" className="code-copy-button" onClick={copyCode}>{copied ? "✓ Copied" : "📋 Copy"}</button>
      </div>
      <pre className={`code-shell-body language-${language}`}><code>{lines.map((line, index) => (
        <div key={`${index}-${line}`} className="code-line">
          <span className="code-line-number">{index + 1}</span>
          <span className="code-line-content">
            {tokenizePreviewLine(line).map((piece, pieceIndex) => (
              <span key={`${pieceIndex}-${piece.value}`} className={`token-${piece.type}`}>{piece.value}</span>
            ))}
          </span>
        </div>
      ))}</code></pre>
    </div>
  );
}

function ReportBlock({ payload }) {
  const title = payload?.title || "Report";
  const summary = payload?.summary || "";
  const highlights = Array.isArray(payload?.highlights) ? payload.highlights : [];

  return (
    <section className="render-report-card">
      <div className="render-card-header">
        <strong>{title}</strong>
        <span>Report</span>
      </div>
      {summary ? <p className="render-card-summary">{summary}</p> : null}
      {highlights.length > 0 ? (
        <div className="render-card-list">
          {highlights.map((item, index) => (
            <div key={`${title}-${index}`} className="render-card-item">
              {item}
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function ReplyOptionsBlock({ payload, onResponsePreference }) {
  const options = Array.isArray(payload?.options) ? payload.options : [];
  if (options.length === 0 || !onResponsePreference) {
    return null;
  }

  return (
    <section className="render-report-card reply-options-card">
      <div className="render-card-header">
        <strong>{payload?.title || "Tune future replies"}</strong>
        <span>Preference</span>
      </div>
      <div className="response-feedback-bar embedded">
        {options.map((option) => (
          <button
            key={`${option.style}-${option.label}`}
            type="button"
            className="response-feedback-chip"
            title={option.description || ""}
            onClick={() => onResponsePreference(option.style)}
          >
            {option.label}
          </button>
        ))}
      </div>
    </section>
  );
}

function ProgrammingAGIRunBlock({ payload }) {
  if (!payload) return null;
  const steps = Array.isArray(payload.steps) ? payload.steps : [];
  const files = Array.isArray(payload.files_changed) ? payload.files_changed : [];
  const preview = payload.preview || {};
  const exportInfo = payload.export || {};
  const validation = payload.validation || {};
  const repairs = Array.isArray(payload.repairs) ? payload.repairs : [];
  const commands = Array.isArray(payload.verification_commands) ? payload.verification_commands : [];
  const status = String(payload.status || "running");
  const progress = Number(payload.progress || 0);
  return (
    <section className={`agent-run-card ${status.includes("fail") ? "failed" : status.includes("complete") ? "ready" : "running"}`}>
      <header className="agent-run-hero">
        <div>
          <p className="agent-run-kicker">Chat-native Agent</p>
          <h3>{status}</h3>
          <p>Planner → memory → sandbox → verifier → repair → preview → export. Output root: {exportInfo.default_output_folder || exportInfo.output_root || "./AGI_Output"}</p>
        </div>
        <div className="agent-run-score"><strong>{progress}%</strong><span>{validation.passed ? "verified" : "checking"}</span></div>
      </header>
      <div className="agent-run-meter"><span style={{ width: `${Math.max(0, Math.min(progress, 100))}%` }} /></div>
      <div className="response-feedback-bar embedded">
        {preview.url ? <a className="response-feedback-chip primary" href={preview.url} target="_blank" rel="noreferrer">Open Preview</a> : null}
        {preview.command ? <code className="response-feedback-label">{preview.command}</code> : null}
        {exportInfo.artifact_id ? <a className="response-feedback-chip primary" href={artifactDownloadUrl(exportInfo.artifact_id)} target="_blank" rel="noreferrer">Download ZIP</a> : null}
        {exportInfo.zip_path || exportInfo.path ? <span className="response-feedback-label">ZIP: {exportInfo.filename || exportInfo.zip_path || exportInfo.path}</span> : null}
      </div>
      {steps.length ? (
        <div className="agent-run-agents">
          {steps.map((step) => (
            <article key={step.id} className={`agent-mini ${step.status === "completed" ? "done" : step.status === "failed" ? "failed" : "active"}`}>
              <strong>{step.agent}</strong>
              <span>{step.title}</span>
            </article>
          ))}
        </div>
      ) : null}
      {validation.failed?.length ? (
        <div className="render-card-summary warning">Blocked gates: {validation.failed.join(" · ")}</div>
      ) : <div className="render-card-summary success">All verification gates passed.</div>}
      {commands.length ? (
        <div className="agent-run-command-list">
          {commands.map((cmd, index) => (
            <code key={`${cmd.cwd}-${cmd.command}-${index}`}>{cmd.cwd}: {cmd.command}</code>
          ))}
        </div>
      ) : null}
      {repairs.length ? (
        <div className="agent-run-command-list">
          {repairs.map((repair) => (
            <code key={repair.number}>repair {repair.number}: {(repair.remaining_failures || []).join(", ") || "resolved"}</code>
          ))}
        </div>
      ) : null}
      {files.length ? (
        <AgentFileTree
          files={files}
          fileContents={payload.file_contents || {}}
          title="Sandbox workspace files"
        />
      ) : null}
    </section>
  );
}

function FileResultBlock({ payload }) {
  const [expandedFile, setExpandedFile] = useState("");
  const [fileContent, setFileContent] = useState({});
  const [loadingPath, setLoadingPath] = useState("");
  const files = Array.isArray(payload?.files) ? payload.files : [];
  if (files.length === 0) {
    return null;
  }

  async function handlePreviewFile(file) {
    const path = file.path;
    if (!path) {
      return;
    }
    if (expandedFile === path) {
      setExpandedFile("");
      return;
    }
    if (fileContent[path]) {
      setExpandedFile(path);
      return;
    }
    if (file.content) {
      setFileContent((current) => ({ ...current, [path]: file.content }));
      setExpandedFile(path);
      return;
    }
    setLoadingPath(path);
    try {
      const result = await readProjectFile(path);
      setFileContent((current) => ({
        ...current,
        [path]: result.success ? result.content || "" : result.message || "Could not read file content.",
      }));
      setExpandedFile(path);
    } catch {
      setFileContent((current) => ({
        ...current,
        [path]: "Could not load file preview.",
      }));
      setExpandedFile(path);
    } finally {
      setLoadingPath("");
    }
  }

  return (
    <section className="render-file-card">
      <div className="render-card-header">
        <strong>{payload?.title || "Files changed"}</strong>
        <span>{files.length} file{files.length === 1 ? "" : "s"}</span>
      </div>
      <div className="render-card-list">
        {files.map((file, index) => {
          const key = `${file.path || file.artifact_id || index}`;
          const language = file.language || inferLanguageFromPath(file.path || file.title || "");
          return (
            <div key={key} className="render-card-item file-item rich-file-item">
              <div>
                <strong>{file.path || file.title || "Generated file"}</strong>
                {file.summary ? <p>{file.summary}</p> : null}
                {file.diff ? <pre className="render-diff-preview">{file.diff}</pre> : null}
                {expandedFile === file.path ? (
                  <CodePreview language={language} code={fileContent[file.path] || file.content || ""} />
                ) : null}
              </div>
              <div className="file-item-actions">
                {file.path ? (
                  <button
                    type="button"
                    className="ghost-button compact-button"
                    onClick={() => handlePreviewFile(file)}
                    disabled={loadingPath === file.path}
                  >
                    {loadingPath === file.path ? "Loading..." : expandedFile === file.path ? "Hide preview" : "Preview code"}
                  </button>
                ) : null}
                {file.artifact_id ? (
                  <button type="button" className="response-feedback-chip primary" onClick={() => triggerArtifactDownload(file.artifact_id)}>
                    ⬇ Download ZIP
                  </button>
                ) : null}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function AgentTimelineBlock({ payload }) {
  const status = String(payload?.status || "running").toLowerCase();
  const events = Array.isArray(payload?.events) ? payload.events : [];
  const messages = Array.isArray(payload?.messages) ? payload.messages : [];
  const decisions = Array.isArray(payload?.decisions) ? payload.decisions : [];
  const files = Array.isArray(payload?.files) ? payload.files : [];
  const artifacts = Array.isArray(payload?.artifacts) ? payload.artifacts : [];
  const timing = payload?.timing || {};
  const visibleEvents = events.length > 0 ? events : messages.map((message) => ({
    agent: message.sender,
    phase: message.kind,
    status: message.kind === "error" ? "failed" : "completed",
    message: message.content,
    target: message.metadata?.path || message.metadata?.target || "",
    output: message.metadata?.output || "",
    error: message.metadata?.error || "",
  }));
  if (visibleEvents.length === 0 && decisions.length === 0 && files.length === 0 && artifacts.length === 0) return null;

  const normalized = visibleEvents.map((event) => ({ ...event, status: String(event.status || "pending").toLowerCase() }));
  const completed = normalized.filter((event) => ["completed", "done", "success", "skipped"].includes(event.status)).length;
  const failed = normalized.filter((event) => ["failed", "error"].includes(event.status)).length;
  const hasExport = artifacts.length > 0 || normalized.some((event) => event.agent === "ExportAgent" && ["completed", "success", "done"].includes(event.status));
  const terminal = hasExport || ["completed", "success", "done", "ready", "exported"].includes(status);
  const hasRunning = normalized.some((event) => ["running", "working", "in_progress", "queued"].includes(event.status));
  const running = !failed && !terminal && (hasRunning || ["running", "working", "in_progress", "queued"].includes(status));
  const displayElapsed = useRunningElapsed(timing, running);
  const explicitProgress = Number(payload?.progress ?? payload?.percent ?? timing?.progress ?? NaN);
  const eventProgress = normalized.length ? Math.round((completed / normalized.length) * 100) : 0;
  const baseProgress = Number.isFinite(explicitProgress) ? explicitProgress : eventProgress;
  const progress = terminal ? 100 : failed ? Math.max(Math.min(baseProgress, 99), 1) : running ? Math.max(4, Math.min(baseProgress || 12, 98)) : Math.max(0, Math.min(baseProgress, 99));
  const statusLabel = failed ? "Needs repair" : terminal ? "Ready" : running ? "Working" : "Paused";
  const latest = [...normalized].reverse().find((event) => event.message || event.content);
  const stepsByAgent = normalized.reduce((acc, event) => {
    const agent = event.agent || "Agent";
    acc[agent] = acc[agent] || { total: 0, completed: 0, failed: 0 };
    acc[agent].total += 1;
    if (["completed", "done", "success", "skipped"].includes(event.status)) acc[agent].completed += 1;
    if (["failed", "error"].includes(event.status)) acc[agent].failed += 1;
    return acc;
  }, {});
  const importantEvents = normalized.filter((event) => {
    const phase = String(event.phase || event.kind || "").toLowerCase();
    return event.status === "failed" || event.agent === "ExportAgent" || phase.includes("verify") || phase.includes("run_command") || phase.includes("anti_template") || phase.includes("repair") || event.target;
  }).slice(-8);

  return (
    <section className={`agent-run-card ${failed ? "failed" : hasExport ? "ready" : running ? "running" : "idle"}`}>
      <header className="agent-run-hero">
        <div>
          <p className="agent-run-kicker">Sandbox run</p>
          <h3>{payload?.title || "Agent collaboration"}</h3>
          <p>{latest?.message || latest?.content || payload?.task || "Plan → build → verify → export"}</p>
        </div>
        <div className="agent-run-score">
          <strong>{progress}%</strong>
          <span>{statusLabel}</span>
        </div>
      </header>

      <div className="agent-run-meter" aria-label={`Progress ${progress}%`}><span style={{ width: `${progress}%` }} /></div>
      <div className="agent-run-meta">
        <span>{formatDuration(displayElapsed)} elapsed</span>
        <span>{completed}/{normalized.length || completed} events complete</span>
        {files.length ? <span>{files.length} file{files.length === 1 ? "" : "s"}</span> : null}
        {artifacts.length ? <span>ZIP ready</span> : null}
      </div>

      <div className="agent-run-agents">
        {Object.entries(stepsByAgent).map(([agent, meta]) => (
          <article key={agent} className={meta.failed ? "agent-mini failed" : meta.completed === meta.total ? "agent-mini done" : "agent-mini active"}>
            <strong>{agent}</strong>
            <span>{meta.failed ? "needs repair" : `${meta.completed}/${meta.total}`}</span>
          </article>
        ))}
      </div>

      {importantEvents.length ? (
        <details className="agent-run-details">
          <summary>View execution details</summary>
          <div className="agent-run-events">
            {importantEvents.map((event, index) => (
              <article key={`${event.agent}-${event.phase}-${index}`} className={`agent-run-event ${event.status || "pending"}`}>
                <div><strong>{event.agent || "Agent"}</strong><span>{event.phase || event.kind || event.status}</span></div>
                <p>{event.message || event.content}</p>
                {event.target ? <code>{event.target}</code> : null}
                {event.error ? <pre className="render-plan-output error">{event.error}</pre> : null}
                {event.output && event.output.length < 900 ? <pre className="render-plan-output">{event.output}</pre> : null}
              </article>
            ))}
          </div>
        </details>
      ) : null}

      {decisions.length > 0 ? (
        <div className="agent-run-decisions">
          {decisions.slice(-3).map((decision, index) => <span key={`${decision.agent}-${index}`}>{decision.agent}: {decision.content}</span>)}
        </div>
      ) : null}

      {files.length > 0 ? <div className="artifact-meta">{files.map((file) => <span key={file} className="artifact-chip">{file}</span>)}</div> : null}
      {artifacts.length > 0 ? (
        <div className="agent-artifact-bar">
          {artifacts.map((artifact, index) => {
            const artifactId = safeArtifactId(artifact);
            return artifactId ? <button key={`agent-artifact-${index}`} type="button" className="response-feedback-chip primary" onClick={() => triggerArtifactDownload(artifactId)}>⬇ Download verified ZIP</button> : null;
          })}
        </div>
      ) : null}
    </section>
  );
}

function CodingResultBlock({ payload }) {
  if (!payload) {
    return null;
  }

  const status = payload.status || "pending";
  const statusLabel = status.replace(/_/g, " ");
  const executionSteps = Array.isArray(payload.execution_steps) ? payload.execution_steps : [];
  const verificationSteps = Array.isArray(payload.verification_steps) ? payload.verification_steps : [];

  return (
    <section className={`render-coding-card ${status}`}>
      <div className="render-card-header">
        <strong>{payload.title || "Coding agent run"}</strong>
        <span>{statusLabel}</span>
      </div>
      <p className="render-coding-task">{payload.task}</p>
      {payload.message ? <p className="render-coding-message">{payload.message}</p> : null}
      <div className="render-coding-metrics">
        <div className="render-coding-metric">
          <strong>{payload.file_count || 0}</strong>
          <span>files touched</span>
        </div>
        <div className="render-coding-metric">
          <strong>{payload.verification_count || 0}</strong>
          <span>verification steps</span>
        </div>
      </div>
      {executionSteps.length > 0 ? (
        <div className="render-coding-section">
          <div className="render-coding-section-title">Execution</div>
          <div className="render-card-list">
            {executionSteps.map((step, index) => (
              <div key={`execution-${index}-${step.target || step.description}`} className={`render-card-item plan-item ${step.status || "pending"}`}>
                <div className="plan-item-row">
                  <strong>Step {step.step_number || index + 1}</strong>
                  <span className="plan-status">{step.status || "pending"}</span>
                </div>
                <p>{step.description}</p>
                {step.target ? <code>{step.target}</code> : null}
                {step.output ? <pre className="render-plan-output">{step.output}</pre> : null}
                {step.error ? <pre className="render-plan-output error">{step.error}</pre> : null}
              </div>
            ))}
          </div>
        </div>
      ) : null}
      {verificationSteps.length > 0 ? (
        <div className="render-coding-section">
          <div className="render-coding-section-title">Verification</div>
          <div className="render-card-list">
            {verificationSteps.map((step, index) => (
              <div key={`verification-${index}-${step.target || step.description}`} className={`render-card-item plan-item ${step.status || "pending"}`}>
                <div className="plan-item-row">
                  <strong>Check {step.step_number || index + 1}</strong>
                  <span className="plan-status">{step.status || "pending"}</span>
                </div>
                <p>{step.description}</p>
                {step.target ? <code>{step.target}</code> : null}
                {step.output ? <pre className="render-plan-output">{step.output}</pre> : null}
                {step.error ? <pre className="render-plan-output error">{step.error}</pre> : null}
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}

function ResearchResultBlock({ payload }) {
  const [showSources, setShowSources] = useState(false);
  const sources = Array.isArray(payload?.sources) ? payload.sources : [];
  const queryPlan = Array.isArray(payload?.query_plan) ? payload.query_plan : [];

  const getConfidenceIcon = (conf) => {
    if (conf === 'high') return '🟢';
    if (conf === 'medium') return '🟡';
    return '🔴';
  };

  return (
    <section className="render-research-card compact">
      <div className="render-card-header research-header" onClick={() => setShowSources(!showSources)} style={{ cursor: 'pointer' }}>
        <div className="header-left">
          <span className="research-icon">🔍</span>
          <strong>Research: {payload?.query || "Web Search"}</strong>
        </div>
        <div className="header-right">
          <span className="provider-badge">{payload?.provider || "web"}</span>
          <span className="expand-icon">{showSources ? '−' : '+'}</span>
        </div>
      </div>

      <div className="research-summary-strip">
        <div className="research-meta-pills">
          {payload?.confidence && (
            <span className={`meta-pill confidence ${payload.confidence}`} title={`Confidence: ${payload.confidence}`}>
              {getConfidenceIcon(payload.confidence)} {payload.confidence}
            </span>
          )}
          {payload?.freshness && (
            <span className="meta-pill freshness" title={payload.freshness}>
              📅 {payload.freshness.match(/\d{4}/)?.[0] || 'Recent'}
            </span>
          )}
          {sources.length > 0 && (
            <span className="meta-pill source-count">
              📚 {sources.length} sources
            </span>
          )}
        </div>
      </div>
      {payload?.comparison_summary ? (
        <div className="research-comparison-strip">{payload.comparison_summary}</div>
      ) : null}

      {showSources && (
        <div className="research-expanded-content">
          {queryPlan.length > 0 && (
            <div className="research-plan-mini">
              <small>Query Strategy:</small>
              <div className="plan-tags">
                {queryPlan.map((query, i) => (
                  <span key={i} className="plan-tag">{query}</span>
                ))}
              </div>
            </div>
          )}
          
          {payload?.conflict && (
            <div className="research-conflict-warning">
              ⚠️ {payload.conflict}
            </div>
          )}

          <div className="research-source-grid">
            {sources.map((source, index) => (
              <a
                key={source.url + index}
                className="source-item-card"
                href={source.url}
                target="_blank"
                rel="noreferrer"
              >
                <div className="source-card-top">
                  <span className="source-domain-mini">{source.domain || 'web'}</span>
                  {source.authority === 'official' && <span className="authority-badge">✓</span>}
                </div>
                <strong className="source-title-mini">{source.title}</strong>
                {source.snippet && <p className="source-snippet-mini">{source.snippet.slice(0, 120)}...</p>}
                {source.reason ? <small className="source-reason-mini">{source.reason}</small> : null}
              </a>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

function PlanResultBlock({ payload = {} }) {
  if (!payload || typeof payload !== "object") return null;
  const steps = Array.isArray(payload?.steps) ? payload.steps : [];
  const artifacts = Array.isArray(payload?.artifacts)
    ? payload.artifacts
    : (payload?.artifact || payload?.export_artifact ? [payload.artifact || payload.export_artifact] : []);
  const timing = payload?.timing || null;
  const totalSteps = steps.length;
  const completedSteps = steps.filter((step) => ["completed", "done", "success"].includes(String(step.status || "").toLowerCase())).length;
  const failedSteps = steps.filter((step) => ["failed", "error"].includes(String(step.status || "").toLowerCase())).length;
  const activeStep = steps.find((step) => ["running", "working", "in_progress"].includes(String(step.status || "").toLowerCase())) || steps.find((step) => String(step.status || "").toLowerCase() === "pending");
  const planIsRunning = failedSteps === 0 && completedSteps < totalSteps && Boolean(activeStep);
  const displayElapsed = useRunningElapsed(timing || {}, planIsRunning);
  const displayEstimated = Math.max(Number(timing?.estimated_seconds || payload?.estimated_seconds || totalSteps * 60 || 180), displayElapsed + (planIsRunning ? 1 : 0), 1);
  const stepProgress = totalSteps > 0 ? Math.round((completedSteps / totalSteps) * 100) : 0;
  const timeProgress = Math.min(planIsRunning ? 95 : 100, Math.round((displayElapsed / displayEstimated) * 100));
  const progressPercent = planIsRunning ? Math.max(stepProgress, timeProgress, 1) : (failedSteps ? stepProgress : 100);
  if (steps.length === 0) {
    return null;
  }

  return (
    <section className="render-plan-card manus-agent-card">
      <div className="render-card-header">
        <strong>{payload?.title || "Execution plan"}</strong>
        <span>{payload?.status || "pending"}</span>
        {timing || planIsRunning ? <span className="artifact-chip available">{formatDuration(displayElapsed)} / {formatDuration(displayEstimated)}</span> : null}
      </div>
      <div className="manus-progress-shell">
        <div className="manus-progress-topline">
          <span>{activeStep ? `${activeStep.agent || "Agent"}: ${activeStep.description}` : `${completedSteps}/${totalSteps} steps complete`}</span>
          <span>{progressPercent}%</span>
        </div>
        <div className="manus-progress-track"><span style={{ width: `${progressPercent}%` }} /></div>
      </div>
      <div className="render-card-list plan-list manus-timeline">
        {steps.map((step) => (
          <div
            key={`${payload?.title || "plan"}-${step.step_number}-${step.target || step.description}`}
            className={`render-card-item plan-item ${step.status || "pending"}`}
          >
            <div className="plan-item-row">
              <strong>{step.agent || `Step ${step.step_number}`}</strong>
              <span className="plan-status">{step.status || "pending"}</span>
            </div>
            <p>{step.description}</p>
            {step.target ? <code>{step.target}</code> : null}
            {step.output ? <pre className="render-plan-output">{step.output}</pre> : null}
            {step.error ? <pre className="render-plan-output error">{step.error}</pre> : null}
          </div>
        ))}
      </div>
      {artifacts.length > 0 ? (
        <div className="agent-artifact-bar">
          {artifacts.map((artifact, index) => {
            const artifactId = artifact.artifact_id || artifact.id;
            return artifactId ? (
              <a key={`agent-artifact-${index}`} className="response-feedback-chip primary" href={artifactDownloadUrl(artifactId)} download target="_blank" rel="noreferrer">
                ⬇ Download verified ZIP
              </a>
            ) : null;
          })}
        </div>
      ) : null}
    </section>
  );
}

function ExecutionPacketBlock({ payload, onExecute }) {
  if (!payload) {
    return null;
  }

  const targets = Array.isArray(payload.targets) ? payload.targets : [];
  const steps = Array.isArray(payload.steps) ? payload.steps : [];
  const verification = Array.isArray(payload.verification) ? payload.verification : [];
  const generatedAt = payload.generated_at ? new Date(payload.generated_at) : null;
  const minutesOld = generatedAt ? Math.max(0, Math.round((Date.now() - generatedAt.getTime()) / 60000)) : null;
  const freshnessLabel = payload.is_stale ? "stale" : minutesOld === null ? "" : "fresh";

  return (
    <section className="render-plan-card execution-packet-card">
      <div className="render-card-header">
        <strong>Execution packet</strong>
        <span>{freshnessLabel || "ready"}</span>
      </div>
      {payload.summary ? <p className="render-card-summary">{payload.summary}</p> : null}
      <div className="artifact-meta">
        {payload.packet_id ? <span className="artifact-chip">id: {payload.packet_id}</span> : null}
        {typeof payload.eval_score === "number" ? <span className="artifact-chip">score: {payload.eval_score}/10</span> : null}
        {generatedAt ? <span className="artifact-chip">{minutesOld}m old</span> : null}
        {payload.stale_reason ? <span className="artifact-chip muted">{payload.stale_reason}</span> : null}
        {payload.sandbox_branch ? <span className="artifact-chip available">sandbox: {payload.sandbox_branch}</span> : null}
        {typeof payload.merge_ready === "boolean" ? (
          <span className={`artifact-chip ${payload.merge_ready ? "available" : "muted"}`}>
            {payload.merge_ready ? "ready to merge" : "not merge-ready"}
          </span>
        ) : null}
      </div>
      {payload.merge_summary ? <p className="render-card-summary">{payload.merge_summary}</p> : null}
      {targets.length > 0 ? (
        <div className="render-card-list">
          {targets.map((item) => (
            <div key={`target-${item}`} className="render-card-item">
              <strong>Target</strong>
              <code>{item}</code>
            </div>
          ))}
        </div>
      ) : null}
      {steps.length > 0 ? (
        <div className="render-card-list plan-list">
          {steps.map((step) => (
            <div key={`packet-step-${step.step_number}`} className="render-card-item plan-item ready">
              <div className="plan-item-row">
                <strong>Step {step.step_number}</strong>
                <span className="plan-status">{step.status || "ready"}</span>
              </div>
              <p>{step.description}</p>
              {step.target ? <code>{step.target}</code> : null}
            </div>
          ))}
        </div>
      ) : null}
      {verification.length > 0 ? (
        <div className="render-card-list">
          {verification.map((item) => (
            <div key={`verification-${item}`} className="render-card-item">
              <strong>Verify</strong>
              <code>{item}</code>
            </div>
          ))}
        </div>
      ) : null}
      {(payload.export_artifact?.id || (onExecute && payload.ready)) ? (
        <div className="response-feedback-bar embedded">
          {payload.export_artifact?.id ? (
            <a className="response-feedback-chip primary" href={artifactDownloadUrl(payload.export_artifact.id)} download target="_blank" rel="noreferrer">
              ⬇ Download ZIP
            </a>
          ) : null}
          {onExecute && payload.ready ? (
            <button type="button" className="response-feedback-chip" onClick={() => onExecute(payload)}>
              {freshnessLabel === "stale" ? "Start remediation anyway" : "Start remediation"}
            </button>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

function ApprovalRequestBlock({ payload }) {
  const [status, setStatus] = useState("");
  const diffs = Array.isArray(payload?.staged_diffs) ? payload.staged_diffs : [];

  async function approve() {
    if (!payload?.plan_id) {
      return;
    }
    setStatus("Approving...");
    try {
      const response = await fetch(`/api/plans/${encodeURIComponent(payload.plan_id)}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          approved_by: "chat-user",
          message: "Approved from chat",
          accepted_files: diffs.map((item) => item.path).filter(Boolean),
        }),
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      setStatus("Approved. Resume started.");
    } catch (error) {
      setStatus(error.message || "Approval failed.");
    }
  }

  return (
    <section className="render-plan-card">
      <div className="render-card-header">
        <strong>Approval required</strong>
        <span>paused</span>
      </div>
      {payload?.task ? <p className="render-card-summary">{payload.task}</p> : null}
      {payload?.step_number ? <p>Blocked at step {payload.step_number}.</p> : null}
      {payload?.step_description ? <p>{payload.step_description}</p> : null}
      {payload?.approval_reason ? <pre className="render-plan-output error">{payload.approval_reason}</pre> : null}
      {diffs.length > 0 ? (
        <div className="render-card-list">
          {diffs.slice(0, 5).map((item) => (
            <div key={item.path} className="render-card-item">
              <strong>{item.path}</strong>
              <pre className="render-diff-preview">{item.diff || "(no diff)"}</pre>
            </div>
          ))}
        </div>
      ) : null}
      <div className="response-feedback-bar embedded">
        <button type="button" className="response-feedback-chip primary" onClick={approve}>
          Approve and resume
        </button>
        {status ? <span className="response-feedback-label">{status}</span> : null}
      </div>
    </section>
  );
}

function MessageBubbleWithAttachments({
  role,
  content,
  attachments,
  searchLogs,
  imageLogs,
  visualization,
  renderBlocks,
  messageKey,
  copiedKey,
  onCopy,
  onResponsePreference,
  isLatestAssistant,
  onContinue,
  onExecutePacket,
  isLoading,
}) {
  const isAssistant = role === "assistant";
  const showContinueButton =
    isAssistant &&
    isLatestAssistant &&
    !isLoading &&
    ((content || "").length > 700 || /generation stopped|provider failed|backend connection failed|continue/i.test(content || ""));

  return (
    <article className={`message-row ${isAssistant ? "assistant" : "user"}`}>
      <div className="avatar">{isAssistant ? "AI" : "ME"}</div>
      <div className="message-bubble">
        <div className="message-header">
          <span className="message-role">{isAssistant ? "Assistant" : "You"}</span>
          <button
            type="button"
            className="copy-button"
            onClick={() => onCopy()}
          >
            {copiedKey === messageKey ? "Copied" : "Copy"}
          </button>
        </div>
        <AttachmentList attachments={attachments} />
        {isAssistant ? <SearchLogList searchLogs={searchLogs} /> : null}
        {isAssistant ? <ImageIntelLogList imageLogs={imageLogs} /> : null}
        {isAssistant ? <AgentProgressLog content={content} /> : null}
        <RichMessage content={content || " "} />
        {isAssistant && isLatestAssistant && onResponsePreference ? (
          <div className="response-feedback-bar">
            <span className="response-feedback-label">Tune next replies</span>
            <button type="button" className="response-feedback-chip" onClick={() => onResponsePreference("concise")}>
              Shorter
            </button>
            <button type="button" className="response-feedback-chip" onClick={() => onResponsePreference("structured")}>
              More structured
            </button>
            {showContinueButton && onContinue ? (
              <button type="button" className="response-feedback-chip primary" onClick={() => onContinue()}>
                Continue
              </button>
            ) : null}
          </div>
        ) : null}
        {visualization ? <DynamicVisualization spec={visualization} /> : null}
        {normalizeRenderBlocks(renderBlocks).map((block, index) =>
              block?.type === "thinking_trace" ? (
                <ThinkingTraceBlock key={`${messageKey}-block-${index}`} payload={block.payload} />
              ) : block?.type === "live_thinking_stream" ? (
                <LiveThinkingStreamBlock key={`${messageKey}-block-${index}`} payload={block.payload} />
              ) : block?.type === "interactive_terminal" ? (
                <InteractiveTerminalBlock key={`${messageKey}-block-${index}`} payload={block.payload} />
              ) : block?.type === "editable_agent_plan" ? (
                <EditableAgentPlanBlock key={`${messageKey}-block-${index}`} payload={block.payload} />
              ) : block?.type === "file_explorer" ? (
                <FileExplorerBlock key={`${messageKey}-block-${index}`} payload={block.payload} />
              ) : block?.type === "agent_loop_visualizer" ? (
                <AgentLoopVisualizerBlock key={`${messageKey}-block-${index}`} payload={block.payload} />
              ) : block?.type === "smart_error_explainer" ? (
                <SmartErrorExplainerBlock key={`${messageKey}-block-${index}`} payload={block.payload} />
              ) : block?.type === "developer_controls" ? (
                <DeveloperControlsBlock key={`${messageKey}-block-${index}`} payload={block.payload} />
              ) : block?.type === "self_improvement_panel" ? (
                <SelfImprovementPanelBlock key={`${messageKey}-block-${index}`} payload={block.payload} />
              ) : block?.type === "visual_data_table" ? (
                <VisualDataTableBlock key={`${messageKey}-block-${index}`} payload={block.payload} />
              ) : block?.type === "visual_metric_grid" ? (
                <VisualMetricGridBlock key={`${messageKey}-block-${index}`} payload={block.payload} />
              ) : block?.type === "visual_json_viewer" ? (
                <VisualJsonViewerBlock key={`${messageKey}-block-${index}`} payload={block.payload} />
              ) : block?.type === "visual_image_gallery" ? (
                <VisualImageGalleryBlock key={`${messageKey}-block-${index}`} payload={block.payload} />
              ) : block?.type === "visual_file_gallery" ? (
                <VisualFileGalleryBlock key={`${messageKey}-block-${index}`} payload={block.payload} />
              ) : block?.type === "visual_design_brief" ? (
                <VisualDesignBriefBlock key={`${messageKey}-block-${index}`} payload={block.payload} />
              ) : block?.type === "visual_repair_loop" ? (
                <VisualRepairLoopBlock key={`${messageKey}-block-${index}`} payload={block.payload} />
              ) : block?.type === "ai_engineer_workbench" ? (
                <AIEngineerWorkbenchBlock key={`${messageKey}-block-${index}`} payload={block.payload} />
              ) : block?.type === "truth_layer_card" ? (
                <TruthLayerCardBlock key={`${messageKey}-block-${index}`} payload={block.payload} />
              ) : block?.type === "reasoning_paths" ? (
                <ReasoningPathsBlock key={`${messageKey}-block-${index}`} payload={block.payload} />
              ) : block?.type === "multi_agent_crew" ? (
                <MultiAgentCrewBlock key={`${messageKey}-block-${index}`} payload={block.payload} />
              ) : block?.type === "design_system_card" ? (
                <DesignSystemCardBlock key={`${messageKey}-block-${index}`} payload={block.payload} />
              ) : block?.type === "figma_design_brief" ? (
                <FigmaDesignBriefBlock key={`${messageKey}-block-${index}`} payload={block.payload} />
              ) : block?.type === "figma_prototype_preview" ? (
                <FigmaPrototypePreviewBlock key={`${messageKey}-block-${index}`} payload={block.payload} />
              ) : block?.type === "execution_summary" ? (
                <VisualJsonViewerBlock key={`${messageKey}-block-${index}`} payload={{ title: block.payload?.title || "Execution summary", data: block.payload }} />
              ) : block?.type === "browser_preview" ? (
                <FigmaPrototypePreviewBlock key={`${messageKey}-block-${index}`} payload={{ title: block.payload?.title || "Browser preview", html: block.payload?.html || `<iframe src="${block.payload?.url || block.payload?.path || "about:blank"}"></iframe>` }} />
              ) : block?.type === "project_file_gallery" ? (
                <VisualFileGalleryBlock key={`${messageKey}-block-${index}`} payload={block.payload} />
              ) : block?.type === "error_debug_panel" ? (
                <VisualJsonViewerBlock key={`${messageKey}-block-${index}`} payload={{ title: "Debug analysis", data: block.payload }} />
              ) : block?.type === "visualization" ? (
                <DynamicVisualization key={`${messageKey}-block-${index}`} spec={block.payload} />
              ) : block?.type === "coding_progress" ? (
                <CodingProgressLog key={`${messageKey}-block-${index}`} payload={block.payload} />
              ) : block?.type === "research_progress" ? (
                <ResearchProgressLog key={`${messageKey}-block-${index}`} payload={block.payload} />
              ) : block?.type === "resource_list" ? (
                <ResourceList key={`${messageKey}-block-${index}`} payload={block.payload} />
              ) : block?.type === "download_card" ? (
                <DownloadCardBlock key={`${messageKey}-block-${index}`} payload={block.payload} />
              ) : block?.type === "folder_listing" ? (
                <FolderListingBlock key={`${messageKey}-block-${index}`} payload={block.payload} />
              ) : block?.type === "file_preview" ? (
                <FilePreviewBlock key={`${messageKey}-block-${index}`} payload={block.payload} />
              ) : block?.type === "report" ? (
                <ReportBlock key={`${messageKey}-block-${index}`} payload={block.payload} />
              ) : block?.type === "reply_options" ? (
                <ReplyOptionsBlock
                  key={`${messageKey}-block-${index}`}
                  payload={block.payload}
                  onResponsePreference={(style) => onResponsePreference?.(style)}
                />
              ) : block?.type === "coding_result" ? (
                <CodingResultBlock key={`${messageKey}-block-${index}`} payload={block.payload} />
              ) : block?.type === "research_result" ? (
                <ResearchResultBlock key={`${messageKey}-block-${index}`} payload={block.payload} />
              ) : block?.type === "plan_result" ? (
                <PlanResultBlock key={`${messageKey}-block-${index}`} payload={block.payload} />
              ) : block?.type === "agent_timeline" ? (
                <AgentTimelineBlock key={`${messageKey}-block-${index}`} payload={block.payload} />
              ) : block?.type === "execution_packet" ? (
                <ExecutionPacketBlock
                  key={`${messageKey}-block-${index}`}
                  payload={block.payload}
                  onExecute={onExecutePacket}
                />
              ) : block?.type === "approval_request" ? (
                <ApprovalRequestBlock key={`${messageKey}-block-${index}`} payload={block.payload} />
              ) : block?.type === "programming_agi_run" ? (
                <ProgrammingAGIRunBlock key={`${messageKey}-block-${index}`} payload={block.payload} />
              ) : block?.type === "file_result" ? (
                <FileResultBlock key={`${messageKey}-block-${index}`} payload={block.payload} />
              ) : block?.type === "downloadable_file" ? (
                <DownloadableFileCard key={`${messageKey}-block-${index}`} file={block.payload} />
              ) : block?.type === "dynamic_diagram" ? (
                <DynamicDiagramCard key={`${messageKey}-block-${index}`} diagram={block.payload} />
              ) : null,
            )}
      </div>
    </article>
  );
}

export default function MessageList({
  messages,
  isLoading,
  copiedKey,
  onCopyMessage,
  onResponsePreference,
  onContinue,
  onExecutePacket,
}) {
  const latestAssistantIndex = [...messages]
    .map((message, index) => ({ message, index }))
    .reverse()
    .find((entry) => entry.message.role === "assistant")?.index;

  return (
    <section className="message-list">
      {/* Rendering order is preserved so streaming text can update the last assistant bubble in place. */}
      {messages.map((message, index) => (
        <MessageBubbleWithAttachments
          key={`${message.role}-${index}`}
          role={message.role}
          content={message.content}
          attachments={message.attachments || []}
          searchLogs={message.search_logs || []}
          imageLogs={message.image_logs || []}
          visualization={message.visualization || null}
          renderBlocks={message.render_blocks || []}
          messageKey={`${message.role}-${index}`}
          copiedKey={copiedKey}
          onCopy={() => onCopyMessage(message, index)}
          onResponsePreference={(style) => onResponsePreference?.(style, message)}
          isLatestAssistant={index === latestAssistantIndex}
          onContinue={() => onContinue?.(message)}
          onExecutePacket={onExecutePacket}
          isLoading={isLoading}
        />
      ))}
      {isLoading ? <div className="stream-status">Streaming response</div> : null}
    </section>
  );
}
