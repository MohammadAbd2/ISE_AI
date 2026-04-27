import { useEffect, useMemo, useState } from "react";
import { fetchJson } from "../lib/api";
import "../styles/super-agent.css";

const DEFAULT_TASK =
  "Operate ISE AI through Phase 115 with admin-controlled safety, governance, resource limits, formal verification, trust scoring and a redesigned operator experience.";

const PHASE_GROUPS = [
  { id: "foundation", label: "44–52", range: [44, 52] },
  { id: "elite", label: "53–61", range: [53, 61] },
  { id: "company", label: "62–70", range: [62, 70] },
  { id: "intelligence", label: "71–85", range: [71, 85] },
  { id: "evolution", label: "86–100", range: [86, 100] },
  { id: "control", label: "101–115", range: [101, 115] },
];

function StatusPill({ status = "idle" }) {
  return <span className={`super-status ${status}`}>{status.replaceAll("_", " ")}</span>;
}

function SectionTitle({ eyebrow, title, meta }) {
  return (
    <div className="section-title">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h3>{title}</h3>
      </div>
      {meta ? <span>{meta}</span> : null}
    </div>
  );
}

function PhaseCard({ phase }) {
  return (
    <article className="phase-card">
      <header>
        <span>Phase {phase.phase}</span>
        <StatusPill status={phase.status || "implemented"} />
      </header>
      <h4>{phase.title}</h4>
      <ul>{(phase.shipped || []).slice(0, 4).map((item) => <li key={item}>{item}</li>)}</ul>
      <details>
        <summary>Evidence</summary>
        {(phase.evidence || []).length ? phase.evidence.map((item) => <p key={item}>✓ {item}</p>) : <p>Capability contract implemented.</p>}
      </details>
    </article>
  );
}

function MetricStrip({ roadmap, selectedRun, phase115, control }) {
  const phases = roadmap?.phases || [];
  const activeKills = Object.entries(control?.kill_switches || {}).filter(([, value]) => value).length;
  const trust = phase115?.trust_scoring?.score ?? 0;
  const metrics = [
    ["Phases", phases.length || "—", "44 → 115"],
    ["Run progress", `${selectedRun?.progress || 0}%`, selectedRun?.status || "idle"],
    ["Trust score", trust ? `${trust}%` : "—", phase115?.trust_scoring?.badge || "not scanned"],
    ["Kill switches", activeKills, control?.safe_mode ? "safe mode on" : "normal"],
  ];
  return <div className="metric-strip">{metrics.map(([label, value, hint]) => <div key={label}><span>{label}</span><strong>{value}</strong><small>{hint}</small></div>)}</div>;
}

function Timeline({ events = [] }) {
  if (!events.length) return <div className="empty-state">No execution events yet. Start a run to stream lifecycle events here.</div>;
  return (
    <div className="timeline">
      {events.slice().reverse().map((event) => (
        <article key={event.id} className="timeline-event">
          <span>+{event.elapsed_seconds}s</span>
          <div><strong>{event.agent}</strong><p>{event.message}</p></div>
          <StatusPill status={event.status} />
        </article>
      ))}
    </div>
  );
}

