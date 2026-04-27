import React, { useEffect, useRef, useState } from 'react';
import FeaturesPanel from "./FeaturesPanel";
import ProjectExportPanel from "./ProjectExportPanel";
import DynamicVisualization from "./DynamicVisualization";
import { artifactDownloadUrl, listPendingApprovals, listApprovalsHistory, approveRequest, rejectRequest, fetchJson, api } from "../lib/api";

function OperationsPanel({ currentSessionId, onRunOperation, operationState }) {
  const disabled = !currentSessionId || operationState.loading;

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Operations</p>
          <h2>Runtime actions</h2>
        </div>
        <span className="panel-chip">{currentSessionId ? "session ready" : "no session"}</span>
      </div>
      <div className="operations-grid">
        <article className="tool-card operation-card">
          <strong>Session Analytics</strong>
          <p>Load the latest visualization, render blocks, and artifact context for the active session.</p>
          <button type="button" className="ghost-button" disabled={disabled} onClick={() => onRunOperation?.("session_analytics")}>
            Open analytics
          </button>
        </article>
        <article className="tool-card operation-card">
          <strong>Research Memory</strong>
          <p>Reopen the latest persisted research artifact as structured chat output.</p>
          <button type="button" className="ghost-button" disabled={disabled} onClick={() => onRunOperation?.("reopen_latest_research")}>
            Open research
          </button>
        </article>
        <article className="tool-card operation-card">
          <strong>Conversation Trace</strong>
          <p>Inspect recent chat history so the assistant can reason over the latest exchange state.</p>
          <button type="button" className="ghost-button" disabled={disabled} onClick={() => onRunOperation?.("session_history")}>
            Inspect history
          </button>
        </article>
      </div>
      {operationState.error ? <div className="panel-error">{operationState.error}</div> : null}
      {operationState.message ? <div className="panel-note">{operationState.message}</div> : null}
    </section>
  );
}

