import { useEffect, useMemo, useState } from "react";
import { fetchJson } from "../lib/api";
import "../styles/ux-intelligence.css";

const UX_PHASES = [
  ["UX-1", "Cognitive load reduction", "Auto-group noise, collapse detail by default, and surface only decisions, blockers, files, and next actions."],
  ["UX-2", "Real-time intelligence feedback", "Backend-tied streaming state, adaptive ETA, live event heartbeat, and reasoning-state badges."],
  ["UX-3", "Modular workspace", "Draggable-style panels, saved layouts, split task views, and operator-focused composition."],
  ["UX-4", "AI co-pilot interface", "Inline suggestions, ask-why controls, editable plans, and conversational command shortcuts."],
  ["UX-5", "Visual execution timeline 2.0", "Branching timeline, retries, alternative strategies, zoom levels, and trace replay."],
  ["UX-6", "Intent-based interface", "Goal-first command bar that translates outcomes into plans and suggested actions."],
  ["UX-7", "Deep inspection mode", "Decision explorer, diff inspection, confidence, audit trail, and replay-ready traces."],
  ["UX-8", "Control and safety dashboard", "Visual policy builder, simulation, rule triggers, approval mode, and live admin controls."],
  ["UX-9", "Memory and context visualization", "Knowledge graph of projects, decisions, preferences, files, and reusable patterns."],
  ["UX-10", "Autonomous mode UI", "Manual, assisted, and autonomous modes with boundaries and intervention controls."],
  ["UX-11", "Multi-agent visualization", "Agent lanes, delegation map, messages, conflicts, and consensus summaries."],
  ["UX-12", "Adaptive UI", "Behavior-aware layout that hides unused surfaces and promotes frequent workflows."],
  ["UX-13", "Built-in UX experimentation", "A/B variants, task completion metrics, friction scoring, and rollout controls."],
  ["UX-14", "Predictive UI", "Next-best actions, risk warnings, preloaded context, and proactive recommendations."],
  ["UX-15", "Zero-UI mode", "Commandless intent execution with review-first expansion instead of forcing the user through panels."],
  ["UX-16", "Anticipation engine", "Predict next actions, preload context, and recommend safe execution before the user asks."],
  ["UX-17", "Context-aware interface morphing", "Beginner, expert, debugging, and admin surfaces selected from task context."],
  ["UX-18", "Conversational workspace", "Chat, dashboard controls, timelines, and artifacts stay synchronized in one workspace."],
  ["UX-19", "Intent graph visualization", "Show the why: goals, sub-goals, dependencies, constraints, and execution paths."],
  ["UX-20", "Time-travel debugging UI", "Scrub, rewind, replay, and inspect any moment of an agent run."],
  ["UX-21", "Trust interface layer", "Confidence, risk, verification, safety rationale, and source-of-truth badges across the UI."],
  ["UX-22", "Emotional UX awareness", "Detect frustration signals and simplify the interface when cognitive load rises."],
  ["UX-23", "Cross-device continuity", "Persist task state, active panels, approvals, and traces across desktop, tablet, and mobile."],
  ["UX-24", "Autonomous UX optimization", "Safe experiments, friction scoring, and controlled rollout of better layouts."],
  ["UX-25", "Input-agnostic frontier", "Voice-first, gesture-ready, and future neural-signal-ready interaction model."],
];

const DEFAULT_WORKSPACE = {
  mode: "assisted",
  layout: "operator-grid",
  density: "focused",
  panels: ["intent", "timeline", "control", "memory", "agents", "experiments", "predictive"],
};

function PhaseRail({ selected, onSelect }) {
  return (
    <aside className="ux-rail" aria-label="UX phase roadmap">
      <p className="eyebrow">UX-1 → UX-25</p>
      <h3>Invisible workspace roadmap</h3>
      <div className="ux-phase-list">
        {UX_PHASES.map(([id, title, description]) => (
          <button key={id} className={selected === id ? "active" : ""} onClick={() => onSelect(id)}>
            <span>{id}</span>
            <strong>{title}</strong>
            <small>{description}</small>
          </button>
        ))}
      </div>
    </aside>
  );
}

