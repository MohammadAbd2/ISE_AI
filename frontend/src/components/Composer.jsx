export default function Composer({
  value,
  onChange,
  onSubmit,
  onStop,
  disabled,
  isLoading,
  error,
}) {
  function handleKeyDown(event) {
    // Match common chat UX: Enter submits, Shift+Enter inserts a newline.
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      onSubmit(event);
    }
  }

  return (
    <form className="composer" onSubmit={onSubmit}>
      <div className="composer-shell">
        <textarea
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask, audit, inspect, reverse, debug..."
          rows={2}
          disabled={disabled}
        />
        {isLoading ? (
          <button type="button" className="stop-button" onClick={onStop}>
            Stop
          </button>
        ) : (
          <button type="submit" disabled={disabled || !value.trim()}>
            Send
          </button>
        )}
      </div>
      <div className="composer-footer">
        {error ? <span className="error-text">{error}</span> : null}
      </div>
    </form>
  );
}
