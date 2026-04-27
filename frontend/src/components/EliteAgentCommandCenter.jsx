import { useEffect, useMemo, useState } from "react";
import { fetchJson } from "../lib/api";
import AgentRunCard from "./agent/AgentRunCard";
import AdminControlDashboard from "./agent/AdminControlDashboard";
import "../styles/elite-agent.css";
import "../styles/real-intelligence-v2.css";

export default function EliteAgentCommandCenter() {
  const [roadmap, setRoadmap] = useState(null);
  const [lifecycle, setLifecycle] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let mounted = true;
    Promise.all([
      fetchJson("/api/real-intelligence-v2/roadmap").catch((err) => ({ error: err.message })),
      fetchJson("/api/real-intelligence-v2/lifecycle").catch((err) => ({ error: err.message })),
    ]).then(([nextRoadmap, nextLifecycle]) => {
      if (!mounted) return;
      if (nextRoadmap?.error || nextLifecycle?.error) setError(nextRoadmap?.error || nextLifecycle?.error);
      setRoadmap(nextRoadmap?.phases ? nextRoadmap : null);
      setLifecycle(nextLifecycle?.steps ? nextLifecycle : null);
    });
    return () => { mounted = false; };
  }, []);

  const demoRun = useMemo(() => ({
    title: "Real Intelligence System v2",
    status: "ready",
    steps: (lifecycle?.steps || []).map((step, index) => ({ ...step, status: index < 2 ? "done" : "pending" })),
    events: lifecycle?.events || [],
    files: [
      { path: "backend/app/services/real_intelligence_v2.py", status: "created", reason: "A-J backend contracts" },
      { path: "frontend/src/components/agent/*", status: "created", reason: "agent UI component rewrite" },
      { path: "frontend/src/styles/real-intelligence-v2.css", status: "created", reason: "clean execution UI" },
    ],
  }), [lifecycle]);

  const phases = roadmap?.phases || [];
  return (
    <section className="elite-agent-command-center real-intelligence-shell">
      <div className="elite-hero">
        <div>
          <p className="eyebrow">Real Intelligence System v2</p>
          <h3>Truthful execution, exact repair, verified export</h3>
          <p>No fake 95% progress, no unrelated file repair, no raw metadata dumps, and no export before integrity checks.</p>
        </div>
        <div className="elite-health"><strong>{error ? "Degraded" : "Ready"}</strong><span>{phases.length} implemented phases</span></div>
      </div>
      {error ? <div className="elite-error">Backend endpoint unavailable: {error}</div> : null}
      <AgentRunCard run={demoRun} />
      <AdminControlDashboard />
      <div className="elite-phase-grid">
        {phases.map((phase) => <article className="elite-phase-card" key={phase.id}><header><span>{phase.id}</span><strong>{phase.title}</strong></header><p>{phase.goal}</p><small>{phase.status}</small></article>)}
      </div>
    </section>
  );
}
