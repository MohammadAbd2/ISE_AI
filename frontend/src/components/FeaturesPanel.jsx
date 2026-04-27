import { useEffect, useState } from "react";
import { api, fetchJson as getJson } from "../lib/api";

export default function FeaturesPanel({ currentSessionId, onArtifactRefresh }) {
  const [activeTab, setActiveTab] = useState("quick-actions");
  const [busy, setBusy] = useState(false);
  const [panelError, setPanelError] = useState("");
  
  // Quick Actions State
  const [quickAction, setQuickAction] = useState("");
  const [quickActionResult, setQuickActionResult] = useState("");
  
  // Code Snippets State
  const [snippets, setSnippets] = useState([]);
  const [newSnippet, setNewSnippet] = useState({ name: "", code: "", language: "python" });
  
  // Project Templates State
  const [selectedTemplate, setSelectedTemplate] = useState("");
  const [templateResult, setTemplateResult] = useState("");

  const quickActions = [
    { id: "explain-code", label: "📖 Explain Code", prompt: "Explain the code in my current file and suggest improvements" },
    { id: "generate-tests", label: "🧪 Generate Tests", prompt: "Generate comprehensive unit tests for the current file" },
    { id: "refactor-code", label: "♻️ Refactor Code", prompt: "Refactor the code to improve readability and performance" },
    { id: "add-comments", label: "💬 Add Comments", prompt: "Add comprehensive comments and documentation to the code" },
    { id: "optimize-code", label: "⚡ Optimize Code", prompt: "Optimize the code for better performance" },
    { id: "find-bugs", label: "🐛 Find Bugs", prompt: "Analyze the code for potential bugs and issues" },
    { id: "security-audit", label: "🔒 Security Audit", prompt: "Perform a security audit on the code" },
    { id: "create-readme", label: "📝 Create README", prompt: "Generate a comprehensive README.md for this project" },
  ];

  const codeSnippets = [
    { name: "Python FastAPI Template", language: "python", code: `from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/items/{item_id}")
async def read_item(item_id: int):
    return {"item_id": item_id}` },
    { name: "React Component", language: "javascript", code: `import React, { useState } from 'react';

const MyComponent = ({ title }) => {
  const [count, setCount] = useState(0);
  
  return (
    <div>
      <h1>{title}</h1>
      <p>Count: {count}</p>
      <button onClick={() => setCount(count + 1)}>
        Increment
      </button>
    </div>
  );
};

export default MyComponent;` },
    { name: "Python Class Template", language: "python", code: `from typing import Optional

class MyClass:
    """A sample class with type hints and docstrings."""
    
    def __init__(self, name: str, value: Optional[int] = None):
        self.name = name
        self.value = value
    
    def get_info(self) -> dict:
        """Return information about this instance."""
        return {
            "name": self.name,
            "value": self.value
        }
    
    def __str__(self) -> str:
        return f"{self.name}: {self.value}"` },
  ];

  const projectTemplates = [
    { id: "fastapi-api", name: "🚀 FastAPI REST API", description: "Complete REST API with authentication" },
    { id: "react-app", name: "⚛️ React App", description: "React app with routing and state management" },
    { id: "python-cli", name: "🖥️ Python CLI Tool", description: "Command-line tool with argparse" },
    { id: "data-analysis", name: "📊 Data Analysis", description: "Python data analysis with pandas/matplotlib" },
  ];

  async function handleQuickAction(prompt) {
    if (!prompt.trim()) {
      return;
    }
    setBusy(true);
    setPanelError("");
    setQuickActionResult("");
    try {
      const response = await fetch("/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: prompt,
          session_id: currentSessionId,
        }),
      });
      
      if (!response.ok) {
        throw new Error("Request failed");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let fullResponse = "";

      while (true) {
        const { value: chunk, done } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(chunk, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        
        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const data = JSON.parse(line);
            if (data.type === "token") {
              fullResponse += data.content;
              setQuickActionResult(fullResponse);
            }
          } catch (e) {
            // Skip invalid JSON
          }
        }
      }
    } catch (error) {
      setPanelError(error.message);
    } finally {
      setBusy(false);
    }
  }

  function handleSnippetSelect(snippet) {
    setNewSnippet({ ...snippet });
  }

  async function handleTemplateGenerate(templateId) {
    setBusy(true);
    setPanelError("");
    setTemplateResult("");
    
    const prompts = {
      "fastapi-api": "Create a complete FastAPI REST API with user authentication, database integration, and error handling",
      "react-app": "Create a React application with routing, state management, and a clean UI",
      "python-cli": "Create a Python CLI tool with argument parsing, logging, and error handling",
      "data-analysis": "Create a Python data analysis script with pandas, matplotlib, and statistical analysis",
    };
    
    try {
      const response = await fetch("/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: prompts[templateId] || "Generate a project template",
          session_id: currentSessionId,
        }),
      });
      
      if (!response.ok) {
        throw new Error("Request failed");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let fullResponse = "";

      while (true) {
        const { value: chunk, done } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(chunk, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        
        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const data = JSON.parse(line);
            if (data.type === "token") {
              fullResponse += data.content;
              setTemplateResult(fullResponse);
            }
          } catch (e) {
            // Skip invalid JSON
          }
        }
      }
    } catch (error) {
      setPanelError(error.message);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    setSnippets(codeSnippets);
  }, []);

  return (
    <section className="panel feature-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Enhanced Features</p>
          <h2>Workspace Tools</h2>
        </div>
        <span className="panel-chip">{currentSessionId ? "Session-aware" : "Draft mode"}</span>
      </div>
      <div className="feature-tabs">
        {["quick-actions", "snippets", "templates"].map((tab) => (
          <button
            key={tab}
            type="button"
            className={`feature-tab ${activeTab === tab ? "active" : ""}`}
            onClick={() => setActiveTab(tab)}
          >
            {tab === "quick-actions" ? "⚡ Quick Actions" : tab === "snippets" ? "📝 Snippets" : "📦 Templates"}
          </button>
        ))}
      </div>
      {panelError ? <div className="panel-error">{panelError}</div> : null}
      <div className="feature-body">
        {activeTab === "quick-actions" ? (
          <div className="tool-form">
            <label>
              Quick AI Actions
              <div className="quick-actions-grid">
                {quickActions.map((action) => (
                  <button
                    key={action.id}
                    type="button"
                    className="quick-action-button"
                    onClick={() => handleQuickAction(action.prompt)}
                    disabled={busy}
                  >
                    {action.label}
                  </button>
                ))}
              </div>
            </label>
            {quickActionResult ? (
              <div className="quick-action-result">
                <h4>Result:</h4>
                <pre className="action-result-content">{quickActionResult}</pre>
              </div>
            ) : null}
          </div>
        ) : null}
        
        {activeTab === "snippets" ? (
          <div className="tool-form">
            <label>
              Code Snippets Library
              <div className="snippets-list">
                {snippets.map((snippet, index) => (
                  <button
                    key={index}
                    type="button"
                    className="snippet-item"
                    onClick={() => handleSnippetSelect(snippet)}
                  >
                    <strong>{snippet.name}</strong>
                    <small>{snippet.language}</small>
                  </button>
                ))}
              </div>
            </label>
            {newSnippet.name && (
              <div className="snippet-editor">
                <h4>{newSnippet.name}</h4>
                <pre className="snippet-code">{newSnippet.code}</pre>
                <button
                  type="button"
                  className="ghost-button"
                  onClick={() => {
                    navigator.clipboard.writeText(newSnippet.code);
                  }}
                >
                  📋 Copy to Clipboard
                </button>
              </div>
            )}
          </div>
        ) : null}
        
        {activeTab === "templates" ? (
          <div className="tool-form">
            <label>
              Project Templates
              <div className="templates-list">
                {projectTemplates.map((template) => (
                  <div key={template.id} className="template-item">
                    <div className="template-info">
                      <strong>{template.name}</strong>
                      <p>{template.description}</p>
                    </div>
                    <button
                      type="button"
                      className="ghost-button"
                      onClick={() => handleTemplateGenerate(template.id)}
                      disabled={busy}
                    >
                      Generate
                    </button>
                  </div>
                ))}
              </div>
            </label>
            {templateResult ? (
              <div className="template-result">
                <h4>Generated Project:</h4>
                <pre className="template-result-content">{templateResult}</pre>
              </div>
            ) : null}
          </div>
        ) : null}
      </div>
    </section>
  );
}
