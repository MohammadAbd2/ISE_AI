import { useRef, useState } from "react";
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
  activeModel = "llama3",
  onModelChange,
  responseEffort = "medium",
  onResponseEffortChange,
  indexedFiles = [],
  onViewIndexedFiles,
}) {
  const fileInputRef = useRef(null);
  const [showModelDropdown, setShowModelDropdown] = useState(false);
  const [showEffortDropdown, setShowEffortDropdown] = useState(false);

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

  function handleModelSelect(model) {
    onModelChange?.(model);
    setShowModelDropdown(false);
  }

  function handleEffortSelect(effort) {
    onResponseEffortChange?.(effort);
    setShowEffortDropdown(false);
  }

  return (
    <form className="composer panel" onSubmit={onSubmit}>
      {/* Top controls bar */}
      <div className="composer-topline">
        <div className="composer-controls">
          {/* Model selector */}
          <div className="control-dropdown">
            <button
              type="button"
              className="control-button"
              onClick={() => setShowModelDropdown(!showModelDropdown)}
            >
              <span className="control-icon">🤖</span>
              <span className="control-label">{activeModel}</span>
              <span className="control-arrow">▼</span>
            </button>
            {showModelDropdown && (
              <div className="control-dropdown-menu">
                {["llama3", "llama3:70b", "mistral", "codellama", "deepseek-coder"].map((model) => (
                  <button
                    key={model}
                    type="button"
                    className={`control-dropdown-item ${activeModel === model ? "active" : ""}`}
                    onClick={() => handleModelSelect(model)}
                  >
                    {model}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Thinking level selector */}
          <div className="control-dropdown">
            <button
              type="button"
              className="control-button"
              onClick={() => setShowEffortDropdown(!showEffortDropdown)}
            >
              <span className="control-icon">🧠</span>
              <span className="control-label">{responseEffort}</span>
              <span className="control-arrow">▼</span>
            </button>
            {showEffortDropdown && (
              <div className="control-dropdown-menu">
                {[
                  { value: "low", label: "Low", icon: "⚡" },
                  { value: "medium", label: "Medium", icon: "🔥" },
                  { value: "high", label: "High", icon: "🚀" },
                ].map((effort) => (
                  <button
                    key={effort.value}
                    type="button"
                    className={`control-dropdown-item ${responseEffort === effort.value ? "active" : ""}`}
                    onClick={() => handleEffortSelect(effort.value)}
                  >
                    <span className="effort-icon">{effort.icon}</span>
                    <span>{effort.label}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Mode switch */}
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
        </div>

        <div className="composer-actions">
          {/* File upload button with + icon */}
          <input
            ref={fileInputRef}
            type="file"
            multiple
            hidden
            accept=".txt,.md,.pdf,.docx,.csv,.json,.zip,.js,.jsx,.ts,.tsx,.py,.png,.jpg,.jpeg,.webp,.gif,.bmp,.mp4,.mov,.mkv,.webm,.avi"
            onChange={handleFileChange}
          />
          <button
            type="button"
            className="upload-button"
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled || isUploading}
            title="Upload files"
          >
            <span className="upload-icon">+</span>
            {isUploading && <span className="upload-text">Uploading...</span>}
          </button>

          {/* Indexed files viewer */}
          {indexedFiles && indexedFiles.length > 0 && (
            <button
              type="button"
              className="indexed-files-button"
              onClick={onViewIndexedFiles}
              title={`View ${indexedFiles.length} indexed files`}
            >
              <span className="files-icon">📁</span>
              <span className="files-count">{indexedFiles.length}</span>
            </button>
          )}
        </div>
      </div>

      {/* Attachments display */}
      {attachments.length > 0 ? (
        <div className="composer-attachments">
          {attachments.map((attachment) => (
            <button
              key={attachment.id}
              type="button"
              className="composer-attachment"
              onClick={() => onRemoveAttachment(attachment.id)}
            >
              <span className="attachment-icon">📎</span>
              <span className="attachment-name">{attachment.name}</span>
              <small className="attachment-remove">✕</small>
            </button>
          ))}
        </div>
      ) : null}

      {/* Main input area */}
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
              <span className="button-icon">⏹</span>
              <span>Stop</span>
            </button>
          ) : (
            <button type="submit" className="send-button" disabled={disabled || (!value.trim() && attachments.length === 0)}>
              <span className="button-icon">➤</span>
              <span>Send</span>
            </button>
          )}
        </div>
      </div>

      {/* Footer with token usage */}
      <div className="composer-footer-row">
        <span className="composer-help">Dynamic tools, file context, voice input, and chart/map rendering are live.</span>
        {tokenUsage ? (
          <div className="token-usage-display">
            <div className="token-item">
              <span className="token-label">Input:</span>
              <span className="token-value">{tokenUsage.inputTokens || 0}</span>
            </div>
            <div className="token-item">
              <span className="token-label">Output:</span>
              <span className="token-value">{tokenUsage.outputTokens || 0}</span>
            </div>
            <div className="token-item">
              <span className="token-label">Total:</span>
              <span className="token-value">{tokenUsage.totalTokens || 0}</span>
            </div>
            <div className="token-item">
              <span className="token-label">Available:</span>
              <span className="token-value token-available">{tokenUsage.availableTokens || 0}</span>
            </div>
          </div>
        ) : null}
      </div>

      {error ? <div className="error-text">{error}</div> : null}
    </form>
  );
}
