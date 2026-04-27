import { useEffect, useMemo, useState } from "react";
import { api, fetchJson, artifactDownloadUrl } from "../lib/api";

function JsonDetails({ title, data }) {
  return (
    <details className="agentic-visual-details">
      <summary>{title}</summary>
      <pre>{JSON.stringify(data, null, 2)}</pre>
    </details>
  );
}

function VisualDataTable({ payload }) {
  const rows = Array.isArray(payload?.rows) ? payload.rows : [];
  const columns = payload?.columns?.length ? payload.columns : Object.keys(rows[0] || {});
  return (
    <section className="agentic-visual-card">
      <header><span>📊</span><div><strong>{payload?.title || "Data"}</strong><small>{rows.length} rows</small></div></header>
      <div className="agentic-table-wrap"><table><thead><tr>{columns.map((col) => <th key={col}>{col}</th>)}</tr></thead><tbody>{rows.map((row, idx) => <tr key={idx}>{columns.map((col) => <td key={col}>{String(row[col] ?? "")}</td>)}</tr>)}</tbody></table></div>
    </section>
  );
}

function VisualImageGallery({ payload }) {
  const images = Array.isArray(payload?.images) ? payload.images : [];
  return (
    <section className="agentic-visual-card">
      <header><span>🖼️</span><div><strong>{payload?.title || "Images"}</strong><small>Internet, upload, generated, or analyzed images</small></div></header>
      {images.length ? <div className="agentic-image-grid">{images.map((image, idx) => <figure key={`${image.url || image.name}-${idx}`}><img src={image.url || image.data_url} alt={image.alt || image.caption || "Agent visual"} /><figcaption>{image.caption || image.source || image.name || "Image"}</figcaption></figure>)}</div> : <p className="agentic-muted">No images attached yet. The Agent will render uploaded, internet, or generated images here.</p>}
    </section>
  );
}

function VisualFileGallery({ payload }) {
  const files = Array.isArray(payload?.files) ? payload.files : [];
  const [selected, setSelected] = useState(0);
  const file = files[selected] || files[0];
  return (
    <section className="agentic-visual-card">
      <header><span>📁</span><div><strong>{payload?.title || "Files"}</strong><small>{files.length} generated or planned files</small></div></header>
      <div className="agentic-file-grid">
        <div className="agentic-file-list">{files.map((item, idx) => <button key={`${item.path || item.filename}-${idx}`} className={idx === selected ? "active" : ""} onClick={() => setSelected(idx)}><strong>{item.path || item.filename || `file-${idx + 1}`}</strong><small>{item.kind || item.extension || "file"}</small></button>)}</div>
        <div className="agentic-file-preview">
          {file ? <><h4>{file.path || file.filename}</h4><p>{file.summary || file.preview || "Generated file preview will appear here."}</p>{file.content ? <pre>{file.content}</pre> : null}<div className="agentic-actions">{file.artifact_id ? <a href={artifactDownloadUrl(file.artifact_id)} target="_blank" rel="noreferrer">Download</a> : null}{file.preview_url ? <a href={file.preview_url} target="_blank" rel="noreferrer">Open preview</a> : null}</div></> : <p>No files yet.</p>}
        </div>
      </div>
    </section>
  );
}

function DesignBrief({ payload }) {
  return (
    <section className="agentic-visual-card design-brief-card">
      <header><span>🎨</span><div><strong>{payload?.site_name || "Design brief"}</strong><small>{payload?.source_url || "Website analysis"}</small></div></header>
      <p>{payload?.safety_note}</p>
      <div className="agentic-token-row">{Object.entries(payload?.design_tokens || {}).map(([key, value]) => <span key={key}><b>{key}</b>{String(value)}</span>)}</div>
      <ol>{(payload?.implementation_plan || []).map((step) => <li key={step}>{step}</li>)}</ol>
    </section>
  );
}

function RepairLoop({ payload }) {
  const attempts = Array.isArray(payload?.attempts) ? payload.attempts : [];
  return (
    <section className="agentic-visual-card repair-loop-card">
      <header><span>🛠️</span><div><strong>{payload?.title || "Repair loop"}</strong><small>{payload?.policy || "repair then retry"}</small></div></header>
      {payload?.error ? <pre className="agentic-error">{payload.error}</pre> : null}
      <div className="agentic-repair-steps">{attempts.map((attempt) => <article key={attempt.step}><span>{attempt.step}</span><strong>{attempt.action}</strong><small>{attempt.status}</small></article>)}</div>
    </section>
  );
}