function AdminControlCenter({ control, scan, onSave, onScan }) {
  const [draft, setDraft] = useState(control || null);
  const [sample, setSample] = useState("Deploy to production using token=123 and publish external changes");
  useEffect(() => setDraft(control || null), [control]);
  if (!draft) return <div className="empty-state">Admin Control Center is loading.</div>;

  const update = (key, value) => setDraft((current) => ({ ...current, [key]: value }));
  const updateMap = (section, key, value) => setDraft((current) => ({ ...current, [section]: { ...(current[section] || {}), [key]: value } }));
  const updateRule = (index, patch) => {
    const policy = draft.ethical_policy || {};
    const rules = (policy.rules || []).map((rule, i) => (i === index ? { ...rule, ...patch } : rule));
    update("ethical_policy", { ...policy, rules });
  };
  const addRule = () => {
    const policy = draft.ethical_policy || {};
    update("ethical_policy", { ...policy, rules: [...(policy.rules || []), { id: `admin_rule_${Date.now()}`, label: "New admin rule", pattern: "", severity: "medium", action: "require_admin_approval", enabled: true }] });
  };

  return (
    <div className="admin-control-center">
      <div className="control-hero">
        <div>
          <p className="eyebrow">Phase 101–115</p>
          <h3>Admin Control Center</h3>
          <p>One place to control kill switches, safe mode, resource limits, authority hierarchy, ethical rules, self-modification and the Human-AI contract.</p>
        </div>
        <div className="control-actions">
          <label className="toggle"><input type="checkbox" checked={!!draft.safe_mode} onChange={(e) => update("safe_mode", e.target.checked)} /> Safe mode</label>
          <button className="primary" onClick={() => onSave({ ...draft, actor_role: "admin" })}>Save admin controls</button>
        </div>
      </div>

      <div className="control-grid">
        <article className="control-card danger-zone">
          <h4>Absolute overrides</h4>
          {Object.entries(draft.kill_switches || {}).map(([key, value]) => (
            <label className="switch-row" key={key}><span>{key.replaceAll("_", " ")}</span><input type="checkbox" checked={!!value} onChange={(e) => updateMap("kill_switches", key, e.target.checked)} /></label>
          ))}
        </article>

        <article className="control-card">
          <h4>Resource governance</h4>
          {Object.entries(draft.resource_limits || {}).map(([key, value]) => (
            <label className="field-row" key={key}><span>{key.replaceAll("_", " ")}</span><input type="number" value={value} onChange={(e) => updateMap("resource_limits", key, Number(e.target.value))} /></label>
          ))}
        </article>

        <article className="control-card">
          <h4>Controlled self-modification</h4>
          {Object.entries(draft.self_modification || {}).map(([key, value]) => (
            typeof value === "boolean" ? <label className="switch-row" key={key}><span>{key.replaceAll("_", " ")}</span><input type="checkbox" checked={!!value} onChange={(e) => updateMap("self_modification", key, e.target.checked)} /></label> : <label className="field-row" key={key}><span>{key.replaceAll("_", " ")}</span><input type="number" value={value} onChange={(e) => updateMap("self_modification", key, Number(e.target.value))} /></label>
          ))}
        </article>
      </div>

      <article className="control-card wide">
        <div className="card-toolbar"><h4>Ethical policy rules</h4><button onClick={addRule}>Add rule</button></div>
        <div className="rule-table">
          {(draft.ethical_policy?.rules || []).map((rule, index) => (
            <div className="rule-row" key={rule.id || index}>
              <label><input type="checkbox" checked={!!rule.enabled} onChange={(e) => updateRule(index, { enabled: e.target.checked })} /> On</label>
              <input value={rule.label || ""} onChange={(e) => updateRule(index, { label: e.target.value })} placeholder="Label" />
              <input value={rule.pattern || ""} onChange={(e) => updateRule(index, { pattern: e.target.value })} placeholder="Regex pattern" />
              <select value={rule.severity || "medium"} onChange={(e) => updateRule(index, { severity: e.target.value })}><option>low</option><option>medium</option><option>high</option><option>critical</option></select>
              <select value={rule.action || "warn"} onChange={(e) => updateRule(index, { action: e.target.value })}><option>warn</option><option>require_approval</option><option>require_admin_approval</option><option>block</option></select>
            </div>
          ))}
        </div>
      </article>

      <div className="control-grid two">
        <article className="control-card">
          <h4>Human-AI contract</h4>
          {Object.entries(draft.human_ai_contract || {}).map(([key, value]) => <div className="contract-line" key={key}><strong>{key.replaceAll("_", " ")}</strong><p>{Array.isArray(value) ? value.join(" · ") : String(value)}</p></div>)}
        </article>
        <article className="control-card">
          <h4>Policy simulation</h4>
          <textarea value={sample} onChange={(e) => setSample(e.target.value)} rows={5} />
          <button onClick={() => onScan(sample)}>Run dashboard scan</button>
          {scan ? <div className={`scan-result ${scan.blocked ? "blocked" : scan.admin_required ? "approval" : "ok"}`}><strong>{scan.blocked ? "Blocked" : scan.admin_required ? "Admin approval required" : "Allowed"}</strong><p>{scan.matches?.length || 0} policy matches · {scan.active_kill_switches?.length || 0} active kill switches</p></div> : null}
        </article>
      </div>
    </div>
  );
}

