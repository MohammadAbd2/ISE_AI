import RichMessage from "./RichMessage";

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
                </a>
              ))}
            </div>
          ) : null}
        </article>
      ))}
    </section>
  );
}

function MessageBubbleWithAttachments({
  role,
  content,
  attachments,
  searchLogs,
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
        <RichMessage content={content || " "} />
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
          messageKey={`${message.role}-${index}`}
          copiedKey={copiedKey}
          onCopy={() => onCopyMessage(message, index)}
        />
      ))}
      {isLoading ? <div className="stream-status">Streaming response</div> : null}
    </section>
  );
}
