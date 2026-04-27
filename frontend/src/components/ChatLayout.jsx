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
  activeView,
  onViewChange,
  chatContent,
  dashboardContent,
  documentationContent,
  terminalContent,
  platformContent,
  superAgentContent,
  uxContent,
  programmingAgiContent,
  backendStatus,
}) {
  const status = backendStatus || { state: "checking", label: "Agent checking", detail: "Checking backend…" };
  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <div className="brand-mark" aria-hidden="true">
            <span className="brand-core" />
            <span className="brand-orbit brand-orbit-a" />
            <span className="brand-orbit brand-orbit-b" />
          </div>
          <div>
            <div className="brand">ISE AI</div>
            <div className="brand-subtitle">Dynamic, context-aware operator workspace</div>
          </div>
        </div>
        <nav className="main-nav">
          <button type="button" className={activeView === "dashboard" ? "active" : ""} onClick={() => onViewChange("dashboard")}>
            Dashboard
          </button>
          <button type="button" className={activeView === "chat" ? "active" : ""} onClick={() => onViewChange("chat")}>
            Chat
          </button>
          <button type="button" className={activeView === "terminal" ? "active" : ""} onClick={() => onViewChange("terminal")}>
            Terminal
          </button>
          <button type="button" className={activeView === "platform" ? "active" : ""} onClick={() => onViewChange("platform")}>
            Platform
          </button>
          <button type="button" className={activeView === "super-agent" ? "active" : ""} onClick={() => onViewChange("super-agent")}>
            Super Agent
          </button>
          <button type="button" className={activeView === "ux" ? "active" : ""} onClick={() => onViewChange("ux")}>
            UX Intelligence
          </button>
          <button type="button" className={activeView === "daily-agi" ? "active" : ""} onClick={() => onViewChange("daily-agi")}>
            Agent Workspace
          </button>
          <button type="button" className={activeView === "documentation" ? "active" : ""} onClick={() => onViewChange("documentation")}>
            Documentation
          </button>
        </nav>
        <div className={`topbar-actions operational-pulse ${status.state}`}>
          <span className="ops-dot" aria-hidden="true" />
          <div>
            <strong>{status.label}</strong>
            <small>{status.detail}</small>
          </div>
        </div>
      </header>
      <div className="workspace">
        <aside className="history-panel">
          <section className="panel sidebar-panel">
            <div className="panel-header">
              <div>
                <p className="eyebrow">Sessions</p>
                <h2>{messageCount > 1 ? `${messageCount - 1} messages` : "Ready"}</h2>
              </div>
              <button type="button" className="ghost-button danger-ghost" onClick={onClearHistory}>Clear All</button>
            </div>
            {/* New Chat Button */}
            <button type="button" className="new-chat-button" onClick={onResetChat}>
              <span className="new-chat-icon">+</span>
              <span>New Chat</span>
            </button>
            <div className="history-list">
              {sessions.map((session) => (
                <article key={session.id} className={`history-card ${session.id === currentSessionId ? "active" : ""}`}>
                  <button type="button" className="history-main" onClick={() => onOpenSession(session.id)}>
                    <strong>{session.title}</strong>
                    <span>{session.preview || "No preview yet"}</span>
                  </button>
                  {session.id !== "draft-chat" ? (
                    <button type="button" className="history-delete" onClick={() => onDeleteSession(session.id)}>Delete</button>
                  ) : null}
                </article>
              ))}
            </div>
          </section>
          <section className="panel sidebar-panel">
            <div className="panel-header">
              <div>
                <p className="eyebrow">AI Profile</p>
                <h2>Behavior and memory</h2>
              </div>
            </div>
            <label className="profile-label">
              Custom instructions
              <textarea value={customInstructions} onChange={(event) => onCustomInstructionsChange(event.target.value)} rows={5} />
            </label>
            <label className="profile-label">
              Memory
              <textarea value={memoryText} onChange={(event) => onMemoryTextChange(event.target.value)} rows={8} />
            </label>
            <button type="button" className="ghost-button" onClick={onSaveProfile}>Save profile</button>
            {profileSaved ? <div className="profile-saved">{profileSaved}</div> : null}
          </section>
        </aside>
        <main className="main-stage">
          {activeView === "dashboard"
            ? dashboardContent
            : activeView === "documentation"
              ? documentationContent
              : activeView === "terminal"
                ? terminalContent
                : activeView === "platform"
                  ? platformContent
                  : activeView === "super-agent"
                    ? superAgentContent
                    : activeView === "ux"
                      ? uxContent
                      : activeView === "daily-agi"
                        ? programmingAgiContent
                        : chatContent}
        </main>
      </div>
    </div>
  );
}
