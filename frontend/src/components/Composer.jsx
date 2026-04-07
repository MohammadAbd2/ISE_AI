import { useRef } from "react";
import { VoiceInputButton } from "./VoiceInput";

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
  mode = "auto",
  onModeChange,
  tokenUsage = null,
  onVoiceCommand,
}) {
  const fileInputRef = useRef(null);

  function handleKeyDown(event) {
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

  function handleVoiceText(transcribedText) {
    onChange(value + (value && !value.endsWith(" ") ? " " : "") + transcribedText);
  }

  return (
    <form className="composer panel" onSubmit={onSubmit}>
      <div className="composer-topline">
        <div className="mode-switch">
          {["auto", "chat", "agent"].map((item) => (
            <button
              key={item}
              type="button"
              className={`mode-pill ${mode === item ? "active" : ""}`}
              onClick={() => onModeChange?.(item)}
            >
              {item}
            </button>
          ))}
        </div>
        <div className="composer-actions">
          <input
            ref={fileInputRef}
            type="file"
            multiple
            hidden
            accept=".txt,.md,.pdf,.docx,.csv,.json,.zip,.js,.jsx,.ts,.tsx,.py,.png,.jpg,.jpeg,.webp,.gif,.bmp,.mp4,.mov,.mkv,.webm,.avi"
            onChange={handleFileChange}
          />
          <button type="button" className="ghost-button" onClick={() => fileInputRef.current?.click()} disabled={disabled || isUploading}>
            {isUploading ? "Uploading..." : "Attach"}
          </button>
        </div>
      </div>
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
              <small>remove</small>
            </button>
          ))}
        </div>
      ) : null}
      <div className="composer-input">
        <textarea
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask, upload files, request code changes, or describe data for a chart or 3D map... (use 🎙️ for voice input)"
          rows={4}
          disabled={disabled}
        />
        <div className="composer-inline-actions">
          <VoiceInputButton onTextInsert={handleVoiceText} />
          {isLoading ? (
            <button type="button" className="send-button stop" onClick={onStop}>
              Stop
            </button>
          ) : (
            <button type="submit" className="send-button" disabled={disabled || (!value.trim() && attachments.length === 0)}>
              Send
            </button>
          )}
        </div>
      </div>
      <div className="composer-footer-row">
        <span className="composer-help">Dynamic tools, file context, voice input, and chart/map rendering are live.</span>
        {tokenUsage ? (
          <div className="token-usage-display">
            <span>{tokenUsage.inputTokens || 0} in</span>
            <span>{tokenUsage.outputTokens || 0} out</span>
            <span>{tokenUsage.availableTokens || 0} left</span>
          </div>
        ) : null}
      </div>
      {error ? <div className="error-text">{error}</div> : null}
    </form>
  );
}
