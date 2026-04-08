import RichMessage from "./RichMessage";
import { useState } from "react";
import DynamicVisualization from "./DynamicVisualization";
import { artifactDownloadUrl } from "../lib/api";

function AttachmentList({ attachments }) {
  if (!attachments || attachments.length === 0) {
    return null;
  }

  return (
    <div className="message-attachments">
      {attachments.map((attachment) => (
        <span key={attachment.id} className="message-attachment-chip">
          {attachment.kind.toUpperCase()} · {attachment.name}
        </span>
      ))}
    </div>
  );
}

function ResearchProgressLog({ payload }) {
  if (!payload) return null;
  
  const { steps, latest_message, is_complete, is_error } = payload;
  
  if (!steps || steps.length === 0) return null;

  return (
    <div className={`research-progress-log ${is_complete ? 'complete' : ''} ${is_error ? 'error' : ''}`}>
      <div className="research-progress-header">
        <span className="research-progress-icon">
          {is_complete ? '✓' : is_error ? '❌' : '🔍'}
        </span>
        <span className="research-progress-status">{latest_message}</span>
      </div>
      <div className="research-progress-steps">
        {steps.map((step, index) => (
          <div key={index} className={`research-progress-step ${step.step}`}>
            <span className="step-icon">
              {step.is_complete ? '✓' : step.is_error ? '❌' : '•'}
            </span>
            <span className="step-message">{step.message}</span>
            {step.details && !step.is_complete && (
              <span className="step-details">{step.details}</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function ResourceList({ payload }) {
  if (!payload || !payload.resources || payload.resources.length === 0) {
    return null;
  }

  const { title, resources } = payload;

  return (
    <div className="resource-list">
      <div className="resource-list-header">
        <span className="resource-list-icon">📚</span>
        <h4 className="resource-list-title">{title || 'Sources'}</h4>
        <span className="resource-count">{resources.length} sources</span>
      </div>
      <div className="resource-grid">
        {resources.map((resource, index) => (
          <a
            key={index}
            href={resource.url}
            target="_blank"
            rel="noreferrer"
            className="resource-card"
            title={`${resource.title}\n${resource.url}`}
          >
            <div className="resource-card-content">
              <div className="resource-header">
                <img 
                  src={resource.favicon_url} 
                  alt="" 
                  className="resource-favicon"
                  onError={(e) => {
                    e.target.style.display = 'none';
                  }}
                />
                <span className="resource-domain">{resource.domain}</span>
              </div>
              <div className="resource-title">{resource.title}</div>
              {resource.snippet && (
                <div className="resource-snippet">{resource.snippet}</div>
              )}
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}

function AgentProgressLog({ content }) {
  // Detect agent progress logs in content
  // Format: 🔧 **Task** followed by action items with ✅ 🔄 ⏳ ❌
  
  const agentLogPattern = /🔧\s+\*\*(.+?)\*\*/;
  const actionPattern = /(✅|🔄|⏳|❌)\s+\*\*(\w+):\*\*\s+(.+?)(?=\n(?:✅|🔄|⏳|❌|$))/gs;
  
  const isAgentLog = agentLogPattern.test(content);
  
  if (!isAgentLog) {
    return null;
  }
  
  const match = content.match(agentLogPattern);
  const taskName = match ? match[1] : "Agent Task";
  
  const actions = [];
  let actionMatch;
  while ((actionMatch = actionPattern.exec(content)) !== null) {
    const iconMap = {
      "✅": "completed",
      "🔄": "in-progress",
      "⏳": "pending",
      "❌": "failed",
    };
    
    actions.push({
      icon: actionMatch[1],
      status: iconMap[actionMatch[1]] || "pending",
      actionType: actionMatch[2],
      description: actionMatch[3].trim(),
    });
  }
  
  return (
    <div className="agent-progress-log">
      <div className="agent-progress-header">
        <span className="agent-progress-icon">🤖</span>
        <span className="agent-progress-title">Agent Mode: {taskName}</span>
      </div>
      <div className="agent-progress-actions">
        {actions.map((action, index) => (
          <div
            key={index}
            className={`agent-progress-action ${action.status}`}
          >
            <span className="agent-progress-action-icon">{action.icon}</span>
            <div className="agent-progress-action-content">
              <span className="agent-progress-action-type">{action.actionType}</span>
              <span className="agent-progress-action-desc">{action.description}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ImageIntelLogList({ imageLogs }) {
  if (!imageLogs || imageLogs.length === 0) {
    return null;
  }

  return (
    <section className="image-intel-list">
      {imageLogs.map((log, index) => (
        <article
          key={`${log.kind}-${log.query || index}-${log.searched_at || index}`}
          className={`image-intel-card ${log.status === "failed" ? "failed" : ""}`}
        >
          <div className="image-intel-header">
            <span className="image-intel-badge">
              {log.kind === "generation"
                ? log.status === "failed"
                  ? "Image generation failed"
                  : "Generated image"
                : log.status === "failed"
                  ? "Image search failed"
                  : "Image search"}
            </span>
            <span className="image-intel-provider">{log.provider || "images"}</span>
          </div>
          {log.query ? <p className="image-intel-query">{log.query}</p> : null}
          {log.summary ? <p className="image-intel-summary">{log.summary}</p> : null}
          {log.error ? <p className="image-intel-error">{log.error}</p> : null}
          {Array.isArray(log.images) && log.images.length > 0 ? (
            <div className="image-intel-grid">
              {log.images.map((hit, hi) => {
                const href = hit.page_url || hit.image_url || "#";
                const src = hit.thumbnail_url || hit.image_url;
                return (
                  <a
                    key={`${hi}-${src?.slice(0, 48) || hi}`}
                    className="image-intel-cell"
                    href={href}
                    target="_blank"
                    rel="noreferrer"
                    onClick={(e) => {
                      // Prevent navigation if clicking on image
                      if (e.target.tagName === 'IMG') {
                        e.preventDefault();
                        // Open image in new tab
                        window.open(src, '_blank');
                      }
                    }}
                  >
                    {src ? (
                      <img 
                        src={src} 
                        alt={hit.title || "Image result"} 
                        loading="lazy"
                        style={{ cursor: 'pointer' }}
                        onError={(e) => {
                          // Handle broken images gracefully
                          e.target.style.display = 'none';
                          e.target.parentElement.innerHTML = '<div class="image-broken">Image unavailable</div>';
                        }}
                      />
                    ) : null}
                    <span className="image-intel-caption">
                      {hit.title || hit.source_name || "Image"}
                      {hit.source_name && <small style={{ display: 'block', opacity: 0.7, marginTop: '2px' }}>Source: {hit.source_name}</small>}
                    </span>
                  </a>
                );
              })}
            </div>
          ) : (
            <div className="image-intel-empty">
              <p>No images available. Try a different search query.</p>
            </div>
          )}
        </article>
      ))}
    </section>
  );
}

function SearchLogList({ searchLogs }) {
  if (!searchLogs || searchLogs.length === 0) {
    return null;
  }

  return (
    <section className="search-log-list">
      {searchLogs.map((log, index) => (
        <article
          key={`${log.query}-${log.searched_at || index}`}
          className={`search-log-card ${log.status === "failed" ? "failed" : ""}`}
        >
          <div className="search-log-header">
            <span className="search-log-badge">
              {log.status === "failed" ? "Web search failed" : "Web search"}
            </span>
            <span className="search-log-provider">{log.provider || "web"}</span>
          </div>
          <p className="search-log-query">
            <strong>Query:</strong> {log.query}
          </p>
          {log.summary ? (
            <p className="search-log-summary">
              <strong>Summary:</strong> {log.summary}
            </p>
          ) : null}
          {log.error ? <p className="search-log-error">Error: {log.error}</p> : null}
          {Array.isArray(log.sources) && log.sources.length > 0 ? (
            <div className="search-source-list">
              <h4 style={{ marginTop: "12px", marginBottom: "8px" }}>Sources ({log.sources.length})</h4>
              {log.sources.map((source, idx) => (
                <a
                  key={`${source.url}-${idx}`}
                  className="search-source-card"
                  href={source.url}
                  target="_blank"
                  rel="noreferrer"
                  style={{ display: "block", marginBottom: "12px", padding: "10px", borderLeft: "3px solid #0066cc" }}
                >
                  <strong style={{ display: "block", marginBottom: "4px" }}>{source.title || source.url}</strong>
                  <span style={{ display: "block", fontSize: "0.85em", color: "#666", marginBottom: "4px" }}>
                    {source.domain || source.url}
                  </span>
                  {source.snippet ? (
                    <small style={{ display: "block", marginBottom: "4px", color: "#555" }}>
                      {source.snippet}
                    </small>
                  ) : null}
                  {source.page_excerpt ? (
                    <small
                      className="search-source-page-excerpt"
                      style={{ display: "block", color: "#666", lineHeight: "1.4" }}
                    >
                      {source.page_excerpt.length > 300
                        ? `${source.page_excerpt.slice(0, 300)}…`
                        : source.page_excerpt}
                    </small>
                  ) : null}
                </a>
              ))}
            </div>
          ) : null}
        </article>
      ))}
    </section>
  );
}

function ReportBlock({ payload }) {
  const title = payload?.title || "Report";
  const summary = payload?.summary || "";
  const highlights = Array.isArray(payload?.highlights) ? payload.highlights : [];

  return (
    <section className="render-report-card">
      <div className="render-card-header">
        <strong>{title}</strong>
        <span>Report</span>
      </div>
      {summary ? <p className="render-card-summary">{summary}</p> : null}
      {highlights.length > 0 ? (
        <div className="render-card-list">
          {highlights.map((item, index) => (
            <div key={`${title}-${index}`} className="render-card-item">
              {item}
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function FileResultBlock({ payload }) {
  const files = Array.isArray(payload?.files) ? payload.files : [];
  if (files.length === 0) {
    return null;
  }

  return (
    <section className="render-file-card">
      <div className="render-card-header">
        <strong>{payload?.title || "Files changed"}</strong>
        <span>{files.length} file{files.length === 1 ? "" : "s"}</span>
      </div>
      <div className="render-card-list">
        {files.map((file, index) => (
          <div key={`${file.path || file.artifact_id || index}`} className="render-card-item file-item">
            <div>
              <strong>{file.path || file.title || "Generated file"}</strong>
              {file.summary ? <p>{file.summary}</p> : null}
              {file.diff ? <pre className="render-diff-preview">{file.diff}</pre> : null}
            </div>
            {file.artifact_id ? (
              <a href={artifactDownloadUrl(file.artifact_id)} target="_blank" rel="noreferrer">
                Download
              </a>
            ) : null}
          </div>
        ))}
      </div>
    </section>
  );
}

function ResearchResultBlock({ payload }) {
  const sources = Array.isArray(payload?.sources) ? payload.sources : [];
  const queryPlan = Array.isArray(payload?.query_plan) ? payload.query_plan : [];

  return (
    <section className="render-research-card">
      <div className="render-card-header">
        <strong>Research Result</strong>
        <span>{payload?.provider || "web"}</span>
      </div>
      {payload?.query ? <p className="render-card-summary">{payload.query}</p> : null}
      <div className="research-meta">
        {payload?.confidence ? <span className={`research-confidence ${payload.confidence}`}>Confidence: {payload.confidence}</span> : null}
        {payload?.freshness ? <span className="research-freshness">{payload.freshness}</span> : null}
      </div>
      {queryPlan.length > 0 ? (
        <div className="research-plan">
          {queryPlan.map((query) => (
            <code key={query}>{query}</code>
          ))}
        </div>
      ) : null}
      {payload?.conflict ? <div className="research-conflict">{payload.conflict}</div> : null}
      {sources.length > 0 ? (
        <div className="render-card-list">
          {sources.map((source) => (
            <a
              key={source.url}
              className="render-card-item research-source"
              href={source.url}
              target="_blank"
              rel="noreferrer"
            >
              <strong>{source.title}</strong>
              <span>{source.domain || source.url}</span>
              <div className="research-source-meta">
                {source.authority ? <small>{source.authority}</small> : null}
                {source.freshness ? <small>{source.freshness}</small> : null}
              </div>
              {source.snippet ? <p>{source.snippet}</p> : null}
            </a>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function PlanResultBlock({ payload }) {
  const steps = Array.isArray(payload?.steps) ? payload.steps : [];
  if (steps.length === 0) {
    return null;
  }

  return (
    <section className="render-plan-card">
      <div className="render-card-header">
        <strong>{payload?.title || "Execution plan"}</strong>
        <span>{payload?.status || "pending"}</span>
      </div>
      <div className="render-card-list plan-list">
        {steps.map((step) => (
          <div
            key={`${payload?.title || "plan"}-${step.step_number}-${step.target || step.description}`}
            className={`render-card-item plan-item ${step.status || "pending"}`}
          >
            <div className="plan-item-row">
              <strong>Step {step.step_number}</strong>
              <span className="plan-status">{step.status || "pending"}</span>
            </div>
            <p>{step.description}</p>
            {step.target ? <code>{step.target}</code> : null}
            {step.output ? <pre className="render-plan-output">{step.output}</pre> : null}
            {step.error ? <pre className="render-plan-output error">{step.error}</pre> : null}
          </div>
        ))}
      </div>
    </section>
  );
}

function MessageBubbleWithAttachments({
  role,
  content,
  attachments,
  searchLogs,
  imageLogs,
  visualization,
  renderBlocks,
  messageKey,
  copiedKey,
  onCopy,
}) {
  const isAssistant = role === "assistant";

  return (
    <article className={`message-row ${isAssistant ? "assistant" : "user"}`}>
      <div className="avatar">{isAssistant ? "AI" : "ME"}</div>
      <div className="message-bubble">
        <div className="message-header">
          <span className="message-role">{isAssistant ? "Assistant" : "You"}</span>
          <button
            type="button"
            className="copy-button"
            onClick={() => onCopy()}
          >
            {copiedKey === messageKey ? "Copied" : "Copy"}
          </button>
        </div>
        <AttachmentList attachments={attachments} />
        {isAssistant ? <SearchLogList searchLogs={searchLogs} /> : null}
        {isAssistant ? <ImageIntelLogList imageLogs={imageLogs} /> : null}
        {isAssistant ? <AgentProgressLog content={content} /> : null}
        <RichMessage content={content || " "} />
        {visualization ? <DynamicVisualization spec={visualization} /> : null}
        {Array.isArray(renderBlocks)
          ? renderBlocks.map((block, index) =>
              block?.type === "visualization" ? (
                <DynamicVisualization key={`${messageKey}-block-${index}`} spec={block.payload} />
              ) : block?.type === "research_progress" ? (
                <ResearchProgressLog key={`${messageKey}-block-${index}`} payload={block.payload} />
              ) : block?.type === "resource_list" ? (
                <ResourceList key={`${messageKey}-block-${index}`} payload={block.payload} />
              ) : block?.type === "report" ? (
                <ReportBlock key={`${messageKey}-block-${index}`} payload={block.payload} />
              ) : block?.type === "research_result" ? (
                <ResearchResultBlock key={`${messageKey}-block-${index}`} payload={block.payload} />
              ) : block?.type === "plan_result" ? (
                <PlanResultBlock key={`${messageKey}-block-${index}`} payload={block.payload} />
              ) : block?.type === "file_result" ? (
                <FileResultBlock key={`${messageKey}-block-${index}`} payload={block.payload} />
              ) : null,
            )
          : null}
      </div>
    </article>
  );
}

export default function MessageList({ messages, isLoading, copiedKey, onCopyMessage }) {
  return (
    <section className="message-list">
      {/* Rendering order is preserved so streaming text can update the last assistant bubble in place. */}
      {messages.map((message, index) => (
        <MessageBubbleWithAttachments
          key={`${message.role}-${index}`}
          role={message.role}
          content={message.content}
          attachments={message.attachments || []}
          searchLogs={message.search_logs || []}
          imageLogs={message.image_logs || []}
          visualization={message.visualization || null}
          renderBlocks={message.render_blocks || []}
          messageKey={`${message.role}-${index}`}
          copiedKey={copiedKey}
          onCopy={() => onCopyMessage(message, index)}
        />
      ))}
      {isLoading ? <div className="stream-status">Streaming response</div> : null}
    </section>
  );
}
