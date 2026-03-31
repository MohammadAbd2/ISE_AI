export default function ChatLayout({
  activeModel,
  models,
  onModelChange,
  responseEffort,
  onResponseEffortChange,
  sessions,
  currentSessionId,
  messageCount,
  onResetChat,
  onOpenSession,
  onDeleteSession,
  onClearHistory,
  customInstructions,
  memoryText,
  onCustomInstructionsChange,
  onMemoryTextChange,
  onSaveProfile,
  profileSaved,
  storageMode,
  profileStorageMode,
  children,
}) {
  return (
    <div className="app-shell">
      {/* Decorative layers live behind the app shell so the chat UI stays readable. */}
      <div className="backdrop">
        <div className="backdrop-orb backdrop-orb-one" />
        <div className="backdrop-orb backdrop-orb-two" />
        <div className="backdrop-scanlines" />
      </div>
      <header className="topbar">
        <div className="topbar-side">
          <div className="ops-card">
            <span className="ops-label">Session</span>
            <strong>{messageCount - 1 > 0 ? `${messageCount - 1} messages` : "Idle"}</strong>
          </div>
        </div>
        <div className="brand-lockup" aria-label="ISE AI">
          <div className="brand-mark">
            <span className="brand-core" />
          </div>
          <div className="brand">ISE AI</div>
        </div>
        <div className="model-picker">
          <label className="sidebar-label" htmlFor="model-select">
            Active model
          </label>
          <div className="toolbar-actions">
            <select
              id="model-select"
              value={activeModel}
              onChange={(event) => onModelChange(event.target.value)}
            >
              {models.map((model) => (
                <option key={model} value={model}>
                  {model}
                </option>
              ))}
            </select>
            <div className="effort-picker">
              <select
                id="effort-select"
                value={responseEffort}
                onChange={(event) => onResponseEffortChange(event.target.value)}
              >
                <option value="low">Low (Faster)</option>
                <option value="medium">Medium</option>
                <option value="high">High (Longer)</option>
              </select>
            </div>
            <button type="button" className="ghost-button" onClick={onResetChat}>
              New chat
            </button>
          </div>
        </div>
      </header>
      <div className="workspace">
        <aside className="history-panel">
          <div className="history-panel-resize-handle" title="Drag to resize"></div>
          <div className="history-panel-header">
            <div>
              <div className="history-title">Chat history</div>
              <div className="history-subtitle">Persisted sessions</div>
            </div>
            <button type="button" className="ghost-button danger-ghost" onClick={onClearHistory}>
              Clear all
            </button>
          </div>
          <div className="history-list">
            {sessions.length === 0 ? (
              <div className="history-empty">No saved chats yet.</div>
            ) : (
              sessions.map((session) => (
                <article
                  key={session.id}
                  className={`history-card ${session.id === currentSessionId ? "active" : ""}`}
                >
                  <button
                    type="button"
                    className="history-main"
                    onClick={() => onOpenSession(session.id)}
                  >
                    <strong>{session.title}</strong>
                    <span>{session.preview || "No preview yet"}</span>
                  </button>
                  {session.id !== "draft-chat" ? (
                    <button
                      type="button"
                      className="history-delete"
                      onClick={() => onDeleteSession(session.id)}
                    >
                      Delete
                    </button>
                  ) : null}
                </article>
              ))
            )}
          </div>
          <div className="profile-panel">
            {/* The profile editor controls global assistant behavior across chats. */}
            <div className="history-title">AI profile</div>
            <label className="profile-label">
              Custom instructions
              <textarea
                value={customInstructions}
                onChange={(event) => onCustomInstructionsChange(event.target.value)}
                placeholder="Tell the assistant how to behave."
                rows={5}
              />
            </label>
            <label className="profile-label">
              Memory
              <textarea
                value={memoryText}
                onChange={(event) => onMemoryTextChange(event.target.value)}
                placeholder="One memory item per line."
                rows={8}
              />
            </label>
            <div className="profile-hint">
              Ask the assistant to show memory, remember facts, or request deletion. Destructive memory changes now require chat confirmation.
            </div>
            <button type="button" className="ghost-button" onClick={onSaveProfile}>
              Save profile
            </button>
            {profileSaved ? <div className="profile-saved">{profileSaved}</div> : null}
          </div>
        </aside>
        <main className="chat-panel">{children}</main>
      </div>
    </div>
  );
}
