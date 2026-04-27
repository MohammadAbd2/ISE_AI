const COMPLETE_STATUSES = new Set(["done", "completed", "exported", "verified", "success", "ready"]);
const FAILED_STATUSES = new Set(["failed", "needs_repair", "error", "blocked"]);

export default function AgentStatusBar({ run }) {
  const events = Array.isArray(run?.events) ? run.events : [];
  const steps = Array.isArray(run?.steps) && run.steps.length
    ? run.steps
    : events.map((event, index) => ({
        id: event.id || `${event.agent}-${event.phase}-${index}`,
        status: event.status,
        required: true
      }));

  const required = steps.filter((step) => step.required !== false);
  const complete = required.filter((step) => COMPLETE_STATUSES.has(String(step.status || "").toLowerCase())).length;
  const failed = required.some((step) => FAILED_STATUSES.has(String(step.status || "").toLowerCase()));
  const running = required.some((step) => String(step.status || "").toLowerCase() === "running");
  const rawProgress = required.length ? Math.round((complete / required.length) * 100) : 0;
  const terminal = COMPLETE_STATUSES.has(String(run?.status || "").toLowerCase()) || Boolean(run?.artifact);
  const finalProgress = terminal ? 100 : failed ? rawProgress : running ? Math.max(1, Math.min(rawProgress, 99)) : rawProgress;
  const label = failed ? "Needs repair" : terminal ? "Ready" : running ? "Working" : (run?.status || "idle");

  return (
    <section className={`agent-status-bar ${failed ? "is-failed" : ""} ${terminal ? "is-ready" : ""}`}>
      <div>
        <strong>{run?.title || "Agent execution"}</strong>
        <span>{label} · {complete}/{required.length || 0} verified steps</span>
      </div>
      <div className="agent-progress-track" aria-label={`Progress ${finalProgress}%`}>
        <span style={{ width: `${finalProgress}%` }} />
      </div>
      <b>{finalProgress}%</b>
    </section>
  );
}