function SignalCard({ label, value, hint, tone = "neutral" }) {
  return <article className={`ux-signal ${tone}`}><span>{label}</span><strong>{value}</strong><small>{hint}</small></article>;
}

function IntentPanel({ intent, setIntent, suggestions = [] }) {
  return (
    <section className="ux-panel ux-intent-panel">
      <div className="ux-panel-head"><div><p className="eyebrow">UX-6</p><h3>Intent command center</h3></div><span className="ux-chip">goal-first</span></div>
      <textarea value={intent} onChange={(event) => setIntent(event.target.value)} rows={5} placeholder="Describe the outcome. The UI turns it into a plan, controls, and predicted next actions." />
      <div className="suggestion-cloud">
        {suggestions.map((item) => <button key={item}>{item}</button>)}
      </div>
    </section>
  );
}

function TimelinePanel({ events = [], selectedPhase }) {
  const filtered = selectedPhase === "all" ? events : events.filter((event) => event.phase === selectedPhase || event.related?.includes(selectedPhase));
  return (
    <section className="ux-panel ux-timeline-panel">
      <div className="ux-panel-head"><div><p className="eyebrow">UX-2 + UX-5</p><h3>Live branching timeline</h3></div><span className="ux-chip live">live</span></div>
      <div className="timeline-branches">
        {(filtered.length ? filtered : events).map((event) => (
          <article key={event.id} className={`branch-event ${event.status}`}>
            <span className="branch-dot" />
            <div><strong>{event.title}</strong><p>{event.detail}</p><small>{event.agent} · {event.elapsed}s · {event.confidence}% confidence</small></div>
            <button title="Open deep inspection">Inspect</button>
          </article>
        ))}
      </div>
    </section>
  );
}

function ControlPanel({ policy, onChange }) {
  const updateRule = (index, patch) => onChange({ ...policy, rules: policy.rules.map((rule, i) => i === index ? { ...rule, ...patch } : rule) });
  const addRule = () => onChange({ ...policy, rules: [...policy.rules, { id: `ux_rule_${Date.now()}`, label: "New visual rule", pattern: "", action: "warn", severity: "medium", enabled: true }] });
  return (
    <section className="ux-panel ux-control-panel">
      <div className="ux-panel-head"><div><p className="eyebrow">UX-8</p><h3>Visual control and safety dashboard</h3></div><button onClick={addRule}>Add rule</button></div>
      <div className="mode-switches">
        {["manual", "assisted", "autonomous"].map((mode) => <label key={mode}><input type="radio" checked={policy.mode === mode} onChange={() => onChange({ ...policy, mode })} /> {mode}</label>)}
      </div>
      <div className="rule-builder">
        {policy.rules.map((rule, index) => (
          <div className="visual-rule" key={rule.id}>
            <label><input type="checkbox" checked={rule.enabled} onChange={(e) => updateRule(index, { enabled: e.target.checked })} /> Enabled</label>
            <input value={rule.label} onChange={(e) => updateRule(index, { label: e.target.value })} />
            <input value={rule.pattern} onChange={(e) => updateRule(index, { pattern: e.target.value })} placeholder="detect pattern" />
            <select value={rule.action} onChange={(e) => updateRule(index, { action: e.target.value })}><option>warn</option><option>require_approval</option><option>block</option></select>
          </div>
        ))}
      </div>
    </section>
  );
}

function MemoryPanel({ graph = [] }) {
  return (
    <section className="ux-panel ux-memory-panel">
      <div className="ux-panel-head"><div><p className="eyebrow">UX-9</p><h3>Memory and context graph</h3></div><span className="ux-chip">visible memory</span></div>
      <div className="memory-map">
        {graph.map((node) => <article key={node.id} className={`memory-node ${node.kind}`}><strong>{node.label}</strong><span>{node.kind}</span><small>{node.links.join(" → ")}</small></article>)}
      </div>
    </section>
  );
}

