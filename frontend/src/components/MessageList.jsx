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
                  >
                    {src ? (
                      <img src={src} alt={hit.title || "result"} loading="lazy" />
                    ) : null}
                    <span className="image-intel-caption">
                      {hit.title || hit.source_name || "Image"}
                    </span>
                  </a>
                );
              })}
            </div>
          ) : null}
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
          <p className="search-log-query">{log.query}</p>
          {log.summary ? <p className="search-log-summary">{log.summary}</p> : null}
          {log.error ? <p className="search-log-error">{log.error}</p> : null}
          {Array.isArray(log.sources) && log.sources.length > 0 ? (
            <div className="search-source-list">
              {log.sources.map((source) => (
                <a
                  key={source.url}
                  className="search-source-card"
                  href={source.url}
                  target="_blank"
                  rel="noreferrer"
                >
                  <strong>{source.title}</strong>
                  <span>{source.domain || source.url}</span>
                  {source.snippet ? <small>{source.snippet}</small> : null}
                  {source.page_excerpt ? (
                    <small className="search-source-page-excerpt">
                      {source.page_excerpt.length > 720
                        ? `${source.page_excerpt.slice(0, 720)}…`
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
