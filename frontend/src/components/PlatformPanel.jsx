import { useEffect, useMemo, useState } from "react";
import { fetchJson } from "../lib/api";

function Timeline({ runs = [], previews = [], smoke }) {
  const items = useMemo(() => {
    const rows = [];
    runs.slice(0, 6).forEach((run, i) => rows.push({ time: `00:${String((i + 1) * 4).padStart(2, "0")}`, agent: "Trace", text: `${run.run_id} · ${run.last_status || "recorded"}`, status: run.last_status || "ok" }));
    previews.slice(0, 4).forEach((preview, i) => rows.push({ time: `00:${String(30 + i * 5).padStart(2, "0")}`, agent: "Preview", text: `${preview.status} · ${preview.url || "pending"}`, status: preview.status }));
    if (smoke) rows.push({ time: "00:45", agent: "Verifier", text: `Reliability smoke ${smoke.status}`, status: smoke.status });
    return rows.length ? rows : [{ time: "00:00", agent: "System", text: "No runs yet. Start a smoke test or autonomous project.", status: "idle" }];
  }, [runs, previews, smoke]);
  return <div className="devin-timeline">{items.map((item, idx) => <div className="devin-timeline-row" key={`${item.time}-${idx}`}><span>{item.time}</span><strong>{item.agent}</strong><p>{item.text}</p><em>{item.status}</em></div>)}</div>;
}

function PluginList({ plugins = [] }) {
  return <div className="plugin-grid">{plugins.map((p) => <article className="platform-mini-card" key={p.name}><strong>{p.name}</strong><span>{p.category}</span><p>{p.description}</p><em>{p.enabled ? "enabled" : "disabled"}</em></article>)}</div>;
}