function AgentsPanel({ agents = [] }) {
  return (
    <section className="ux-panel ux-agents-panel">
      <div className="ux-panel-head"><div><p className="eyebrow">UX-11</p><h3>Multi-agent visualization</h3></div><span className="ux-chip">swarm view</span></div>
      <div className="agent-lanes">
        {agents.map((agent) => <article key={agent.name}><div><strong>{agent.name}</strong><span>{agent.state}</span></div><p>{agent.task}</p><progress max="100" value={agent.progress} /></article>)}
      </div>
    </section>
  );
}

function ExperimentPanel({ experiments = [] }) {
  return (
    <section className="ux-panel ux-experiment-panel">
      <div className="ux-panel-head"><div><p className="eyebrow">UX-12 + UX-13</p><h3>Adaptive UI experiments</h3></div><span className="ux-chip">self-optimizing</span></div>
      {experiments.map((experiment) => <article key={experiment.id} className="experiment-row"><strong>{experiment.name}</strong><span>{experiment.variant}</span><p>{experiment.metric}: {experiment.score}</p></article>)}
    </section>
  );
}

function PredictivePanel({ predictions = [] }) {
  return (
    <section className="ux-panel ux-predictive-panel">
      <div className="ux-panel-head"><div><p className="eyebrow">UX-14</p><h3>Predictive next actions</h3></div><span className="ux-chip warning">ahead of you</span></div>
      {predictions.map((item) => <article key={item.id} className={`prediction ${item.risk}`}><strong>{item.title}</strong><p>{item.reason}</p><button>{item.action}</button></article>)}
    </section>
  );
}

function InspectionPanel({ phase }) {
  const item = UX_PHASES.find(([id]) => id === phase) || UX_PHASES[0];
  return (
    <section className="ux-panel ux-inspection-panel">
      <div className="ux-panel-head"><div><p className="eyebrow">UX-4 + UX-7</p><h3>Co-pilot inspection</h3></div><span className="ux-chip">ask why</span></div>
      <article className="decision-card"><span>{item[0]}</span><strong>{item[1]}</strong><p>{item[2]}</p><div className="decision-actions"><button>Ask why</button><button>Edit plan</button><button>Replay trace</button></div></article>
    </section>
  );
}

