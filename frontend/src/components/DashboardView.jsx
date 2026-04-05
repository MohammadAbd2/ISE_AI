import FeaturesPanel from "./FeaturesPanel";
import DynamicVisualization from "./DynamicVisualization";
import { artifactDownloadUrl } from "../lib/api";

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

function ToolList({ tools }) {
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
            <strong>{tool.name}</strong>
            <p>{tool.description || tool.category || "Runtime capability"}</p>
            <span>{Object.keys(tool.parameters || {}).length > 0 ? "Structured input" : "Direct invocation"}</span>
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
                    Download
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
                    Download
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
}) {
  return (
    <div className="dashboard-view">
      <FeaturesPanel currentSessionId={currentSessionId} onArtifactRefresh={onArtifactRefresh} />
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
      <ArtifactPanel artifacts={artifacts} onOpenArtifact={onOpenArtifact} />
    </div>
  );
}
