import { useEffect, useState } from "react";
import { api, fetchJson as getJson } from "../lib/api";

export default function FeaturesPanel({ currentSessionId, onArtifactRefresh }) {
  const [activeTab, setActiveTab] = useState("search");
  const [busy, setBusy] = useState(false);
  const [terminalCommand, setTerminalCommand] = useState("");
  const [terminalOutput, setTerminalOutput] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [gitStatus, setGitStatus] = useState(null);
  const [reviewPath, setReviewPath] = useState("");
  const [reviewContent, setReviewContent] = useState("");
  const [reviewResult, setReviewResult] = useState("");
  const [filePath, setFilePath] = useState("");
  const [fileContent, setFileContent] = useState("");
  const [learningStats, setLearningStats] = useState(null);
  const [panelError, setPanelError] = useState("");

  async function runTerminal() {
    if (!terminalCommand.trim()) {
      return;
    }
    setBusy(true);
    setPanelError("");
    try {
      const data = await getJson(api.terminal, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: terminalCommand, timeout: 120 }),
      });
      setTerminalOutput((current) =>
        [current, `$ ${terminalCommand}`, data.stdout, data.stderr, data.suggested_fix || ""]
          .filter(Boolean)
          .join("\n"),
      );
      setTerminalCommand("");
    } catch (error) {
      setPanelError(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function runSearch() {
    if (!searchQuery.trim()) {
      return;
    }
    setBusy(true);
    setPanelError("");
    try {
      const data = await getJson(api.ragSearch, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: searchQuery, limit: 8 }),
      });
      setSearchResults(data.results || []);
    } catch (error) {
      setPanelError(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function loadGitStatus() {
    setBusy(true);
    setPanelError("");
    try {
      const data = await getJson(api.gitStatus);
      setGitStatus(data);
    } catch (error) {
      setPanelError(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function runReview() {
    if (!reviewPath.trim() || !reviewContent.trim()) {
      return;
    }
    setBusy(true);
    setPanelError("");
    try {
      const data = await getJson(api.codeReview, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file_path: reviewPath, content: reviewContent }),
      });
      setReviewResult(data.review || "");
    } catch (error) {
      setPanelError(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function saveFile() {
    if (!filePath.trim()) {
      return;
    }
    setBusy(true);
    setPanelError("");
    try {
      await getJson(api.fileOperation, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ operation: "write", path: filePath, content: fileContent }),
      });
      onArtifactRefresh?.();
    } catch (error) {
      setPanelError(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function loadLearning() {
    setBusy(true);
    setPanelError("");
    try {
      const [stats, planning] = await Promise.all([
        getJson(api.learningStats),
        getJson(api.planningDemo),
      ]);
      setLearningStats({ stats, planning });
    } catch (error) {
      setPanelError(error.message);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (activeTab === "git" && !gitStatus) {
      loadGitStatus();
    }
    if (activeTab === "learning" && !learningStats) {
      loadLearning();
    }
  }, [activeTab]);

  return (
    <section className="panel feature-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Enhanced Features</p>
          <h2>Workspace tools</h2>
        </div>
        <span className="panel-chip">{currentSessionId ? "Session-aware" : "Draft mode"}</span>
      </div>
      <div className="feature-tabs">
        {["search", "terminal", "git", "review", "files", "learning"].map((tab) => (
          <button
            key={tab}
            type="button"
            className={`feature-tab ${activeTab === tab ? "active" : ""}`}
            onClick={() => setActiveTab(tab)}
          >
            {tab}
          </button>
        ))}
      </div>
      {panelError ? <div className="panel-error">{panelError}</div> : null}
      <div className="feature-body">
        {activeTab === "search" ? (
          <div className="tool-form">
            <label>
              Semantic code search
              <div className="inline-form">
                <input value={searchQuery} onChange={(event) => setSearchQuery(event.target.value)} placeholder="Find route handlers, hooks, models..." />
                <button type="button" onClick={runSearch} disabled={busy}>Run</button>
              </div>
            </label>
            <div className="result-list">
              {searchResults.map((result) => (
                <article key={`${result.file_path}-${result.line_number}`} className="result-card">
                  <strong>{result.file_path}</strong>
                  <span>Line {result.line_number || "?"} · score {result.score?.toFixed?.(2) ?? result.score}</span>
                  <p>{result.content}</p>
                </article>
              ))}
            </div>
          </div>
        ) : null}
        {activeTab === "terminal" ? (
          <div className="tool-form">
            <label>
              Run project command
              <div className="inline-form">
                <input value={terminalCommand} onChange={(event) => setTerminalCommand(event.target.value)} placeholder="pytest, npm run build, uvicorn backend.app.main:app --reload" />
                <button type="button" onClick={runTerminal} disabled={busy}>Run</button>
              </div>
            </label>
            <pre className="terminal-screen">{terminalOutput || "$ ready"}</pre>
          </div>
        ) : null}
        {activeTab === "git" ? (
          <div className="tool-form">
            <button type="button" onClick={loadGitStatus} disabled={busy}>Refresh git state</button>
            {gitStatus ? (
              <div className="stats-grid compact">
                <div className="stat-card"><span>Branch</span><strong>{gitStatus.branch}</strong></div>
                <div className="stat-card"><span>Staged</span><strong>{gitStatus.staged_changes.length}</strong></div>
                <div className="stat-card"><span>Unstaged</span><strong>{gitStatus.unstaged_changes.length}</strong></div>
                <div className="stat-card"><span>Untracked</span><strong>{gitStatus.untracked_files.length}</strong></div>
              </div>
            ) : null}
          </div>
        ) : null}
        {activeTab === "review" ? (
          <div className="tool-form">
            <input value={reviewPath} onChange={(event) => setReviewPath(event.target.value)} placeholder="src/components/App.jsx" />
            <textarea value={reviewContent} onChange={(event) => setReviewContent(event.target.value)} rows={8} placeholder="Paste code to review..." />
            <button type="button" onClick={runReview} disabled={busy}>Review code</button>
            {reviewResult ? <pre className="review-output">{reviewResult}</pre> : null}
          </div>
        ) : null}
        {activeTab === "files" ? (
          <div className="tool-form">
            <input value={filePath} onChange={(event) => setFilePath(event.target.value)} placeholder="relative/path/to/file.txt" />
            <textarea value={fileContent} onChange={(event) => setFileContent(event.target.value)} rows={8} placeholder="Write content..." />
            <button type="button" onClick={saveFile} disabled={busy}>Write file</button>
          </div>
        ) : null}
        {activeTab === "learning" && learningStats ? (
          <div className="tool-form">
            <div className="stats-grid compact">
              <div className="stat-card"><span>Interactions</span><strong>{learningStats.stats.total_interactions ?? 0}</strong></div>
              <div className="stat-card"><span>Preferences</span><strong>{learningStats.stats.preferences_learned ?? 0}</strong></div>
              <div className="stat-card"><span>Styles</span><strong>{learningStats.stats.code_styles ?? 0}</strong></div>
            </div>
            <div className="result-card">
              <strong>Planning examples</strong>
              {(learningStats.planning.example_tasks || []).map((item) => <p key={item}>{item}</p>)}
            </div>
          </div>
        ) : null}
      </div>
    </section>
  );
}