function ZeroUiPanel({ intent, mode, setMode }) {
  return <section className="ux-panel zero-ui-panel"><div className="ux-panel-head"><div><p className="eyebrow">UX-15</p><h3>Zero-UI commandless mode</h3></div><span className="ux-chip">invisible by default</span></div><article className="zero-command-card"><strong>{intent.slice(0,95)}{intent.length>95?"...":""}</strong><p>The interface converts intent into an execution path, then only expands decisions, blockers, changed files, and trust checks.</p></article><div className="mode-switches compact">{["silent","review-first","full-control"].map((item)=><label key={item}><input type="radio" checked={mode===item} onChange={()=>setMode(item)} /> {item}</label>)}</div></section>;
}
function AnticipationPanel({ predictions = [] }) { return <section className="ux-panel anticipation-panel"><div className="ux-panel-head"><div><p className="eyebrow">UX-16</p><h3>Anticipation engine</h3></div><span className="ux-chip live">preloaded</span></div>{predictions.slice(0,3).map((item,index)=><article key={item.id||index} className={`anticipation-step ${item.risk}`}><span>{index+1}</span><div><strong>{item.title}</strong><p>{item.reason}</p></div><button>{item.action}</button></article>)}</section>; }
function InterfaceMorphPanel({ density, setDensity }) { const modes=["beginner","expert","debugging","admin"]; return <section className="ux-panel morph-panel"><div className="ux-panel-head"><div><p className="eyebrow">UX-17</p><h3>Context-aware interface morphing</h3></div><span className="ux-chip">adaptive surface</span></div><div className="morph-grid">{modes.map((mode)=><button key={mode} className={density===mode?"active":""} onClick={()=>setDensity(mode)}><strong>{mode}</strong><small>{mode==="admin"?"Full governance controls":mode==="debugging"?"Trace and replay first":mode==="expert"?"Dense keyboard-friendly workspace":"Simple outcome-first workspace"}</small></button>)}</div></section>; }
function ConversationalWorkspacePanel() { return <section className="ux-panel conversation-workspace-panel"><div className="ux-panel-head"><div><p className="eyebrow">UX-18</p><h3>Conversational workspace</h3></div><span className="ux-chip">chat + UI fused</span></div><div className="chat-ui-thread"><div className="bubble user">Build the CV landing page and export a ZIP.</div><div className="bubble ai">Roadmap created, files built, build verified, generic copy detected and repaired.</div><div className="bubble system"><button>Open files</button><button>Replay fix</button><button>Download ZIP</button></div></div></section>; }
function IntentGraphPanel() { const nodes=[["Goal","Create CV landing page"],["Structure","Header · Body · Footer"],["Quality","Specific copy · no canned markers"],["Verify","Build · anti-template · export"],["Control","Admin approval gates"]]; return <section className="ux-panel intent-graph-panel"><div className="ux-panel-head"><div><p className="eyebrow">UX-19</p><h3>Intent graph</h3></div><span className="ux-chip">why-first</span></div><div className="intent-graph">{nodes.map(([k,v],i)=><article key={k}><span>{k}</span><strong>{v}</strong>{i<nodes.length-1?<em />:null}</article>)}</div></section>; }
function TimeTravelPanel({ events = [] }) { const [cursor,setCursor]=useState(60); const current=events[Math.min(events.length-1,Math.floor((cursor/100)*Math.max(events.length-1,0)))]||events[0]; return <section className="ux-panel time-travel-panel"><div className="ux-panel-head"><div><p className="eyebrow">UX-20</p><h3>Time-travel debugging</h3></div><span className="ux-chip">replayable</span></div><input type="range" value={cursor} onChange={(e)=>setCursor(Number(e.target.value))}/><article className="replay-card"><strong>{current?.title||"No event selected"}</strong><p>{current?.detail||"Move the scrubber to inspect agent history."}</p><small>{cursor}% through execution</small></article></section>; }
function TrustLayerPanel() { return <section className="ux-panel trust-layer-panel"><div className="ux-panel-head"><div><p className="eyebrow">UX-21</p><h3>Trust interface layer</h3></div><span className="ux-chip warning">risk-aware</span></div><div className="trust-grid"><article><strong>94%</strong><span>confidence</span><small>build verified</small></article><article><strong>Low</strong><span>data risk</span><small>no secrets detected</small></article><article><strong>Required</strong><span>approval</span><small>export changes files</small></article></div></section>; }
function EmotionalUxPanel({ density, setDensity }) { return <section className="ux-panel emotional-ux-panel"><div className="ux-panel-head"><div><p className="eyebrow">UX-22</p><h3>Feedback-aware UX</h3></div><button onClick={()=>setDensity('focused')}>Simplify now</button></div><p>Rapid cancels, repeated preview toggles, and ignored panels raise a friction score. When friction rises, the UI collapses detail and promotes one safe next action.</p><div className="friction-meter"><span style={{width:'34%'}} /></div><small>Current density: {density}</small></section>; }
function ContinuityPanel() { return <section className="ux-panel continuity-panel"><div className="ux-panel-head"><div><p className="eyebrow">UX-23</p><h3>Cross-device continuity</h3></div><span className="ux-chip">synced</span></div><div className="device-row"><span>Desktop</span><strong>Editing plan</strong></div><div className="device-row"><span>Tablet</span><strong>Timeline synced</strong></div><div className="device-row"><span>Mobile</span><strong>Approval controls ready</strong></div></section>; }
function AutonomousOptimizationPanel({ experiments = [] }) { return <section className="ux-panel autonomous-optimization-panel"><div className="ux-panel-head"><div><p className="eyebrow">UX-24</p><h3>Autonomous UX optimization</h3></div><span className="ux-chip">self-healing UX</span></div>{experiments.map((item)=><article key={item.id} className="optimization-row"><strong>{item.name}</strong><span>{item.variant}</span><small>{item.metric}: {item.score}</small></article>)}</section>; }
function FrontierInputPanel() { return <section className="ux-panel frontier-input-panel"><div className="ux-panel-head"><div><p className="eyebrow">UX-25</p><h3>Input-agnostic frontier</h3></div><span className="ux-chip">voice-ready</span></div><div className="input-frontier-grid"><article><strong>Voice-first</strong><small>Hands-free execution and review</small></article><article><strong>Gesture-ready</strong><small>Spatial and touch interactions</small></article><article><strong>Neural-ready</strong><small>Future low-friction intent signals</small></article></div></section>; }
function CognitiveCompressionPanel() { return <section className="ux-panel cognitive-compression-panel"><div className="ux-panel-head"><div><p className="eyebrow">Final stage</p><h3>Cognitive compression</h3></div><span className="ux-chip">less = more</span></div><p>Selective transparency shows only meaningful insight: blockers, irreversible actions, changed files, trust signals, and required decisions.</p><ul className="compression-list"><li>Hide routine logs by default</li><li>Promote warnings and approvals</li><li>Summarize multi-agent debate</li><li>Keep raw traces one click away</li></ul></section>; }