function ToolList({ tools, onExecuteTool, onUploadCode, onToggleTool, onDeleteTool }) {
  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Dynamic Tools</p>
          <h2>Tool registry</h2>
        </div>
      </div>
      <div className="tool-grid">
        {tools.map((tool) => (
          <article key={tool.name} className="tool-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <strong>{tool.name}</strong>
                <p>{tool.description || tool.category || "Runtime capability"}</p>
                <span>{Object.keys(tool.parameters || {}).length > 0 ? "Structured input" : "Direct invocation"}</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <button type="button" className="ghost-button" onClick={() => onExecuteTool?.(tool.name)}>
                  Execute
                </button>
                <button
                  type="button"
                  className="ghost-button"
                  onClick={async () => {
                    const code = window.prompt(`Paste source code for ${tool.name}`);
                    if (code) {
                      await onUploadCode?.(tool.name, code);
                    }
                  }}
                >
                  Upload code
                </button>
                <button
                  type="button"
                  className="ghost-button"
                  onClick={() => onToggleTool?.(tool)}
                >
                  {tool.enabled ? "Disable" : "Enable"}
                </button>
                <button
                  type="button"
                  className="danger-button"
                  onClick={() => {
                    if (window.confirm(`Delete tool ${tool.name}?`)) {
                      onDeleteTool?.(tool.name);
                    }
                  }}
                >
                  Delete
                </button>
              </div>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function CapabilityList({ capabilities }) {
  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Capabilities</p>
          <h2>System scope</h2>
        </div>
      </div>
      <div className="capability-list">
        {capabilities.map((capability) => (
          <article key={capability.name} className="capability-card">
            <div>
              <strong>{capability.name}</strong>
              <p>{capability.description || capability.category || "Available capability"}</p>
              {capability.metadata ? (
                <div className="artifact-meta">
                  {capability.metadata.route ? <span className="artifact-chip">{capability.metadata.route}</span> : null}
                  {capability.metadata.dashboard_panel ? <span className="artifact-chip muted">{capability.metadata.dashboard_panel}</span> : null}
                  {capability.metadata.default ? <span className="artifact-chip available">built-in</span> : null}
                </div>
              ) : null}
            </div>
            <span className={`status-pill ${capability.status || "available"}`}>{capability.status || "available"}</span>
          </article>
        ))}
      </div>
    </section>
  );
}

function ArtifactPanel({ artifacts, onOpenArtifact }) {
  const researchArtifacts = artifacts.filter((artifact) => artifact.kind === "research");
  const contextArtifacts = artifacts.filter((artifact) => artifact.kind !== "research");

  return (
    <>
      <section className="panel">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Research Memory</p>
            <h2>Persisted web research</h2>
          </div>
          <span className="panel-chip">{researchArtifacts.length}</span>
        </div>
        <div className="artifact-list">
          {researchArtifacts.length === 0 ? (
            <div className="empty-state">Run web research to build a reusable research memory for this session.</div>
          ) : (
            researchArtifacts.map((artifact) => (
              <article key={artifact.id} className="artifact-card research-artifact-card">
                <div>
                  <strong>{artifact.title}</strong>
                  <p>{artifact.preview}</p>
                  <div className="artifact-meta">
                    {artifact.metadata?.confidence ? (
                      <span className={`artifact-chip research-confidence ${artifact.metadata.confidence}`}>
                        {artifact.metadata.confidence} confidence
                      </span>
                    ) : null}
                    {artifact.metadata?.freshness ? (
                      <span className="artifact-chip">{artifact.metadata.freshness}</span>
                    ) : null}
                    {artifact.metadata?.conflict ? (
                      <span className="artifact-chip muted">{artifact.metadata.conflict}</span>
                    ) : null}
                  </div>
                  {Array.isArray(artifact.metadata?.query_variants) && artifact.metadata.query_variants.length > 0 ? (
                    <div className="artifact-query-plan">
                      {artifact.metadata.query_variants.slice(0, 3).map((item) => (
                        <code key={item}>{item}</code>
                      ))}
                    </div>
                  ) : null}
                </div>
                <div className="artifact-actions">
                  <button type="button" className="ghost-button" onClick={() => onOpenArtifact?.(artifact)}>
                    Open
                  </button>
                  <a href={artifactDownloadUrl(artifact.id)} target="_blank" rel="noreferrer">
                    ⬇ Download ZIP
                  </a>
                </div>
              </article>
            ))
          )}
        </div>
      </section>
      <section className="panel">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Knowledge Inputs</p>
            <h2>Uploaded context</h2>
          </div>
        </div>
        <div className="artifact-list">
          {contextArtifacts.length === 0 ? (
            <div className="empty-state">Upload files or a project archive to train the current session context.</div>
          ) : (
            contextArtifacts.map((artifact) => (
              <article key={artifact.id} className="artifact-card">
                <div>
                  <strong>{artifact.title}</strong>
                  <p>{artifact.preview}</p>
                  {artifact.kind === "archive" ? (
                    <div className="artifact-meta">
                      {Array.isArray(artifact.metadata?.frameworks)
                        ? artifact.metadata.frameworks.map((framework) => (
                            <span key={framework} className="artifact-chip">{framework}</span>
                          ))
                        : null}
                      {Array.isArray(artifact.metadata?.important_configs)
                        ? artifact.metadata.important_configs.slice(0, 3).map((item) => (
                            <span key={item} className="artifact-chip muted">{item}</span>
                          ))
                        : null}
                    </div>
                  ) : null}
                </div>
                <div className="artifact-actions">
                  <button type="button" className="ghost-button" onClick={() => onOpenArtifact?.(artifact)}>
                    Open
                  </button>
                  <a href={artifactDownloadUrl(artifact.id)} target="_blank" rel="noreferrer">
                    ⬇ Download ZIP
                  </a>
                </div>
              </article>
            ))
          )}
        </div>
      </section>
    </>
  );
}

function EvalPanel() {
  const [report, setReport] = useState(null);
  const [history, setHistory] = useState([]);
  const [drift, setDrift] = useState(null);
  const [unstable, setUnstable] = useState([]);
  const [prioritizedInstability, setPrioritizedInstability] = useState([]);
  const [hotspots, setHotspots] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function runEvals() {
    setLoading(true);
    setError("");
    try {
      const data = await fetchJson(api.evals);
      setReport(data);
      const [historyData, driftData, unstableData, prioritizedData, hotspotsData] = await Promise.all([
        fetchJson(api.evalHistory),
        fetchJson(api.evalDrift),
        fetchJson(api.evalUnstable),
        fetchJson(api.evalPrioritizedInstability),
        fetchJson(api.evalHotspots),
      ]);
      setHistory(Array.isArray(historyData.history) ? historyData.history : []);
      setDrift(driftData);
      setUnstable(Array.isArray(unstableData.cases) ? unstableData.cases : []);
      setPrioritizedInstability(Array.isArray(prioritizedData.cases) ? prioritizedData.cases : []);
      setHotspots(Array.isArray(hotspotsData.hotspots) ? hotspotsData.hotspots : []);
    } catch (err) {
      setError(err.message || String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    Promise.allSettled([
      fetchJson(api.evalHistory),
      fetchJson(api.evalDrift),
      fetchJson(api.evalUnstable),
      fetchJson(api.evalPrioritizedInstability),
      fetchJson(api.evalHotspots),
    ])
      .then((results) => {
        setHistory(results[0].status === "fulfilled" && Array.isArray(results[0].value.history) ? results[0].value.history : []);
        setDrift(results[1].status === "fulfilled" ? results[1].value : null);
        setUnstable(results[2].status === "fulfilled" && Array.isArray(results[2].value.cases) ? results[2].value.cases : []);
        setPrioritizedInstability(results[3].status === "fulfilled" && Array.isArray(results[3].value.cases) ? results[3].value.cases : []);
        setHotspots(results[4].status === "fulfilled" && Array.isArray(results[4].value.hotspots) ? results[4].value.hotspots : []);
      })
      .catch(() => {
        setHistory([]);
        setDrift(null);
        setUnstable([]);
        setPrioritizedInstability([]);
        setHotspots([]);
      });
  }, []);

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Quality</p>
          <h2>Internal evals</h2>
        </div>
        <button type="button" className="ghost-button" onClick={runEvals} disabled={loading}>
          {loading ? "Running..." : "Run evals"}
        </button>
      </div>
      {error ? <div className="panel-error">{error}</div> : null}
      {!report && !loading ? (
        <div className="empty-state">Run the routing regression suite to inspect current agent quality.</div>
      ) : null}
      {report ? (
        <div className="eval-panel">
          <div className="stats-grid">
            <div className="stat-card"><span>Suite</span><strong>{report.suite}</strong></div>
            <div className="stat-card"><span>Score</span><strong>{report.score}/10</strong></div>
            <div className="stat-card"><span>Passed</span><strong>{report.passed}/{report.total}</strong></div>
            {report.sections ? (
              <>
                <div className="stat-card"><span>Routing</span><strong>{report.sections.routing.passed}/{report.sections.routing.total}</strong></div>
                <div className="stat-card"><span>Contracts</span><strong>{report.sections.contracts.passed}/{report.sections.contracts.total}</strong></div>
              </>
            ) : null}
          </div>
          <div className="artifact-list">
            {report.results.map((result) => (
              <article key={result.name} className={`artifact-card ${result.passed ? "" : "research-artifact-card"}`}>
                <div>
                  <strong>{result.name}</strong>
                  <p>{result.prompt}</p>
                  <div className="artifact-meta">
                    <span className={`artifact-chip ${result.passed ? "available" : "muted"}`}>
                      {result.passed ? "pass" : "fail"}
                    </span>
                    <span className="artifact-chip">intent: {result.intent.kind}</span>
                    <span className="artifact-chip">agent: {String(result.intent.use_agent)}</span>
                    <span className="artifact-chip">search: {String(result.should_search)}</span>
                    <span className="artifact-chip">docs: {String(result.docs_loaded)}</span>
                  </div>
                  {!result.passed && Array.isArray(result.failures) ? (
                    <div className="artifact-query-plan">
                      {result.failures.map((failure) => (
                        <code key={`${result.name}-${failure.field}`}>
                          {failure.field}: actual={String(failure.actual)} expected={String(failure.expected)}
                        </code>
                      ))}
                    </div>
                  ) : null}
                </div>
              </article>
            ))}
            {Array.isArray(report.contracts) ? report.contracts.map((contract) => (
              <article key={contract.name} className={`artifact-card ${contract.passed ? "" : "research-artifact-card"}`}>
                <div>
                  <strong>{contract.name}</strong>
                  <p>{contract.dashboard_panel || "Capability contract"}</p>
                  <div className="artifact-meta">
                    <span className={`artifact-chip ${contract.passed ? "available" : "muted"}`}>
                      {contract.passed ? "pass" : "fail"}
                    </span>
                    <span className="artifact-chip">status: {contract.status}</span>
                    {contract.route ? <span className="artifact-chip">{contract.route}</span> : null}
                  </div>
                </div>
              </article>
            )) : null}
          </div>
          {history.length > 0 ? (
            <div className="artifact-list">
              <article className="artifact-card">
                <div>
                  <strong>Recent eval trend</strong>
                  <div className="artifact-query-plan">
                    {history.slice(-8).map((entry) => (
                      <code key={entry.created_at}>{new Date(entry.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}: {entry.score}/10</code>
                    ))}
                  </div>
                </div>
              </article>
              {drift?.available ? (
                <article className={`artifact-card ${drift.score_delta < 0 ? "research-artifact-card" : ""}`}>
                  <div>
                    <strong>Run-to-run drift</strong>
                    <p>{drift.summary}</p>
                    <div className="artifact-meta">
                      <span className="artifact-chip">delta: {drift.score_delta}</span>
                      <span className="artifact-chip">previous: {drift.previous_score}</span>
                      <span className="artifact-chip">current: {drift.current_score}</span>
                    </div>
                    {Array.isArray(drift.new_failures) && drift.new_failures.length > 0 ? (
                      <div className="artifact-query-plan">
                        {drift.new_failures.map((item) => <code key={`new-${item}`}>new: {item}</code>)}
                      </div>
                    ) : null}
                    {Array.isArray(drift.resolved_failures) && drift.resolved_failures.length > 0 ? (
                      <div className="artifact-query-plan">
                        {drift.resolved_failures.map((item) => <code key={`resolved-${item}`}>resolved: {item}</code>)}
                      </div>
                    ) : null}
                  </div>
                </article>
              ) : null}
              {unstable.length > 0 ? (
                <article className="artifact-card">
                  <div>
                    <strong>Most unstable cases</strong>
                    <div className="artifact-query-plan">
                      {unstable.map((item) => (
                        <code key={item.name}>{item.name}: {item.failures} failures</code>
                      ))}
                    </div>
                  </div>
                </article>
              ) : null}
              {prioritizedInstability.length > 0 ? (
                <article className="artifact-card research-artifact-card">
                  <div>
                    <strong>Highest impact instability</strong>
                    <div className="artifact-query-plan">
                      {prioritizedInstability.map((item) => (
                        <code key={item.name}>{item.name}: weighted {item.weighted_score}, rate {item.failure_rate}</code>
                      ))}
                    </div>
                  </div>
                </article>
              ) : null}
              {hotspots.length > 0 ? (
                <article className="artifact-card">
                  <div>
                    <strong>Subsystem hotspots</strong>
                    <div className="artifact-query-plan">
                      {hotspots.map((item) => (
                        <code key={item.subsystem}>{item.subsystem}: weighted {item.weighted_score}, cases {item.case_count}</code>
                      ))}
                    </div>
                  </div>
                </article>
              ) : null}
              {Array.isArray(report?.signals?.remediation_targets) && report.signals.remediation_targets.length > 0 ? (
                <article className="artifact-card">
                  <div>
                    <strong>Likely remediation targets</strong>
                    <div className="artifact-query-plan">
                      {report.signals.remediation_targets.slice(0, 5).map((item) => (
                        <code key={item.subsystem}>
                          {item.subsystem}: {(item.targets || []).slice(0, 3).join(", ") || "none"}
                        </code>
                      ))}
                    </div>
                  </div>
                </article>
              ) : null}
              {report?.signals?.remediation_brief?.ready ? (
                <article className="artifact-card research-artifact-card">
                  <div>
                    <strong>Remediation brief</strong>
                    <p>{report.signals.remediation_brief.summary}</p>
                    <div className="artifact-query-plan">
                      {(report.signals.remediation_brief.targets || []).slice(0, 4).map((item) => (
                        <code key={`target-${item}`}>{item}</code>
                      ))}
                    </div>
                    <div className="artifact-query-plan">
                      {(report.signals.remediation_brief.checks || []).slice(0, 3).map((item) => (
                        <code key={`check-${item}`}>{item}</code>
                      ))}
                    </div>
                  </div>
                </article>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

function CodebaseMapPanel() {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function loadMap() {
    setLoading(true);
    setError("");
    try {
      const data = await fetchJson(api.projectMap);
      setReport(data.data || null);
    } catch (err) {
      setError(err.message || String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadMap();
  }, []);

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Architecture</p>
          <h2>Codebase map</h2>
        </div>
        <button type="button" className="ghost-button" onClick={loadMap} disabled={loading}>
          {loading ? "Refreshing..." : "Refresh map"}
        </button>
      </div>
      {error ? <div className="panel-error">{error}</div> : null}
      {report ? (
        <>
          <div className="stats-grid">
            <div className="stat-card"><span>API files</span><strong>{report.summary.backend_api_files}</strong></div>
            <div className="stat-card"><span>Services</span><strong>{report.summary.backend_service_files}</strong></div>
            <div className="stat-card"><span>Components</span><strong>{report.summary.frontend_component_files}</strong></div>
            <div className="stat-card"><span>Docs</span><strong>{report.summary.docs_files}</strong></div>
            <div className="stat-card"><span>Tests</span><strong>{report.summary.test_files}</strong></div>
          </div>
          <div className="artifact-list">
            <article className="artifact-card">
              <div>
                <strong>Route modules</strong>
                <div className="artifact-query-plan">
                  {report.backend.route_modules.slice(0, 12).map((item) => <code key={item}>{item}</code>)}
                </div>
              </div>
            </article>
            <article className="artifact-card">
              <div>
                <strong>Key frontend views</strong>
                <div className="artifact-query-plan">
                  {report.frontend.key_views.slice(0, 8).map((item) => <code key={item}>{item}</code>)}
                </div>
              </div>
            </article>
            <article className="artifact-card">
              <div>
                <strong>Developer docs</strong>
                <div className="artifact-query-plan">
                  {report.docs.files.slice(0, 8).map((item) => <code key={item}>{item}</code>)}
                </div>
              </div>
            </article>
          </div>
        </>
      ) : !loading ? (
        <div className="empty-state">No codebase map is available yet.</div>
      ) : null}
    </section>
  );
}

function ImprovementPlanPanel() {
  const [report, setReport] = useState(null);
  const [packet, setPacket] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function loadPlan() {
    setLoading(true);
    setError("");
    try {
      const [data, packetData, historyData] = await Promise.all([
        fetchJson(api.improvementPlan),
        fetchJson(api.executionPacket),
        fetchJson(api.executionPacketHistory),
      ]);
      setReport(data);
      setPacket(packetData);
      setHistory(Array.isArray(historyData) ? historyData : []);
    } catch (err) {
      setError(err.message || String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadPlan();
  }, []);

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Self Development</p>
          <h2>Improvement planner</h2>
        </div>
        <button type="button" className="ghost-button" onClick={loadPlan} disabled={loading}>
          {loading ? "Refreshing..." : "Refresh plan"}
        </button>
      </div>
      {error ? <div className="panel-error">{error}</div> : null}
      {report ? (
        <>
          <div className="stats-grid">
            <div className="stat-card"><span>Eval score</span><strong>{report.overview.eval_score}/10</strong></div>
            <div className="stat-card"><span>Proposals</span><strong>{report.overview.proposal_count}</strong></div>
            <div className="stat-card"><span>Avg priority</span><strong>{report.overview.average_priority_score}</strong></div>
          </div>
          <div className="artifact-list">
            {report.proposals.map((proposal) => (
              <article key={proposal.title} className="artifact-card research-artifact-card">
                <div>
                  <strong>{proposal.title}</strong>
                  <p>{proposal.summary}</p>
                  <div className="artifact-meta">
                    <span className="artifact-chip">{proposal.category}</span>
                    <span className="artifact-chip">{proposal.priority}</span>
                    <span className="artifact-chip">{proposal.score}</span>
                  </div>
                  <div className="artifact-query-plan">
                    {proposal.rationale.slice(0, 3).map((item) => <code key={`${proposal.title}-${item}`}>{item}</code>)}
                  </div>
                  <div className="artifact-query-plan">
                    {proposal.actions.slice(0, 3).map((item) => <code key={`${proposal.title}-action-${item}`}>{item}</code>)}
                  </div>
                </div>
              </article>
            ))}
            {packet?.ready ? (
              <article className="artifact-card">
                <div>
                  <strong>Execution packet</strong>
                  <p>{packet.summary}</p>
                  <div className="artifact-query-plan">
                    {(packet.targets || []).map((item) => <code key={`target-${item}`}>{item}</code>)}
                  </div>
                  <div className="artifact-query-plan">
                    {(packet.steps || []).map((item) => <code key={`step-${item.step_number}`}>{item.step_number}. {item.description}</code>)}
                  </div>
                </div>
              </article>
            ) : null}
            {history.length > 0 ? (
              <article className="artifact-card">
                <div>
                  <strong>Recent remediation launches</strong>
                  {report?.signals?.remediation_execution_summary ? (
                    <div className="artifact-meta">
                      <span className="artifact-chip">improved: {report.signals.remediation_execution_summary.improved || 0}</span>
                      <span className="artifact-chip">pending: {report.signals.remediation_execution_summary.pending_verification || 0}</span>
                      <span className="artifact-chip">regressed: {report.signals.remediation_execution_summary.regressed || 0}</span>
                    </div>
                  ) : null}
                  <div className="artifact-query-plan">
                    {history.slice(-5).map((item) => (
                      <code key={`${item.launched_at}-${item.packet_id}`}>
                        {item.subsystem || "packet"}: {item.packet_id} [{item.status || "unknown"}]
                        {typeof item.score_delta === "number" ? ` Δ${item.score_delta >= 0 ? "+" : ""}${item.score_delta}` : ""}
                      </code>
                    ))}
                  </div>
                </div>
              </article>
            ) : null}
          </div>
          <PlanStreamPanel />
        </>
      ) : !loading ? (
        <div className="empty-state">No improvement plan is available yet.</div>
      ) : null}
    </section>
  );
}

function PlanStreamPanel(){
  const [planId, setPlanId] = useState('')
  const [events, setEvents] = useState([])
  const [connected, setConnected] = useState(false)
  const esRef = useRef(null)

  function connect(){
    if(!planId) return
    try{
      if(esRef.current){ try{ esRef.current.close() }catch(e){} }
      const es = new EventSource(`/api/plans/${encodeURIComponent(planId)}/stream`)
      es.onmessage = (ev)=>{
        try{ const data = JSON.parse(ev.data); setEvents((cur)=>[data,...cur].slice(0,50)) }catch(e){}
      }
      es.onerror = ()=>{ setConnected(false); try{ es.close() }catch(e){} }
      esRef.current = es
      setConnected(true)
    }catch(e){
      setConnected(false)
    }
  }

  function disconnect(){
    if(esRef.current){ try{ esRef.current.close() }catch(e){} }
    esRef.current = null
    setConnected(false)
  }

  return (
    <section style={{marginTop:12, padding:12, borderTop:'1px solid #eee'}}>
      <h4>Plan Stream (SSE)</h4>
      <div style={{display:'flex',gap:8,alignItems:'center'}}>
        <input placeholder="Plan ID (checkpoint)" value={planId} onChange={(e)=>setPlanId(e.target.value)} />
        <button className="ghost-button" onClick={connect} disabled={connected || !planId}>Connect</button>
        <button className="ghost-button" onClick={disconnect} disabled={!connected}>Disconnect</button>
        <span style={{marginLeft:8}}>{connected? 'Connected':'Disconnected'}</span>
      </div>
      <div style={{marginTop:8}}>
        {events.map((ev,idx)=> (
          <div key={idx} style={{padding:8,background:'#fafafa',border:'1px solid #eee',marginBottom:6}}>
            <div style={{display:'flex',justifyContent:'space-between'}}>
              <div><strong>{ev.task || ev.type || 'progress'}</strong> — {ev.status || ''} — {ev.progress || ''}</div>
              <div>
                {ev.steps && ev.steps.some(s => s.metadata && s.metadata.requires_approval) ? (
                  <button className="ghost-button" onClick={async ()=>{
                    try{
                      await fetch(`/api/plans/${encodeURIComponent(planId)}/approve`, { method: 'POST' })
                      // show a simple confirmation
                      setEvents((cur)=>[{task: ev.task, status:'approved', progress: ev.progress, steps: ev.steps}, ...cur].slice(0,50))
                    }catch(e){
                      // ignore
                    }
                  }}>Approve</button>
                ) : null}
              </div>
            </div>
            <pre style={{whiteSpace:'pre-wrap'}}>{JSON.stringify(ev.steps?.slice(0,5) || [], null, 2)}</pre>
          </div>
        ))}
      </div>
    </section>
  )
}

function TurnDiagnosticsPanel() {
  const [report, setReport] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function loadDiagnostics() {
    setLoading(true);
    setError("");
    try {
      const data = await fetchJson(api.turnDiagnostics);
      setReport(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message || String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDiagnostics();
  }, []);

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Observability</p>
          <h2>Recent turn diagnostics</h2>
        </div>
        <button type="button" className="ghost-button" onClick={loadDiagnostics} disabled={loading}>
          {loading ? "Refreshing..." : "Refresh traces"}
        </button>
      </div>
      {error ? <div className="panel-error">{error}</div> : null}
      {report.length === 0 && !loading ? (
        <div className="empty-state">No turn diagnostics are available yet.</div>
      ) : null}
      <div className="artifact-list">
        {report.slice(0, 10).map((item) => (
          <article key={`${item.created_at}-${item.message_preview}`} className="artifact-card">
            <div>
              <strong>{item.intent_kind}</strong>
              <p>{item.message_preview}</p>
              <div className="artifact-meta">
                <span className="artifact-chip">{item.mode}</span>
                <span className="artifact-chip">agent: {String(item.use_agent)}</span>
                <span className="artifact-chip">reply: {String(item.had_reply)}</span>
                <span className="artifact-chip">search: {item.search_count}</span>
                <span className="artifact-chip">images: {item.image_count}</span>
              </div>
              {item.used_agents?.length ? (
                <div className="artifact-query-plan">
                  {item.used_agents.map((agent) => <code key={`${item.created_at}-${agent}`}>{agent}</code>)}
                </div>
              ) : null}
              {item.render_block_types?.length ? (
                <div className="artifact-query-plan">
                  {item.render_block_types.map((block) => <code key={`${item.created_at}-${block}`}>{block}</code>)}
                </div>
              ) : null}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function MemorySummaryPanel() {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function loadSummary() {
    setLoading(true);
    setError("");
    try {
      const data = await fetchJson(api.memorySummary);
      setReport(data);
    } catch (err) {
      setError(err.message || String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadSummary();
  }, []);

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Memory</p>
          <h2>Structured memory</h2>
        </div>
        <button type="button" className="ghost-button" onClick={loadSummary} disabled={loading}>
          {loading ? "Refreshing..." : "Refresh memory"}
        </button>
      </div>
      {error ? <div className="panel-error">{error}</div> : null}
      {report ? (
        <div className="artifact-list">
          <article className="artifact-card">
            <div>
              <strong>User memory</strong>
              <div className="artifact-query-plan">
                <code>saved_memory: {report.user_memory.saved_memory?.length || 0}</code>
                <code>response_style: {report.user_memory.response_style || "none"}</code>
                <code>preferences: {report.user_memory.learned_preferences || 0}</code>
              </div>
            </div>
          </article>
          <article className="artifact-card">
            <div>
              <strong>Project memory</strong>
              <div className="artifact-query-plan">
                <code>technologies: {(report.project_memory.technologies || []).join(", ") || "none"}</code>
                <code>services: {report.project_memory.backend_services || 0}</code>
                <code>components: {report.project_memory.frontend_components || 0}</code>
              </div>
            </div>
          </article>
          <article className="artifact-card">
            <div>
              <strong>Research memory</strong>
              <div className="artifact-query-plan">
                <code>cached_queries: {report.research_memory.cached_queries || 0}</code>
                {(report.research_memory.known_topics || []).slice(0, 5).map((item) => <code key={item}>{item}</code>)}
              </div>
            </div>
          </article>
          <article className="artifact-card">
            <div>
              <strong>Execution memory</strong>
              <div className="artifact-query-plan">
                <code>recent_turns: {report.execution_memory.recent_turn_count || 0}</code>
                {(report.execution_memory.recent_agents || []).slice(0, 6).map((item) => <code key={item}>{item}</code>)}
              </div>
            </div>
          </article>
        </div>
      ) : !loading ? (
        <div className="empty-state">No structured memory summary is available yet.</div>
      ) : null}
    </section>
  );
}

function SelfReflectionPanel() {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function loadReflection() {
    setLoading(true);
    setError("");
    try {
      const data = await fetchJson(api.selfReflection);
      setReport(data);
    } catch (err) {
      setError(err.message || String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadReflection();
  }, []);

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Agent Insight</p>
          <h2>Self reflection</h2>
        </div>
        <button type="button" className="ghost-button" onClick={loadReflection} disabled={loading}>
          {loading ? "Refreshing..." : "Refresh reflection"}
        </button>
      </div>
      {error ? <div className="panel-error">{error}</div> : null}
      {report ? (
        <div className="artifact-list">
          <article className="artifact-card research-artifact-card">
            <div>
              <strong>Grounded self-development answer</strong>
              <p>{report.reply}</p>
            </div>
          </article>
          {Array.isArray(report.render_blocks) ? report.render_blocks.map((block, index) => (
            <article key={`${block.type}-${index}`} className="artifact-card">
              <div>
                <strong>{block.payload?.title || block.type}</strong>
                {block.payload?.summary ? <p>{block.payload.summary}</p> : null}
                {Array.isArray(block.payload?.highlights) ? (
                  <div className="artifact-query-plan">
                    {block.payload.highlights.map((item) => <code key={`${block.type}-${item}`}>{item}</code>)}
                  </div>
                ) : null}
                {Array.isArray(block.payload?.steps) ? (
                  <div className="artifact-query-plan">
                    {block.payload.steps.map((item) => <code key={`${block.type}-${item.step_number}`}>{item.description}</code>)}
                  </div>
                ) : null}
              </div>
            </article>
          )) : null}
        </div>
      ) : !loading ? (
        <div className="empty-state">No self-reflection report is available yet.</div>
      ) : null}
    </section>
  );
}

export default function DashboardView({
  currentSessionId,
  tools,
  capabilities,
  stats,
  artifacts,
  visualization,
  operationState,
  onArtifactRefresh,
  onOpenArtifact,
  onRunOperation,
  onExecuteTool,
  onUploadToolCode,
  onToggleTool,
  onDeleteTool,
}) {
  // Pending approvals subcomponent
  function PendingApprovalsPanel() {
    const [requests, setRequests] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [viewMode, setViewMode] = useState('pending'); // 'pending' | 'history'

    useEffect(() => {
      let mounted = true;
      setLoading(true);

      const loader = viewMode === 'pending' ? listPendingApprovals : listApprovalsHistory;
      loader()
        .then((data) => {
          if (!mounted) return;
          setRequests(data.requests || []);
        })
        .catch((err) => {
          if (!mounted) return;
          setError(err.message || String(err));
        })
        .finally(() => {
          if (mounted) setLoading(false);
        });
      return () => {
        mounted = false;
      };
    }, [viewMode]);

    const handleApprove = async (id) => {
      try {
        const autoEnable = window.confirm('Auto-enable related capability on approval? (OK = yes)');
        await approveRequest(id, { auto_enable: autoEnable });
        setRequests((prev) => prev.filter((r) => r.id !== id));
      } catch (e) {
        alert("Failed to approve: " + (e.message || String(e)));
      }
    };

    const handleReject = async (id) => {
      try {
        const reason = window.prompt("Reason for rejection (optional):");
        await rejectRequest(id, { reason });
        setRequests((prev) => prev.filter((r) => r.id !== id));
      } catch (e) {
        alert("Failed to reject: " + (e.message || String(e)));
      }
    };

    if (loading) {
      return <div className="empty-state">Loading approvals...</div>;
    }

    if (error) {
      return <div className="panel-error">{error}</div>;
    }

    if (!requests || requests.length === 0) {
      return <div className="empty-state">No {viewMode === 'pending' ? 'pending' : 'historical'} approval requests.</div>;
    }

    return (
      <div>
        <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
          <button className={viewMode === 'pending' ? 'primary-button' : 'ghost-button'} onClick={() => setViewMode('pending')}>Pending</button>
          <button className={viewMode === 'history' ? 'primary-button' : 'ghost-button'} onClick={() => setViewMode('history')}>History</button>
        </div>
        <div className="approval-list">
          {requests.map((req) => (
            <article key={req.id} className="tool-card approval-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px' }}>
                <div style={{ flex: 1 }}>
                  <strong>{req.action}</strong>
                  <p style={{ whiteSpace: 'pre-wrap' }}>{req.details}</p>
                  <div className="artifact-meta">
                    <span className="artifact-chip muted">Requested: {new Date(req.requested_at).toLocaleString()}</span>
                    {req.status ? <span className="artifact-chip">{req.status}</span> : null}
                  </div>
                </div>
                {viewMode === 'pending' ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <button type="button" className="ghost-button" onClick={() => handleApprove(req.id)}>Approve</button>
                    <button type="button" className="danger-button" onClick={() => handleReject(req.id)}>Reject</button>
                  </div>
                ) : null}
              </div>
            </article>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard-view">
      <FeaturesPanel currentSessionId={currentSessionId} onArtifactRefresh={onArtifactRefresh} />
      <section className="panel">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Approvals</p>
            <h2>Pending requests</h2>
          </div>
        </div>
        <PendingApprovalsPanel />
      </section>
      <section className="panel">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Overview</p>
            <h2>AI operations dashboard</h2>
          </div>
        </div>
        <div className="stats-grid">
          <div className="stat-card"><span>Tools</span><strong>{tools.length}</strong></div>
          <div className="stat-card"><span>Capabilities</span><strong>{capabilities.length}</strong></div>
          <div className="stat-card"><span>RAG files</span><strong>{stats.rag_indexed_files ?? 0}</strong></div>
          <div className="stat-card"><span>Symbols</span><strong>{stats.rag_symbols ?? 0}</strong></div>
          <div className="stat-card"><span>Research Runs</span><strong>{artifacts.filter((artifact) => artifact.kind === "research").length}</strong></div>
        </div>
      </section>
      <EvalPanel />
      <CodebaseMapPanel />
      <ImprovementPlanPanel />
      <TurnDiagnosticsPanel />
      <MemorySummaryPanel />
      <SelfReflectionPanel />
      <OperationsPanel
        currentSessionId={currentSessionId}
        onRunOperation={onRunOperation}
        operationState={operationState || {}}
      />
      {visualization ? (
        <section className="panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Visualization Studio</p>
              <h2>Current dynamic view</h2>
            </div>
          </div>
          <DynamicVisualization spec={visualization} />
        </section>
      ) : null}
      <ToolList tools={tools} />
      <CapabilityList capabilities={capabilities} />
      <ProjectExportPanel currentSessionId={currentSessionId} onExported={onArtifactRefresh} />
      <ArtifactPanel artifacts={artifacts} onOpenArtifact={onOpenArtifact} />
    </div>
  );
}
