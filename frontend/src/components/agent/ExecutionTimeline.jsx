export default function ExecutionTimeline({ steps = [] }) {
  return <ol className="execution-timeline-v2">{steps.map((step, index) => <li key={step.id || index} className={`timeline-step is-${step.status || "pending"}`}><span className="step-index">{index + 1}</span><div><strong>{step.title}</strong><p>{step.goal || step.detail}</p><small>{step.agent}</small></div></li>)}</ol>;
}
