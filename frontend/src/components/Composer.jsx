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
            placeholder="Ask, paste a URL, or upload docs, images, and videos..."
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
      </div>
      <div className="composer-footer">
        {error ? <span className="error-text">{error}</span> : null}
      </div>
    </form>
  );
}
