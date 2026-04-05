/**
 * Enhanced Composer Component
 * Improved error handling, loading states, and accessibility
 */

import { useRef, useState, useCallback, useEffect } from "react";
import { VoiceCommandButton } from "../hooks/useVoiceCommand";
import {
  LoadingStateManager,
  EnhancedErrorHandler,
  ChatRetryManager,
} from "../lib/enhancedChat";

export default function EnhancedComposer({
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
  const [uploadError, setUploadError] = useState(null);
  const [showErrorDetails, setShowErrorDetails] = useState(false);
  const loadingStateManager = useRef(new LoadingStateManager());
  const retryManager = useRef(new ChatRetryManager());
  const textareaRef = useRef(null);

  // Clear errors after a delay
  useEffect(() => {
    if (error || uploadError) {
      const timer = setTimeout(() => {
        setUploadError(null);
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [error, uploadError]);

  const handleKeyDown = useCallback((event) => {
    if (event.key === "Enter" && !event.shiftKey && !isLoading) {
      event.preventDefault();
      onSubmit(event);
    }
    // Allow Shift+Enter for line breaks
    if (event.key === "Enter" && event.shiftKey) {
      event.preventDefault();
      const textarea = event.target;
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const newValue = value.substring(0, start) + "\n" + value.substring(end);
      onChange(newValue);
    }
  }, [value, isLoading, onSubmit, onChange]);

  const handleFileChange = useCallback(async (event) => {
    const files = Array.from(event.target.files || []);
    if (files.length === 0) return;

    setUploadError(null);

    try {
      loadingStateManager.current.setLoading("file_upload", true);

      // Validate file sizes and types
      const maxFileSize = 50 * 1024 * 1024; // 50MB
      const validFiles = files.filter((file) => {
        if (file.size > maxFileSize) {
          setUploadError(
            `File "${file.name}" is too large. Max 50MB per file.`
          );
          return false;
        }
        return true;
      });

      if (validFiles.length === 0) return;

      // Use retry manager for upload
      await retryManager.current.executeWithRetry(
        () => onUploadFiles(validFiles),
        "file_upload"
      );
    } catch (err) {
      const handled = EnhancedErrorHandler.handle(err, "file_upload");
      setUploadError(handled.recovery?.suggestion || handled.message);
      console.error("Upload failed:", handled);
    } finally {
      loadingStateManager.current.setLoading("file_upload", false);
      event.target.value = "";
    }
  }, [onUploadFiles]);

  const handleSubmit = useCallback(
    async (event) => {
      event.preventDefault();

      if (isLoading || (!value.trim() && attachments.length === 0)) {
        return;
      }

      try {
        setUploadError(null);
        loadingStateManager.current.setLoading("message_send", true);

        await retryManager.current.executeWithRetry(
          () => onSubmit(event),
          "message_send"
        );
      } catch (err) {
        const handled = EnhancedErrorHandler.handle(err, "message_send");
        setUploadError(handled.recovery?.suggestion || handled.message);
        console.error("Message send failed:", handled);
      } finally {
        loadingStateManager.current.setLoading("message_send", false);
      }
    },
    [value, attachments, isLoading, onSubmit]
  );

  const displayError = error || uploadError;
  const currentRetryAttempt = retryManager.current.attempts;

  return (
    <form className="composer panel enhanced-composer" onSubmit={handleSubmit}>
      {/* Mode selector */}
      <div className="composer-topline">
        <div className="mode-switch">
          {["auto", "chat", "agent"].map((item) => (
            <button
              key={item}
              type="button"
              className={`mode-pill ${mode === item ? "active" : ""}`}
              onClick={() => onModeChange?.(item)}
              title={`Switch to ${item} mode`}
              disabled={isLoading || isUploading}
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
            aria-label="Attach files to your message"
          />
          <button
            type="button"
            className="ghost-button"
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled || isUploading || isLoading}
            title="Attach files (txt, pdf, code, images, video)"
          >
            {isUploading ? (
              <>
                <span className="spinner" />
                Uploading...
              </>
            ) : (
              "Attach"
            )}
          </button>
        </div>
      </div>

      {/* Attachment chips */}
      {attachments.length > 0 && (
        <div className="composer-attachments" role="status">
          {attachments.map((attachment) => (
            <button
              key={attachment.id}
              type="button"
              className="composer-attachment"
              onClick={() => onRemoveAttachment(attachment.id)}
              aria-label={`Remove ${attachment.name}`}
            >
              <span>{attachment.name}</span>
              <small>✕</small>
            </button>
          ))}
        </div>
      )}

      {/* Input area */}
      <div className="composer-input">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask, upload files, request code changes, or describe data for a chart or 3D map... (Shift+Enter for newline)"
          rows={4}
          disabled={disabled || isLoading}
          aria-label="Message input"
          spellCheck="true"
        />

        <div className="composer-inline-actions">
          <VoiceCommandButton
            onCommand={onVoiceCommand}
            disabled={isLoading || disabled}
          />

          {isLoading ? (
            <button
              type="button"
              className="send-button stop"
              onClick={onStop}
              aria-label="Stop message generation"
            >
              ⏹ Stop
            </button>
          ) : (
            <button
              type="submit"
              className="send-button"
              disabled={
                disabled ||
                (!value.trim() && attachments.length === 0) ||
                isLoading
              }
              aria-label="Send message"
            >
              Send
            </button>
          )}
        </div>
      </div>

      {/* Footer with token usage and help */}
      <div className="composer-footer-row">
        <span className="composer-help">
          {currentRetryAttempt > 0 && (
            <span className="retry-indicator">
              Attempt {currentRetryAttempt + 1} |
            </span>
          )}
          Dynamic tools, file context, voice input, and visualizations are
          live.
        </span>

        {tokenUsage && (
          <div className="token-usage-display" title="Token usage">
            <span title="Input tokens">📥 {tokenUsage.inputTokens || 0}</span>
            <span title="Output tokens">📤 {tokenUsage.outputTokens || 0}</span>
            <span
              title="Available tokens"
              className={
                tokenUsage.availableTokens &&
                tokenUsage.availableTokens < 500
                  ? "low-tokens"
                  : ""
              }
            >
              🎯 {tokenUsage.availableTokens || 0}
            </span>
          </div>
        )}
      </div>

      {/* Error display with details */}
      {displayError && (
        <div className="error-container" role="alert">
          <div className="error-message">
            <strong>⚠️ Error:</strong> {displayError}
          </div>

          {currentRetryAttempt > 0 && (
            <div className="retry-info">
              Retried {currentRetryAttempt} time
              {currentRetryAttempt > 1 ? "s" : ""}
            </div>
          )}

          {showErrorDetails && retryManager.current.lastError && (
            <details className="error-details">
              <summary>Technical details</summary>
              <pre>{JSON.stringify(retryManager.current.lastError, null, 2)}</pre>
            </details>
          )}

          <button
            type="button"
            className="error-action-btn"
            onClick={() => setShowErrorDetails(!showErrorDetails)}
          >
            {showErrorDetails ? "Hide" : "Show"} Details
          </button>
        </div>
      )}

      {/* Loading indicator */}
      {(isLoading || isUploading) && (
        <div className="loading-indicator" role="status">
          <span className="spinner" />
          {isUploading ? "Uploading files..." : "Processing..."}
        </div>
      )}
    </form>
  );
}