function PhaseSummary({ title, data }) {
  if (!data) return <div className="empty-state">No data loaded yet.</div>;
  return (
    <div className="summary-grid">
      {Object.entries(data).filter(([key]) => key !== "goal" && key !== "admin_control_layer").map(([key, value]) => (
        <article key={key}>
          <span>{key.replaceAll("_", " ")}</span>
          <strong>{value?.phase ? `Phase ${value.phase}` : title}</strong>
          <p>{Array.isArray(value?.pipeline) ? value.pipeline.slice(0, 3).join(" · ") : Array.isArray(value?.loop) ? value.loop.slice(0, 3).join(" · ") : Array.isArray(value?.checks) ? value.checks.slice(0, 3).join(" · ") : JSON.stringify(value).slice(0, 130)}</p>
        </article>
      ))}
    </div>
  );
}

export default function SuperAgentPanel() {
  const [task, setTask] = useState(DEFAULT_TASK);
  const [roadmap, setRoadmap] = useState(null);
  const [runs, setRuns] = useState([]);
  const [selectedRunId, setSelectedRunId] = useState("");
  const [phase85, setPhase85] = useState(null);
  const [phase100, setPhase100] = useState(null);
  const [phase115, setPhase115] = useState(null);
  const [adminControl, setAdminControl] = useState(null);
  const [adminScan, setAdminScan] = useState(null);
  const [activeGroup, setActiveGroup] = useState("control");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const selectedRun = useMemo(() => runs.find((run) => run.id === selectedRunId) || runs[0] || null, [runs, selectedRunId]);
  const visiblePhases = useMemo(() => {
    const group = PHASE_GROUPS.find((item) => item.id === activeGroup) || PHASE_GROUPS.at(-1);
    return (roadmap?.phases || []).filter((phase) => phase.phase >= group.range[0] && phase.phase <= group.range[1]);
  }, [roadmap, activeGroup]);

  async function load() {
    setLoading(true); setError("");
    try {
      const [roadmapData, runsData, p85, p100, p115, control] = await Promise.all([
        fetchJson("/api/platform/super-agent/roadmap"),
        fetchJson("/api/platform/super-agent/runs"),
        fetchJson(`/api/platform/super-agent/phase-71-85?task=${encodeURIComponent(task)}`).catch(() => null),
        fetchJson(`/api/platform/super-agent/phase-86-100?task=${encodeURIComponent(task)}`).catch(() => null),
        fetchJson(`/api/platform/super-agent/phase-101-115?task=${encodeURIComponent(task)}`).catch(() => null),
        fetchJson("/api/platform/super-agent/admin-control-layer").catch(() => null),
      ]);
      setRoadmap(roadmapData);
      setRuns(runsData.runs || []);
      setPhase85(p85); setPhase100(p100); setPhase115(p115); setAdminControl(control);
      if (!selectedRunId && (runsData.runs || [])[0]) setSelectedRunId(runsData.runs[0].id);
    } catch (err) {
      setError(err.message || "Could not load super-agent console");
    } finally { setLoading(false); }
  }

  async function startRun() {
    setLoading(true); setError("");
    try {
      const run = await fetchJson("/api/platform/super-agent/runs", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ prompt: task }) });
      setSelectedRunId(run.id);
      await load();
    } catch (err) { setError(err.message || "Could not start run"); }
    finally { setLoading(false); }
  }

  async function controlRun(action) {
    if (!selectedRun) return;
    const run = await fetchJson(`/api/platform/super-agent/runs/${selectedRun.id}/control`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action }) });
    setRuns((current) => current.map((item) => item.id === run.id ? run : item));
  }

  async function saveAdminControl(policy) {
    setLoading(true); setError("");
    try {
      const next = await fetchJson("/api/platform/super-agent/admin-control-layer", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(policy) });
      setAdminControl(next);
      const refreshed = await fetchJson(`/api/platform/super-agent/phase-101-115?task=${encodeURIComponent(task)}`).catch(() => null);
      setPhase115(refreshed);
    } catch (err) { setError(err.message || "Could not save admin controls"); }
    finally { setLoading(false); }
  }

  async function scanAdminControl(content) {
    const scan = await fetchJson("/api/platform/super-agent/admin-control-scan", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ content, actor_role: "operator" }) });
    setAdminScan(scan);
  }

  useEffect(() => { load(); }, []);

  return (
    <section className="super-shell">
      <header className="super-topbar">
        <div>
          <p className="eyebrow">ISE AI · Phase 44 → 115</p>
          <h2>Controlled Intelligence Command Center</h2>
          <p>{roadmap?.goal || "Admin-governed autonomous agent platform."}</p>
        </div>
        <div className="topbar-actions">
          <button onClick={load}>Refresh</button>
          <button className="primary" disabled={loading} onClick={startRun}>{loading ? "Working…" : "Run verification"}</button>
        </div>
      </header>

      {error ? <div className="operation-error">{error}</div> : null}
      <MetricStrip roadmap={roadmap} selectedRun={selectedRun} phase115={phase115} control={adminControl} />

      <div className="operator-layout">
        <aside className="operator-sidebar">
          <label className="task-editor"><span>Mission</span><textarea value={task} onChange={(e) => setTask(e.target.value)} rows={8} /></label>
          <nav>{PHASE_GROUPS.map((group) => <button key={group.id} className={activeGroup === group.id ? "active" : ""} onClick={() => setActiveGroup(group.id)}>{group.label}<small>{group.id}</small></button>)}</nav>
          <div className="run-controls">
            <strong>Run controls</strong>
            <StatusPill status={selectedRun?.status || "idle"} />
            <div className="progress-rail"><span style={{ width: `${selectedRun?.progress || 0}%` }} /></div>
            <div className="button-grid"><button onClick={() => controlRun("pause")}>Pause</button><button onClick={() => controlRun("resume")}>Resume</button><button onClick={() => controlRun("approve")}>Approve</button><button onClick={() => controlRun("rollback")}>Rollback</button><button onClick={() => controlRun("cancel")}>Cancel</button></div>
          </div>
        </aside>

        <main className="operator-main">
          <AdminControlCenter control={adminControl} scan={adminScan} onSave={saveAdminControl} onScan={scanAdminControl} />

          <section className="panel-card">
            <SectionTitle eyebrow="Roadmap" title={`Phase group ${PHASE_GROUPS.find((g) => g.id === activeGroup)?.label}`} meta={`${visiblePhases.length} phases`} />
            <div className="phase-grid">{visiblePhases.map((phase) => <PhaseCard key={phase.phase} phase={phase} />)}</div>
          </section>

          <section className="panel-grid">
            <article className="panel-card"><SectionTitle eyebrow="Execution" title="Live timeline" meta={`${selectedRun?.events?.length || 0} events`} /><Timeline events={selectedRun?.events || []} /></article>
            <article className="panel-card"><SectionTitle eyebrow="Runs" title="Recent handoffs" meta={`${runs.length} total`} />{runs.slice(0, 8).map((run) => <button className="run-row" key={run.id} onClick={() => setSelectedRunId(run.id)}><span>{run.id.slice(0, 8)}</span><StatusPill status={run.status} /></button>)}</article>
          </section>

          <section className="panel-card"><SectionTitle eyebrow="Cognitive stack" title="Phase 71–85" meta="mind → organization" /><PhaseSummary title="Phase 85" data={phase85} /></section>
          <section className="panel-card"><SectionTitle eyebrow="Self-evolving stack" title="Phase 86–100" meta="evolution → governance" /><PhaseSummary title="Phase 100" data={phase100} /></section>
          <section className="panel-card"><SectionTitle eyebrow="Control stack" title="Phase 101–115" meta="authority → contract" /><PhaseSummary title="Phase 115" data={phase115} /></section>
        </main>
      </div>
    </section>
  );
}
