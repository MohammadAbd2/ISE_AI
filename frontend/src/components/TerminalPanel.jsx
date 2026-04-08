import { useState, useRef, useEffect } from "react";
import { api } from "../lib/api";

export default function TerminalPanel({ visible = true }) {
  const [command, setCommand] = useState("");
  const [output, setOutput] = useState([]);
  const [isRunning, setIsRunning] = useState(false);
  const [commandHistory, setCommandHistory] = useState([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const outputRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [output]);

  async function runCommand(cmd) {
    if (!cmd.trim() || isRunning) return;

    setIsRunning(true);
    setCommandHistory((prev) => [cmd, ...prev.slice(0, 49)]);
    setHistoryIndex(-1);

    // Add command to output
    setOutput((prev) => [...prev, { type: "command", content: cmd }]);

    try {
      const response = await fetch(`${api.terminal || "http://localhost:8000/api/terminal"}/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: cmd, timeout: 120 }),
      });

      const result = await response.json();

      // Add stdout
      if (result.stdout) {
        setOutput((prev) => [...prev, { type: "stdout", content: result.stdout }]);
      }

      // Add stderr
      if (result.stderr) {
        setOutput((prev) => [...prev, { type: "stderr", content: result.stderr }]);
      }

      // Add error analysis if available
      if (result.error_analysis) {
        setOutput((prev) => [
          ...prev,
          {
            type: "error_analysis",
            content: result.error_analysis,
            fix: result.suggested_fix,
          },
        ]);
      }

      // Add return code
      setOutput((prev) => [
        ...prev,
        {
          type: "return_code",
          content: result.return_code,
          duration: result.duration_ms,
        },
      ]);
    } catch (error) {
      setOutput((prev) => [
        ...prev,
        { type: "stderr", content: `Error: ${error.message}` },
      ]);
    } finally {
      setIsRunning(false);
      setCommand("");
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      runCommand(command);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (commandHistory.length > 0 && historyIndex < commandHistory.length - 1) {
        const newIndex = historyIndex + 1;
        setHistoryIndex(newIndex);
        setCommand(commandHistory[newIndex]);
      }
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      if (historyIndex > 0) {
        const newIndex = historyIndex - 1;
        setHistoryIndex(newIndex);
        setCommand(commandHistory[newIndex]);
      } else {
        setHistoryIndex(-1);
        setCommand("");
      }
    } else if (e.key === "l" && e.ctrlKey) {
      e.preventDefault();
      setOutput([]);
    }
  }

  function clearOutput() {
    setOutput([]);
  }

  if (!visible) return null;

  return (
    <div className="terminal-panel" style={{
      display: "flex",
      flexDirection: "column",
      height: "100%",
      background: "#1e1e1e",
      color: "#d4d4d4",
      fontFamily: "'Fira Code', 'Cascadia Code', 'Consolas', monospace",
      fontSize: "13px",
    }}>
      {/* Terminal Header */}
      <div style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: "8px 12px",
        background: "#2d2d2d",
        borderBottom: "1px solid #3e3e3e",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ fontSize: "14px" }}>⌨️</span>
          <span style={{ fontWeight: "bold", fontSize: "12px" }}>TERMINAL</span>
        </div>
        <button
          onClick={clearOutput}
          style={{
            background: "transparent",
            border: "1px solid #555",
            color: "#aaa",
            padding: "2px 8px",
            borderRadius: "3px",
            cursor: "pointer",
            fontSize: "11px",
          }}
        >
          Clear (Ctrl+L)
        </button>
      </div>

      {/* Terminal Output */}
      <div
        ref={outputRef}
        style={{
          flex: 1,
          overflow: "auto",
          padding: "12px",
          lineHeight: "1.5",
        }}
      >
        {output.length === 0 && (
          <div style={{ color: "#666", fontStyle: "italic" }}>
            Welcome to ISE AI Terminal
            <br />
            Type a command and press Enter to execute
            <br />
            <br />
            <span style={{ color: "#4ec9b0" }}>Tip:</span> Use ↑/↓ for command history
          </div>
        )}

        {output.map((line, index) => {
          if (line.type === "command") {
            return (
              <div key={index} style={{ marginTop: "8px" }}>
                <span style={{ color: "#4ec9b0" }}>$ </span>
                <span style={{ color: "#dcdcaa" }}>{line.content}</span>
              </div>
            );
          }

          if (line.type === "stdout") {
            return (
              <div key={index} style={{ whiteSpace: "pre-wrap", color: "#d4d4d4" }}>
                {line.content}
              </div>
            );
          }

          if (line.type === "stderr") {
            return (
              <div key={index} style={{ whiteSpace: "pre-wrap", color: "#f48771" }}>
                {line.content}
              </div>
            );
          }

          if (line.type === "error_analysis") {
            return (
              <div key={index} style={{
                marginTop: "8px",
                padding: "8px",
                background: "#2d1f1f",
                border: "1px solid #5a3e3e",
                borderRadius: "4px",
              }}>
                <div style={{ color: "#f48771", fontWeight: "bold", marginBottom: "4px" }}>
                  🔍 Error Analysis:
                </div>
                {line.content.error_type && (
                  <div style={{ color: "#dcdcaa" }}>
                    Type: {line.content.error_type}
                  </div>
                )}
                {line.content.file_path && (
                  <div style={{ color: "#9cdcfe" }}>
                    File: {line.content.file_path}
                    {line.content.line_number && `:${line.content.line_number}`}
                  </div>
                )}
                {line.content.suggestions && line.content.suggestions.length > 0 && (
                  <div style={{ marginTop: "4px" }}>
                    {line.content.suggestions.map((suggestion, i) => (
                      <div key={i} style={{ color: "#6a9955" }}>
                        💡 {suggestion}
                      </div>
                    ))}
                  </div>
                )}
                {line.fix && (
                  <div style={{
                    marginTop: "8px",
                    padding: "6px",
                    background: "#1f2d1f",
                    border: "1px solid #3e5a3e",
                    borderRadius: "3px",
                  }}>
                    <span style={{ color: "#4ec9b0", fontWeight: "bold" }}>🔧 Suggested Fix:</span>
                    <br />
                    <span style={{ color: "#ce9178" }}>{line.fix}</span>
                  </div>
                )}
              </div>
            );
          }

          if (line.type === "return_code") {
            const success = line.content === 0;
            return (
              <div key={index} style={{
                marginTop: "4px",
                color: success ? "#4ec9b0" : "#f48771",
                fontWeight: "bold",
              }}>
                {success ? "✅" : "❌"} Exit code: {line.content}
                {line.duration && ` (${line.duration}ms)`}
              </div>
            );
          }

          return null;
        })}

        {isRunning && (
          <div style={{ color: "#4ec9b0", marginTop: "8px" }}>
            ⏳ Running...
          </div>
        )}
      </div>

      {/* Terminal Input */}
      <div style={{
        display: "flex",
        alignItems: "center",
        padding: "8px 12px",
        background: "#2d2d2d",
        borderTop: "1px solid #3e3e3e",
      }}>
        <span style={{ color: "#4ec9b0", marginRight: "8px" }}>$</span>
        <input
          ref={inputRef}
          type="text"
          value={command}
          onChange={(e) => setCommand(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type command..."
          disabled={isRunning}
          style={{
            flex: 1,
            background: "transparent",
            border: "none",
            color: "#d4d4d4",
            fontFamily: "inherit",
            fontSize: "inherit",
            outline: "none",
          }}
        />
        <button
          onClick={() => runCommand(command)}
          disabled={isRunning || !command.trim()}
          style={{
            background: isRunning ? "#555" : "#0e639c",
            border: "none",
            color: "white",
            padding: "4px 12px",
            borderRadius: "3px",
            cursor: isRunning ? "not-allowed" : "pointer",
            marginLeft: "8px",
          }}
        >
          {isRunning ? "⏳" : "▶️"}
        </button>
      </div>
    </div>
  );
}
