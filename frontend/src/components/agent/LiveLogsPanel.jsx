export default function LiveLogsPanel({ events = [] }) {
  const visible = events.slice(-12);
  return <section className="live-logs-panel"><header><strong>Live evidence</strong><span>{events.length} events</span></header>{visible.map((event, index) => <article key={`${event.created_at || index}-${event.title}`} className={`log-event is-${event.status || "info"}`}><b>{event.agent || "System"}</b><span>{event.title}</span>{event.detail ? <small>{event.detail}</small> : null}</article>)}</section>;
}
