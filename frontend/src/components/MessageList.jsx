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

function MessageBubbleWithAttachments({
  role,
  content,
  attachments,
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
          messageKey={`${message.role}-${index}`}
          copiedKey={copiedKey}
          onCopy={() => onCopyMessage(message, index)}
        />
      ))}
      {isLoading ? <div className="stream-status">Streaming response</div> : null}
    </section>
  );
}
