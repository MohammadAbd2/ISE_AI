import { useRef } from "react";

export default function Composer({
  value,
  onChange,
  onSubmit,
  onStop,
  onUploadFiles,
  onRemoveAttachment,
  attachments,
  disabled,
  isLoading,
  isUploading,
  error,
  mode = "auto",  // "auto", "chat", or "agent"
  onModeChange,
  tokenUsage = null,
}) {
  const fileInputRef = useRef(null);

  function handleKeyDown(event) {
    // Match common chat UX: Enter submits, Shift+Enter inserts a newline.
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      onSubmit(event);
    }
  }

  async function handleFileChange(event) {
    const files = Array.from(event.target.files || []);
    if (files.length > 0) {
      await onUploadFiles(files);
    }
    event.target.value = "";
  }

  const getModeIcon = (m) => {
    switch(m) {
      case 'auto': return '🤖';
      case 'chat': return '💬';
      case 'agent': return '⚡';
      default: return '🤖';
    }
  };

  const getModeLabel = (m) => {
    switch(m) {
      case 'auto': return 'Auto';
      case 'chat': return 'Chat';
      case 'agent': return 'Agent';
      default: return 'Auto';
    }
  };

  const getModeHint = (m) => {
    switch(m) {
      case 'auto': return 'Auto selects best mode: Agent for coding tasks, Chat for questions';
      case 'chat': return 'Chat mode for questions, conversations, and general queries';
      case 'agent': return 'Agent can modify files, install packages, and execute code';
      default: return '';
    }
  };

  return (
    <form className="composer" onSubmit={onSubmit}>
      {attachments.length > 0 ? (
        <div className="composer-attachments">
          {attachments.map((attachment) => (
            <button
              key={attachment.id}
              type="button"
              className="composer-attachment"
              onClick={() => onRemoveAttachment(attachment.id)}
            >
              <span>{attachment.name}</span>
              <span className="composer-attachment-remove">Remove</span>
            </button>
          ))}
        </div>
      ) : null}
      <div className="composer-shell">
        {/* Mode Toggle */}
        <div className="composer-mode-toggle">
          <div className="mode-toggle-group">
            <button
              type="button"
              className={`mode-toggle-btn auto ${mode === "auto" ? "active" : ""}`}
              onClick={() => onModeChange && onModeChange("auto")}
              title="Auto: AI selects best mode based on your request"
            >
              🤖 Auto
            </button>
            <button
              type="button"
              className={`mode-toggle-btn chat ${mode === "chat" ? "active" : ""}`}
              onClick={() => onModeChange && onModeChange("chat")}
              title="Chat: Always use conversation mode"
            >
              💬 Chat
            </button>
            <button
              type="button"
              className={`mode-toggle-btn agent ${mode === "agent" ? "active" : ""}`}
              onClick={() => onModeChange && onModeChange("agent")}
              title="Agent: Always use autonomous coding agent"
            >
              ⚡ Agent
            </button>
          </div>
          <span className="mode-hint">
            {getModeHint(mode)}
          </span>
        </div>

        <div className="composer-toolbar">
          <div className="composer-tools">
            <input
              ref={fileInputRef}
              type="file"
              multiple
              hidden
              accept={[
                ".txt",
                ".md",
                ".pdf",
                ".docx",
                ".png",
                ".jpg",
                ".jpeg",
                ".webp",
                ".gif",
                ".bmp",
                ".mp4",
                ".mov",
                ".mkv",
                ".webm",
                ".avi",
                "text/plain",
                "application/pdf",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "image/*",
                "video/*",
              ].join(",")}
              onChange={handleFileChange}
            />
            <button
              type="button"
              className="upload-button"
              onClick={() => fileInputRef.current?.click()}
              disabled={disabled || isUploading}
            >
              {isUploading ? "Uploading..." : "Upload files"}
            </button>
          </div>
          <span className="composer-hint">Docs, images, videos, and pasted links are supported.</span>
        </div>
        <div className="composer-input-row">
          <textarea
            value={value}
            onChange={(event) => onChange(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              mode === "agent"
                ? "Ask me to code, fix bugs, create features, or modify files..."
                : mode === "auto"
                ? "Ask anything - I'll auto-select the best mode (coding tasks → Agent, questions → Chat)..."
                : "Ask, paste a URL, or upload docs, images, and videos..."
            }
            rows={3}
            disabled={disabled}
          />
          {isLoading ? (
            <button type="button" className="stop-button" onClick={onStop}>
              Stop
            </button>
          ) : (
            <button type="submit" disabled={disabled || (!value.trim() && attachments.length === 0)}>
              Send
            </button>
          )}
        </div>

        {/* Token Usage Display */}
        {tokenUsage && (
          <div className="token-usage-display">
            <div className="token-box">
              <span className="token-label">Input</span>
              <span className="token-value">{tokenUsage.inputTokens?.toLocaleString() || 0}</span>
            </div>
            <div className="token-box">
              <span className="token-label">Output</span>
              <span className="token-value">{tokenUsage.outputTokens?.toLocaleString() || 0}</span>
            </div>
            <div className="token-box total">
              <span className="token-label">Total</span>
              <span className="token-value">{tokenUsage.totalTokens?.toLocaleString() || 0}</span>
            </div>
            <div className="token-box available">
              <span className="token-label">Available</span>
              <span className="token-value">{tokenUsage.availableTokens?.toLocaleString() || "∞"}</span>
            </div>
          </div>
        )}
      </div>
      <div className="composer-footer">
        {error ? <span className="error-text">{error}</span> : null}
      </div>
    </form>
  );
}
