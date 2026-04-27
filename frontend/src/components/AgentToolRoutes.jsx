export default function AgentToolRoutes({ routes = [] }) {
  if (!routes.length) return null;
  return (
    <section className="agent-tool-routes">
      <div className="agent-tool-routes-head">
        <p className="maximum-agent-kicker">Tool routing</p>
        <h4>Selected tools and agent capabilities</h4>
      </div>
      <div className="agent-tool-route-grid">
        {routes.map((route) => (
          <article className={`agent-tool-route ${route.status}`} key={`${route.name}-${route.trigger}`}>
            <strong>{route.name}</strong>
            <span>{route.status}</span>
            <p>{route.reason || route.trigger}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