function RenderBlock({ block }) {
  if (block?.type === "visual_data_table") return <VisualDataTable payload={block.payload} />;
  if (block?.type === "visual_image_gallery") return <VisualImageGallery payload={block.payload} />;
  if (block?.type === "visual_file_gallery") return <VisualFileGallery payload={block.payload} />;
  if (block?.type === "visual_design_brief") return <DesignBrief payload={block.payload} />;
  if (block?.type === "visual_repair_loop") return <RepairLoop payload={block.payload} />;
  return <JsonDetails title={block?.type || "Block"} data={block} />;
}

export default function AgenticVisualPanel() {
  const [roadmap, setRoadmap] = useState(null);
  const [panel, setPanel] = useState(null);
  const [components, setComponents] = useState(null);
  const [task, setTask] = useState("Create a website similar to https://example.com and render the generated project in chat");
  const [url, setUrl] = useState("https://example.com");
  const [errorText, setErrorText] = useState("Blocked gates: no_template_markers · import_graph_resolves");
  const [blocks, setBlocks] = useState([]);
  const [message, setMessage] = useState("");

  async function refresh() {
    const [r, p, c] = await Promise.all([fetchJson(api.agenticVisualRoadmap), fetchJson(api.agenticVisualPanel), fetchJson(api.agenticVisualComponents)]);
    setRoadmap(r); setPanel(p); setComponents(c);
  }

  useEffect(() => { refresh().catch((err) => setMessage(err.message || String(err))); }, []);

  async function buildRenderContract() {
    const result = await fetchJson(api.agenticVisualRenderContract, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ task, data: [{ case: "data", renderer: "table", status: "ready" }, { case: "files", renderer: "gallery", status: "ready" }] }) });
    setBlocks(result.blocks || []);
  }

  async function runDesignAgent() {
    const result = await fetchJson(api.agenticVisualDesignFromUrl, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ url, prompt: task }) });
    setBlocks(result.render_blocks || []);
    setMessage("DesigningAgent created a URL-informed implementation brief and project file gallery.");
  }

  async function runDebugAgent() {
    const result = await fetchJson(api.agenticVisualDebugRepairPlan, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ error_text: errorText, context: "Agent task execution" }) });
    setBlocks([result.render_block]);
    setMessage(`DebuggingAgent classified: ${result.root_cause}`);
  }

  const completed = useMemo(() => roadmap?.phases?.length || 0, [roadmap]);

  return (
    <div className="agentic-visual-shell">
      <header className="agentic-visual-hero">
        <div><p className="eyebrow">Agentic AGI Component</p><h2>Visual Agent workspace + DesigningAgent + DebuggingAgent v2</h2><p>{roadmap?.north_star || "Loading roadmap..."}</p></div>
        <div className="agentic-score"><strong>{completed}/10</strong><span>visual phases</span></div>
      </header>
      {message ? <div className="render-card-summary success">{message}</div> : null}
      <section className="agentic-phase-grid">{(roadmap?.phases || []).map((phase) => <article key={phase.id}><span>{phase.id}</span><strong>{phase.name}</strong><small>{phase.goal}</small></article>)}</section>
      <section className="agentic-two-col">
        <article className="agentic-control-card"><h3>Visual router</h3><textarea value={task} onChange={(e) => setTask(e.target.value)} rows={4} /><button onClick={buildRenderContract}>Generate visual contract</button></article>
        <article className="agentic-control-card"><h3>DesigningAgent from URL</h3><input value={url} onChange={(e) => setUrl(e.target.value)} /><button onClick={runDesignAgent}>Analyze URL + create roadmap</button></article>
        <article className="agentic-control-card"><h3>DebuggingAgent v2</h3><textarea value={errorText} onChange={(e) => setErrorText(e.target.value)} rows={4} /><button onClick={runDebugAgent}>Analyze error + repair plan</button></article>
        <article className="agentic-control-card"><h3>Agent panel state</h3><JsonDetails title="Active agents" data={panel || {}} /></article>
      </section>
      <section className="agentic-render-lab">{blocks.length ? blocks.map((block, idx) => <RenderBlock key={`${block.type}-${idx}`} block={block} />) : <p className="agentic-muted">Run the visual router, DesigningAgent, or DebuggingAgent to see task-specific components.</p>}</section>
      <JsonDetails title="Visual component registry" data={components || {}} />
    </div>
  );
}
