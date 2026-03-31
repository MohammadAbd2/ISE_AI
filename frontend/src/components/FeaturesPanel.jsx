import { useState, useEffect } from "react";
import { VoiceCommandButton } from "../hooks/useVoiceCommand";

/**
 * Enhanced Features Panel
 * 
 * Provides access to:
 * - Voice commands
 * - Terminal
 * - Git operations
 * - RAG search
 * - Code review
 * - Project search/replace
 */
export default function FeaturesPanel({ onFeatureAction }) {
  const [activeTab, setActiveTab] = useState("terminal");
  const [terminalOutput, setTerminalOutput] = useState("");
  const [command, setCommand] = useState("");
  const [gitStatus, setGitStatus] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  // Terminal Functions
  const runCommand = async () => {
    if (!command.trim()) return;
    
    setIsLoading(true);
    try {
      const response = await fetch("http://localhost:8000/api/terminal/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command, timeout: 120 }),
      });

      const data = await response.json();
      setTerminalOutput(prev => prev + `\n$ ${command}\n${data.stdout}\n${data.stderr}`);
      
      if (data.suggested_fix) {
        setTerminalOutput(prev => prev + `\n💡 Suggestion: ${data.suggested_fix}\n`);
      }
    } catch (error) {
      setTerminalOutput(prev => prev + `\n❌ Error: ${error.message}\n`);
    } finally {
      setIsLoading(false);
      setCommand("");
    }
  };

  // Git Functions
  const loadGitStatus = async () => {
    try {
      const response = await fetch("http://localhost:8000/api/git/status");
      const data = await response.json();
      setGitStatus(data);
    } catch (error) {
      console.error("Failed to load git status:", error);
    }
  };

  const generateCommitMessage = async () => {
    try {
      const response = await fetch("http://localhost:8000/api/git/commit-message", {
        method: "POST",
      });
      const data = await response.json();
      onFeatureAction?.("commit", { message: data.message });
    } catch (error) {
      console.error("Failed to generate commit message:", error);
    }
  };

  // RAG Search Functions
  const searchCodebase = async () => {
    if (!searchQuery.trim()) return;
    
    setIsLoading(true);
    try {
      const response = await fetch("http://localhost:8000/api/rag/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: searchQuery, limit: 10 }),
      });

      const data = await response.json();
      setSearchResults(data.results);
    } catch (error) {
      console.error("Search failed:", error);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle voice commands
  useEffect(() => {
    const handleVoiceCommand = (event) => {
      const { command_type, action, suggested_params } = event.detail;
      
      switch (action) {
        case "terminal":
          setActiveTab("terminal");
          if (suggested_params.path) {
            setCommand(`python ${suggested_params.path}`);
          }
          break;
        case "rag_search":
          setActiveTab("search");
          if (suggested_params.query) {
            setSearchQuery(suggested_params.query);
            searchCodebase();
          }
          break;
        case "git_operation":
          setActiveTab("git");
          loadGitStatus();
          break;
        default:
          break;
      }
    };

    window.addEventListener("voice-command", handleVoiceCommand);
    return () => window.removeEventListener("voice-command", handleVoiceCommand);
  }, []);

  return (
    <div className="features-panel">
      {/* Panel Header with Voice Command */}
      <div className="features-header">
        <h3>🛠️ Enhanced Features</h3>
        <VoiceCommandButton />
      </div>

      {/* Tab Navigation */}
      <div className="features-tabs">
        <button
          className={`tab ${activeTab === "terminal" ? "active" : ""}`}
          onClick={() => setActiveTab("terminal")}
        >
          💻 Terminal
        </button>
        <button
          className={`tab ${activeTab === "git" ? "active" : ""}`}
          onClick={() => {
            setActiveTab("git");
            loadGitStatus();
          }}
        >
          📦 Git
        </button>
        <button
          className={`tab ${activeTab === "search" ? "active" : ""}`}
          onClick={() => setActiveTab("search")}
        >
          🔍 Search
        </button>
        <button
          className={`tab ${activeTab === "review" ? "active" : ""}`}
          onClick={() => setActiveTab("review")}
        >
          📝 Review
        </button>
      </div>

      {/* Tab Content */}
      <div className="features-content">
        {/* Terminal Tab */}
        {activeTab === "terminal" && (
          <div className="terminal-tab">
            <div className="terminal-output">
              <pre>{terminalOutput || "$ Ready for commands..."}</pre>
            </div>
            <div className="terminal-input-row">
              <input
                type="text"
                value={command}
                onChange={(e) => setCommand(e.target.value)}
                onKeyPress={(e) => e.key === "Enter" && runCommand()}
                placeholder="Enter command..."
                disabled={isLoading}
              />
              <button onClick={runCommand} disabled={isLoading}>
                {isLoading ? "⏳" : "▶️"}
              </button>
            </div>
          </div>
        )}

        {/* Git Tab */}
        {activeTab === "git" && (
          <div className="git-tab">
            {gitStatus ? (
              <div className="git-status">
                <div className="git-branch">
                  <strong>Branch:</strong> {gitStatus.branch}
                </div>
                {gitStatus.staged_changes.length > 0 && (
                  <div className="git-section">
                    <strong>Staged Changes:</strong>
                    <ul>
                      {gitStatus.staged_changes.map((file, i) => (
                        <li key={i}>{file}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {gitStatus.unstaged_changes.length > 0 && (
                  <div className="git-section">
                    <strong>Unstaged Changes:</strong>
                    <ul>
                      {gitStatus.unstaged_changes.map((file, i) => (
                        <li key={i}>{file}</li>
                      ))}
                    </ul>
                  </div>
                )}
                <button onClick={generateCommitMessage} className="git-action-btn">
                  ✨ Generate Commit Message
                </button>
              </div>
            ) : (
              <div className="git-loading">
                <p>Loading git status...</p>
                <button onClick={loadGitStatus}>Refresh</button>
              </div>
            )}
          </div>
        )}

        {/* Search Tab */}
        {activeTab === "search" && (
          <div className="search-tab">
            <div className="search-input-row">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={(e) => e.key === "Enter" && searchCodebase()}
                placeholder="Search codebase..."
                disabled={isLoading}
              />
              <button onClick={searchCodebase} disabled={isLoading}>
                {isLoading ? "⏳" : "🔍"}
              </button>
            </div>
            {searchResults.length > 0 && (
              <div className="search-results">
                {searchResults.map((result, i) => (
                  <div key={i} className="search-result">
                    <div className="result-header">
                      <span className="result-file">{result.file_path}</span>
                      <span className="result-score">Score: {(result.score * 100).toFixed(0)}%</span>
                    </div>
                    <pre className="result-content">{result.content}</pre>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Review Tab */}
        {activeTab === "review" && (
          <div className="review-tab">
            <div className="review-placeholder">
              <p>📝 Code Review Feature</p>
              <p className="hint">Select code in the chat and click "Review" to get AI-powered feedback</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