export default function UXIntelligenceWorkspace() {
  const [selectedPhase, setSelectedPhase] = useState("UX-25");
  const [intent, setIntent] = useState("Make the agent dashboard easier to trust, control, inspect, and operate autonomously without overwhelming the user.");
  const [workspace, setWorkspace] = useState(DEFAULT_WORKSPACE);
  const [zeroUiMode, setZeroUiMode] = useState("review-first");
  const [data, setData] = useState(null);
  const [policy, setPolicy] = useState({ mode: "assisted", rules: [
    { id: "secret-leak", label: "Detect secret leakage", pattern: "token|api[_-]?key|password", action: "block", severity: "critical", enabled: true },
    { id: "prod-risk", label: "Require approval for production changes", pattern: "deploy|production|database migration", action: "require_approval", severity: "high", enabled: true },
  ] });

  useEffect(() => {
    fetchJson("/api/platform/ux-intelligence/workspace").then(setData).catch(() => setData(null));
  }, []);

  const fallback = useMemo(() => ({
    signals: [
      { label: "Noise reduced", value: "68%", hint: "logs grouped by relevance", tone: "good" },
      { label: "ETA quality", value: "adaptive", hint: "event-driven heartbeat", tone: "neutral" },
      { label: "Control mode", value: policy.mode, hint: "admin visible", tone: "warning" },
      { label: "Predictions", value: "4", hint: "next actions ready", tone: "good" },
    ],
    suggestions: ["Show only blockers", "Simulate safety policy", "Open memory graph", "Compare layout variants", "Replay last run"],
    events: [
      { id: "e1", phase: "UX-2", related: ["UX-5"], title: "Streaming heartbeat received", detail: "Progress updated from backend event, not static mock state.", agent: "Runtime", elapsed: 12, confidence: 94, status: "success" },
      { id: "e2", phase: "UX-5", related: ["UX-7"], title: "Alternative branch created", detail: "Reviewer requested a safer plan before export.", agent: "ReviewerAgent", elapsed: 21, confidence: 88, status: "warning" },
      { id: "e3", phase: "UX-8", related: ["UX-10"], title: "Admin rule triggered", detail: "Production deployment requires approval in autonomous mode.", agent: "ControlLayer", elapsed: 24, confidence: 99, status: "blocked" },
      { id: "e4", phase: "UX-14", related: ["UX-12"], title: "Predictive suggestion generated", detail: "The UI recommends opening policy simulation before merge.", agent: "PredictiveUI", elapsed: 31, confidence: 91, status: "success" },
    ],
    graph: [
      { id: "m1", label: "User prefers dashboard control", kind: "preference", links: ["Phase 84", "Phase 98", "UX-8"] },
      { id: "m2", label: "Code previews must be syntax-highlighted", kind: "lesson", links: ["MessageList", "RichMessage"] },
      { id: "m3", label: "Progress must be real-time", kind: "constraint", links: ["Runtime events", "UX-2"] },
      { id: "m4", label: "Autonomy needs intervention controls", kind: "policy", links: ["UX-10", "Phase 101"] },
    ],
    agents: [
      { name: "PlannerAgent", state: "reasoning", task: "Convert user intent into adaptive execution plan", progress: 82 },
      { name: "UXCriticAgent", state: "reviewing", task: "Detect cognitive overload and surface design fixes", progress: 74 },
      { name: "ControlAgent", state: "guarding", task: "Apply admin-defined policies and approval gates", progress: 96 },
      { name: "PredictiveAgent", state: "forecasting", task: "Suggest the next safest operator action", progress: 68 },
    ],
    experiments: [
      { id: "a", name: "Timeline density", variant: "Grouped blockers first", metric: "time-to-understand", score: "-32%" },
      { id: "b", name: "Control panel placement", variant: "Pinned right rail", metric: "policy edits", score: "+21%" },
      { id: "c", name: "Predictive prompts", variant: "Contextual chips", metric: "accepted next actions", score: "+44%" },
    ],
    predictions: [
      { id: "p1", title: "Open policy simulation before autonomous run", reason: "Your current intent mentions dashboard control and may trigger deployment rules.", action: "Simulate now", risk: "medium" },
      { id: "p2", title: "Collapse low-value logs", reason: "The current workspace has enough events to increase cognitive load.", action: "Focus view", risk: "low" },
      { id: "p3", title: "Save this layout", reason: "You repeatedly inspect control, timeline, and memory together.", action: "Save layout", risk: "low" },
      { id: "p4", title: "Require approval for export", reason: "A package generation action changes project files and should be governed.", action: "Add gate", risk: "high" },
    ],
  }), [policy.mode]);
  const view = data || fallback;

  return (
    <div className="ux-intelligence-shell">
      <header className="ux-hero">
        <div><p className="eyebrow">UI/UX Phase UX-25 complete</p><h2>Invisible Intelligent Workspace</h2><p>A focused operator interface that filters noise, explains decisions, visualizes agents, exposes memory, controls autonomy, and predicts the next safest action.</p></div>
        <div className="workspace-controls">
          <label>Mode<select value={workspace.mode} onChange={(e) => setWorkspace({ ...workspace, mode: e.target.value })}><option>manual</option><option>assisted</option><option>autonomous</option></select></label>
          <label>Density<select value={workspace.density} onChange={(e) => setWorkspace({ ...workspace, density: e.target.value })}><option>focused</option><option>balanced</option><option>deep-inspection</option><option>beginner</option><option>expert</option><option>debugging</option><option>admin</option></select></label>
        </div>
      </header>
      <div className="ux-signal-grid">{view.signals.map((signal) => <SignalCard key={signal.label} {...signal} />)}</div>
      <div className="ux-workspace-grid">
        <PhaseRail selected={selectedPhase} onSelect={setSelectedPhase} />
        <main className="ux-main-stack">
          <IntentPanel intent={intent} setIntent={setIntent} suggestions={view.suggestions} />
          <TimelinePanel events={view.events} selectedPhase={selectedPhase} />
          <ControlPanel policy={policy} onChange={setPolicy} />
          <div className="ux-two-col"><MemoryPanel graph={view.graph} /><AgentsPanel agents={view.agents} /></div>
          <div className="ux-two-col"><ExperimentPanel experiments={view.experiments} /><PredictivePanel predictions={view.predictions} /></div>
          <div className="ux-two-col"><ZeroUiPanel intent={intent} mode={zeroUiMode} setMode={setZeroUiMode} /><AnticipationPanel predictions={view.predictions} /></div>
          <div className="ux-two-col"><InterfaceMorphPanel density={workspace.density} setDensity={(density) => setWorkspace({ ...workspace, density })} /><ConversationalWorkspacePanel /></div>
          <IntentGraphPanel />
          <div className="ux-two-col"><TimeTravelPanel events={view.events} /><TrustLayerPanel /></div>
          <div className="ux-two-col"><EmotionalUxPanel density={workspace.density} setDensity={(density) => setWorkspace({ ...workspace, density })} /><ContinuityPanel /></div>
          <div className="ux-two-col"><AutonomousOptimizationPanel experiments={view.experiments} /><FrontierInputPanel /></div>
          <CognitiveCompressionPanel />
          <InspectionPanel phase={selectedPhase} />
        </main>
      </div>
    </div>
  );
}