export default function PlatformPanel() {
  const [traces, setTraces] = useState([]);
  const [previews, setPreviews] = useState([]);
  const [plugins, setPlugins] = useState([]);
  const [benchmarks, setBenchmarks] = useState([]);
  const [projects, setProjects] = useState([]);
  const [intelligence, setIntelligence] = useState(null);
  const [reasoning, setReasoning] = useState(null);
  const [knowledge, setKnowledge] = useState([]);
  const [deployTargets, setDeployTargets] = useState([]);
  const [smoke, setSmoke] = useState(null);
  const [plan, setPlan] = useState(null);
  const [task, setTask] = useState("Build a market shop landing page with React, verify it, preview it, and export a ZIP.");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function load() {
    try {
      const [traceData, previewData, pluginData, benchData, projectData, intelData, knowledgeData, deployData] = await Promise.all([
        fetchJson("/api/platform/traces").catch(() => ({ runs: [] })),
        fetchJson("/api/platform/preview").catch(() => ({ previews: [] })),
        fetchJson("/api/platform/plugins").catch(() => ({ plugins: [] })),
        fetchJson("/api/platform/benchmarks").catch(() => ({ cases: [] })),
        fetchJson("/api/platform/autonomous-project").catch(() => ({ runs: [] })),
        fetchJson("/api/platform/intelligence/summary").catch(() => null),
        fetchJson(`/api/platform/knowledge/search?q=${encodeURIComponent(task)}&limit=5`).catch(() => ({ items: [] })),
        fetchJson("/api/platform/deploy/targets").catch(() => ({ targets: [] })),
      ]);
      setTraces(traceData.runs || []);
      setPreviews(previewData.previews || []);
      setPlugins(pluginData.plugins || []);
      setBenchmarks(benchData.cases || []);
      setProjects(projectData.runs || []);
      setIntelligence(intelData);
      setKnowledge(knowledgeData.items || []);
      setDeployTargets(deployData.targets || []);
    } catch (err) { setError(err.message || "Could not load platform status"); }
  }
  async function runSmoke() {
    setLoading(true); setError("");
    try {
      const result = await fetchJson("/api/platform/reliability/react-smoke", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ task, session_id: "platform-panel" }) });
      setSmoke(result); await load();
    } catch (err) { setError(err.message || "Smoke test failed"); } finally { setLoading(false); }
  }
  async function makePlan() {
    setLoading(true); setError("");
    try {
      const [candidatePlan, reflective] = await Promise.all([
        fetchJson("/api/platform/planner/candidates", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ task }) }),
        fetchJson("/api/platform/reasoning/reflect", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ task, max_revisions: 3 }) }),
      ]);
      setPlan(candidatePlan);
      setReasoning(reflective);
    }
    catch (err) { setError(err.message || "Plan generation failed"); } finally { setLoading(false); }
  }
  async function startAutonomousProject() {
    setLoading(true); setError("");
    try { await fetchJson("/api/platform/autonomous-project", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ prompt: task }) }); await load(); }
    catch (err) { setError(err.message || "Could not start project mode"); } finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []);
  return (
    <section className="platform-panel devin-console">
      <div className="platform-panel-header">
        <div><p className="eyebrow">Autonomous developer platform</p><h2>Devin-style control center</h2><p>Security, planning, browser verification, previews, plugins, traces, and artifact reliability.</p></div>
        <div className="platform-actions"><button className="response-feedback-chip" onClick={load}>Refresh</button><button className="response-feedback-chip primary" disabled={loading} onClick={runSmoke}>Run smoke</button></div>
      </div>
      {error ? <div className="operation-error">{error}</div> : null}
      <div className="platform-command-row"><input value={task} onChange={(e) => setTask(e.target.value)} placeholder="Describe an autonomous project task" /><button onClick={makePlan}>Tree plan</button><button onClick={startAutonomousProject}>Start project mode</button></div>
      <div className="devin-layout">
        <article className="platform-card chat-panel"><strong>Live agent thinking</strong><div className="agent-thought"><span>🤖 Planner</span><p>{plan?.selected?.rationale || "Waiting for architecture decision."}</p></div><div className="agent-thought"><span>🛠 Builder</span><p>Writes files only through validated tool calls.</p></div><div className="agent-thought"><span>🔍 Debugger</span><p>Receives failed build/test/browser observations and retries with a different strategy.</p></div><div className="agent-thought"><span>📦 Exporter</span><p>Only shows download after ZIP hash, size, manifest, and file-count checks pass.</p></div></article>
        <article className="platform-card timeline-panel"><strong>Timeline</strong><Timeline runs={traces} previews={previews} smoke={smoke} /></article>
        <article className="platform-card preview-panel"><strong>Live preview</strong>{previews[0]?.url ? <iframe title="Generated app preview" src={previews[0].url} /> : <div className="preview-empty">No preview running yet. Start a generated app preview from the execution packet or platform API.</div>}</article>
      </div>

      <div className="platform-grid intelligence-dashboard">
        <article className="platform-card wide"><strong>Intelligence dashboard</strong>{intelligence ? <div className="platform-checks"><span className="artifact-chip available">Trace runs: {intelligence.trace_runs}</span><span className="artifact-chip available">Benchmark: {intelligence.benchmark_score ?? "n/a"}</span><span className="artifact-chip available">Success rate: {intelligence.success_rate ?? "learning"}</span>{(intelligence.top_risks || []).map((risk) => <p key={risk}>⚠️ {risk}</p>)}</div> : <p>Loading intelligence metrics…</p>}</article>
        <article className="platform-card"><strong>Reflective reasoning</strong>{reasoning?.revisions?.map((rev) => <div className="agent-thought" key={rev.id}><span>{rev.phase}</span><p>{rev.critique}</p><em>{rev.decision} · {Math.round((rev.confidence || 0) * 100)}%</em></div>) || <p>Run Tree plan to generate critique and revision steps.</p>}</article>
        <article className="platform-card"><strong>Persistent knowledge</strong>{knowledge.length ? knowledge.map((item) => <div className="platform-mini-card" key={item.id}><strong>{item.title}</strong><p>{item.content?.slice(0, 140)}</p><em>{item.source}</em></div>) : <p>No matching knowledge snippets yet.</p>}</article>
        <article className="platform-card"><strong>Deployment targets</strong>{deployTargets.map((target) => <div className="control-row" key={target.id}><code>{target.name}</code><span>{target.best_for}</span></div>)}</article>
      </div>
      <div className="platform-grid">
        <article className="platform-card"><strong>Autonomous project controls</strong>{projects.slice(0,3).map((p)=><div className="control-row" key={p.id}><code>{p.id.slice(0,8)}</code><span>{p.status}</span><button>Pause</button><button>Resume</button><button>Force export</button></div>)}{!projects.length ? <p>No project-mode runs yet.</p> : null}</article>
        <article className="platform-card"><strong>Plan candidates</strong>{plan?.candidates?.slice(0,3).map((c)=><div className="plan-candidate" key={c.id}><strong>{c.strategy}</strong><span>{c.score}/100</span><p>{c.rationale}</p></div>) || <p>Create a tree-of-thought plan to compare strategies.</p>}</article>
        <article className="platform-card wide"><strong>Plugin ecosystem</strong><PluginList plugins={plugins} /></article>
        <article className="platform-card wide"><strong>Benchmark suite</strong><div className="plugin-grid">{benchmarks.map((b)=><article className="platform-mini-card" key={b.id}><strong>{b.id}</strong><p>{b.prompt}</p><em>{b.expected_artifact}</em></article>)}</div></article>
        <article className="platform-card wide"><strong>Latest reliability smoke</strong>{smoke ? <div className="platform-checks"><p>Status: {smoke.status} · {smoke.elapsed_ms}ms</p>{(smoke.checks || []).map((check)=><span key={check.name} className={`artifact-chip ${check.status === "failed" ? "error" : "available"}`}>{check.name}: {check.status}</span>)}{smoke.download_url ? <a className="response-feedback-chip primary" href={smoke.download_url}>⬇ Download verified artifact</a> : null}</div> : <p>No smoke test run yet.</p>}</article>
      </div>
    </section>
  );
}
