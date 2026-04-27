import { useState } from "react";

/**
 * Confirmation Card Component
 * 
 * Displays a beautiful confirmation request with action buttons.
 * Similar to VSCode and Cursor permission dialogs.
 */
export default function ConfirmationCard({ confirmation, onRespond }) {
  const [isResponding, setIsResponding] = useState(false);
  const [customResponse, setCustomResponse] = useState("");

  if (!confirmation) {
    return null;
  }

  const {
    confirmation_id,
    icon,
    title,
    description,
    details,
    buttons,
    text_hint,
  } = confirmation;

  const handleButtonClick = async (action) => {
    setIsResponding(true);
    try {
      await onRespond(confirmation_id, action);
    } finally {
      setIsResponding(false);
    }
  };

  const handleTextSubmit = async (e) => {
    e.preventDefault();
    if (!customResponse.trim()) return;

    setIsResponding(true);
    try {
      await onRespond(confirmation_id, customResponse.trim());
      setCustomResponse("");
    } finally {
      setIsResponding(false);
    }
  };

  // Extract file path for display
  const filePath = details?.path || details?.file_path || "";
  const command = details?.command || "";
  const packageName = details?.package || "";

  return (
    <div className="confirmation-card">
      <div className="confirmation-header">
        <span className="confirmation-icon">{icon}</span>
        <h3 className="confirmation-title">{title}</h3>
      </div>

      <div className="confirmation-body">
        <p className="confirmation-description">{description}</p>

        {/* Show relevant details */}
        {filePath && (
          <div className="confirmation-detail">
            <span className="detail-label">📁 File:</span>
            <code className="detail-value">{filePath}</code>
          </div>
        )}

        {command && (
          <div className="confirmation-detail">
            <span className="detail-label">💻 Command:</span>
            <code className="detail-value">{command}</code>
          </div>
        )}

        {packageName && (
          <div className="confirmation-detail">
            <span className="detail-label">📦 Package:</span>
            <code className="detail-value">{packageName}</code>
          </div>
        )}

        {/* Action Buttons */}
        <div className="confirmation-buttons">
          {buttons.map((button, index) => (
            <button
              key={index}
              type="button"
              className={`confirmation-btn ${button.style}`}
              onClick={() => handleButtonClick(button.value)}
              disabled={isResponding}
              title={button.tooltip}
            >
              {button.label}
            </button>
          ))}
        </div>

        {/* Divider */}
        <div className="confirmation-divider">
          <span>or</span>
        </div>

        {/* Text Response */}
        <form onSubmit={handleTextSubmit} className="confirmation-text-input">
          <input
            type="text"
            value={customResponse}
            onChange={(e) => setCustomResponse(e.target.value)}
            placeholder={text_hint}
            disabled={isResponding}
            className="confirmation-input"
          />
          <button
            type="submit"
            className="confirmation-submit-btn"
            disabled={isResponding || !customResponse.trim()}
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
