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
 * - AI Dashboard
 */
export default function FeaturesPanel({ onFeatureAction }) {
  const [activeTab, setActiveTab] = useState("terminal");
  const [terminalOutput, setTerminalOutput] = useState("");
  const [command, setCommand] = useState("");
  const [gitStatus, setGitStatus] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  
  // Code Review State
  const [reviewCode, setReviewCode] = useState("");
  const [reviewResult, setReviewResult] = useState("");
  
  // Search/Replace State
  const [searchText, setSearchText] = useState("");
  const [replaceText, setReplaceText] = useState("");
  const [searchGlob, setSearchGlob] = useState("**/*.py");
  const [replaceResults, setReplaceResults] = useState([]);
  
  // Dashboard State
  const [dashboardStats, setDashboardStats] = useState(null);

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

  // Code Review Function
  const reviewCode = async () => {
    if (!reviewCode.trim()) return;

    setIsLoading(true);
    try {
      const response = await fetch("http://localhost:8000/api/code/review", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: reviewCode }),
      });

      const data = await response.json();
      setReviewResult(data.review || data.feedback || "No review available");
    } catch (error) {
      setReviewResult(`❌ Error: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  // Search/Replace Function
  const searchAndReplace = async () => {
    if (!searchText.trim()) return;

    setIsLoading(true);
    try {
      const response = await fetch("http://localhost:8000/api/project/search-replace", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          search: searchText,
          replace: replaceText,
          glob: searchGlob,
          dry_run: true, // Preview first
        }),
      });

      const data = await response.json();
      setReplaceResults(data.results || []);
    } catch (error) {
      console.error("Search/Replace failed:", error);
    } finally {
      setIsLoading(false);
    }
  };

  // Dashboard Stats
  const loadDashboardStats = async () => {
    try {
      // Fetch learning stats
      const learningResponse = await fetch("http://localhost:8000/api/learning/stats");
      const learningData = await learningResponse.json();
      
      // Fetch planning demo
      const planningResponse = await fetch("http://localhost:8000/api/planning/demo");
      const planningData = await planningResponse.json();
      
      setDashboardStats({
        ...learningData,
        planning_demo: planningData,
      });
    } catch (error) {
      console.error("Failed to load dashboard stats:", error);
      // Fallback to mock data
      setDashboardStats({
        total_interactions: 0,
        preferences_learned: 0,
        code_styles: 0,
        technologies: [],
        top_patterns: [],
        planning_demo: {
          example_tasks: [
            "Create a file called text1.txt, then update the content to 'this is a text', and show me the result",
            "Create 2 files: hello.py and world.py, then run hello.py",
          ],
          features: [
            "Multi-step task planning",
            "Progress tracking (0/3, 1/3, 2/3, 3/3)",
            "Autonomous execution",
            "Detailed progress logs",
          ],
        },
      });
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

  // Load dashboard stats when tab is activated
  useEffect(() => {
    if (activeTab === "dashboard") {
      loadDashboardStats();
    }
  }, [activeTab]);

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
        <button
          className={`tab ${activeTab === "replace" ? "active" : ""}`}
          onClick={() => setActiveTab("replace")}
        >
          🔄 Replace
        </button>
        <button
          className={`tab ${activeTab === "dashboard" ? "active" : ""}`}
          onClick={() => {
            setActiveTab("dashboard");
            loadDashboardStats();
          }}
        >
          📊 Dashboard
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
            <textarea
              value={reviewCode}
              onChange={(e) => setReviewCode(e.target.value)}
              placeholder="Paste your code here for review..."
              className="code-input"
              rows={10}
            />
            <button onClick={reviewCode} disabled={isLoading || !reviewCode.trim()}>
              {isLoading ? "⏳ Reviewing..." : "📝 Review Code"}
            </button>
            {reviewResult && (
              <div className="review-result">
                <pre>{reviewResult}</pre>
              </div>
            )}
          </div>
        )}

        {/* Replace Tab */}
        {activeTab === "replace" && (
          <div className="replace-tab">
            <div className="replace-form">
              <input
                type="text"
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                placeholder="Search for..."
                className="search-input"
              />
              <input
                type="text"
                value={replaceText}
                onChange={(e) => setReplaceText(e.target.value)}
                placeholder="Replace with..."
                className="replace-input"
              />
              <input
                type="text"
                value={searchGlob}
                onChange={(e) => setSearchGlob(e.target.value)}
                placeholder="File pattern (e.g., **/*.py)"
                className="glob-input"
              />
              <button onClick={searchAndReplace} disabled={isLoading || !searchText.trim()}>
                {isLoading ? "⏳ Searching..." : "🔍 Search"}
              </button>
            </div>
            {replaceResults.length > 0 && (
              <div className="replace-results">
                <h4>Found {replaceResults.length} matches</h4>
                {replaceResults.map((result, i) => (
                  <div key={i} className="replace-result">
                    <div className="result-header">
                      <span className="result-file">{result.file_path}</span>
                      <span className="result-count">{result.matches} matches</span>
                    </div>
                    <pre className="result-preview">{result.preview}</pre>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Dashboard Tab */}
        {activeTab === "dashboard" && (
          <div className="dashboard-tab">
            {dashboardStats ? (
              <div className="dashboard-stats">
                <h3>📊 AI Chatbot Dashboard</h3>
                <div className="stats-grid">
                  <div className="stat-card">
                    <div className="stat-icon">💬</div>
                    <div className="stat-value">{dashboardStats.total_interactions || 0}</div>
                    <div className="stat-label">Total Interactions</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-icon">🎯</div>
                    <div className="stat-value">{dashboardStats.preferences_learned || 0}</div>
                    <div className="stat-label">Preferences Learned</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-icon">🎨</div>
                    <div className="stat-value">{dashboardStats.code_styles || 0}</div>
                    <div className="stat-label">Code Styles</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-icon">💻</div>
                    <div className="stat-value">{(dashboardStats.technologies || []).length}</div>
                    <div className="stat-label">Technologies</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-icon">📈</div>
                    <div className="stat-value">{(dashboardStats.top_patterns || []).length}</div>
                    <div className="stat-label">Patterns Detected</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-icon">🤖</div>
                    <div className="stat-value">Active</div>
                    <div className="stat-label">Planning Agent</div>
                  </div>
                </div>
                
                {dashboardStats.technologies && dashboardStats.technologies.length > 0 && (
                  <div className="dashboard-section">
                    <h4>💻 Detected Technologies</h4>
                    <div className="tech-tags">
                      {dashboardStats.technologies.map((tech, i) => (
                        <span key={i} className="tech-tag">{tech}</span>
                      ))}
                    </div>
                  </div>
                )}
                
                {dashboardStats.top_patterns && dashboardStats.top_patterns.length > 0 && (
                  <div className="dashboard-section">
                    <h4>🎓 Top Learned Patterns</h4>
                    <div className="patterns-list">
                      {dashboardStats.top_patterns.map((pattern, i) => (
                        <div key={i} className="pattern-item">
                          <span className="pattern-category">{pattern.category}</span>
                          <span className="pattern-name">{pattern.preference}</span>
                          <span className="pattern-confidence">{(pattern.confidence * 100).toFixed(0)}%</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                
                <div className="dashboard-section">
                  <h4>📋 Planning Agent Demo</h4>
                  <p className="demo-description">
                    The planning agent can execute multi-step tasks with progress tracking.
                    Try these examples:
                  </p>
                  <div className="example-tasks">
                    {(dashboardStats.planning_demo?.example_tasks || []).map((task, i) => (
                      <div key={i} className="example-task">
                        <span className="task-number">{i + 1}</span>
                        <span className="task-text">{task}</span>
                      </div>
                    ))}
                  </div>
                  <div className="planning-features">
                    <h5>Features:</h5>
                    <ul>
                      {(dashboardStats.planning_demo?.features || []).map((feature, i) => (
                        <li key={i}>✅ {feature}</li>
                      ))}
                    </ul>
                  </div>
                </div>
                
                <div className="dashboard-section">
                  <h4>🔧 Recent Activity</h4>
                  <div className="activity-log">
                    {dashboardStats.recent_activity?.map((activity, i) => (
                      <div key={i} className="activity-item">
                        <span className="activity-time">{activity.time}</span>
                        <span className="activity-action">{activity.action}</span>
                      </div>
                    )) || <p className="no-activity">No recent activity. Start chatting to see learning in action!</p>}
                  </div>
                </div>
              </div>
            ) : (
              <div className="dashboard-loading">
                <p>Loading dashboard...</p>
                <button onClick={loadDashboardStats}>Refresh</button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
