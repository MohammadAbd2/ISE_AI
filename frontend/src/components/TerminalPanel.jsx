import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../lib/api";

function makeRunId() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID().slice(0, 12);
  return `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`;
}

function lineClass(type) {
  if (type === "stderr") return "terminal-line terminal-line-error";
  if (type === "command") return "terminal-line terminal-line-command";
  if (type === "exit") return "terminal-line terminal-line-exit";
  if (type === "heartbeat") return "terminal-line terminal-line-muted";
  return "terminal-line";
}

export default function TerminalPanel({ visible = true, initialCwd = "." }) {
  const [command, setCommand] = useState("");
  const [output, setOutput] = useState([]);
  const [isRunning, setIsRunning] = useState(false);
  const [activeRunId, setActiveRunId] = useState("");
  const [commandHistory, setCommandHistory] = useState([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const [cwd, setCwd] = useState(initialCwd || ".");
  const [streamingReady, setStreamingReady] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const abortRef = useRef(null);
  const outputRef = useRef(null);

  const statusText = useMemo(() => {
    if (isRunning) return `Streaming ${activeRunId || "run"}`;
    return streamingReady ? "Live streaming ready" : "REST fallback ready";
  }, [activeRunId, isRunning, streamingReady]);

  useEffect(() => {
    fetch(api.terminalStreamingCapabilities)
      .then((response) => setStreamingReady(response.ok))
      .catch(() => setStreamingReady(false));
  }, []);

  useEffect(() => {
    if (autoScroll && outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [output, autoScroll]);

  useEffect(() => () => abortRef.current?.abort(), []);

  function push(line) {
    setOutput((prev) => [...prev, { id: `${Date.now()}-${Math.random()}`, ...line }]);
  }

  async function runCommandFallback(cmd) {
    const response = await fetch(`${api.terminal}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ command: cmd, timeout: 120, cwd }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result?.detail || result?.message || "Command failed");
    if (result.cwd && result.cwd !== cwd) setCwd(result.cwd);
    if (result.stdout) push({ type: "stdout", content: result.stdout });
    if (result.stderr) push({ type: "stderr", content: result.stderr });
    if (result.error_analysis) push({ type: "stderr", content: JSON.stringify(result.error_analysis, null, 2) });
    push({ type: "exit", content: `Exit code ${result.return_code} (${result.duration_ms}ms)`, success: result.return_code === 0 });
  }

  async function runCommandStream(cmd) {
    const runId = makeRunId();
    setActiveRunId(runId);
    abortRef.current = new AbortController();
    const response = await fetch(api.terminalStream, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: abortRef.current.signal,
      body: JSON.stringify({ command: cmd, timeout: 300, cwd, run_id: runId }),
    });
    if (!response.ok || !response.body) {
      const text = await response.text();
      throw new Error(text || "Streaming terminal failed");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";
      for (const raw of lines) {
        if (!raw.trim()) continue;
        const event = JSON.parse(raw);
        if (event.event === "start") {
          if (event.cwd) setCwd(event.cwd);
          push({ type: "system", content: `▶ ${event.command}\nrun: ${event.run_id}\ncwd: ${event.cwd}` });
        } else if (event.event === "stdout" || event.event === "stderr") {
          push({ type: event.event, content: event.text });
        } else if (event.event === "heartbeat") {
          push({ type: "heartbeat", content: `… ${Math.round((event.elapsed_ms || 0) / 1000)}s` });
        } else if (event.event === "exit") {
          push({ type: "exit", success: event.success, content: `${event.success ? "✅" : "❌"} Exit code ${event.return_code} (${event.duration_ms}ms)` });
        }
      }
    }
  }

  async function runCommand(cmd) {
    if (!cmd.trim() || isRunning) return;
    setIsRunning(true);
    setCommandHistory((prev) => [cmd, ...prev.filter((item) => item !== cmd).slice(0, 49)]);
    setHistoryIndex(-1);
    push({ type: "command", content: `${cwd} $ ${cmd}` });
    try {
      if (streamingReady) await runCommandStream(cmd);
      else await runCommandFallback(cmd);
    } catch (error) {
      if (error.name !== "AbortError") push({ type: "stderr", content: `Error: ${error.message}` });
      else push({ type: "stderr", content: "Run cancelled by user." });
    } finally {
      setIsRunning(false);
      setCommand("");
      setActiveRunId("");
      abortRef.current = null;
    }
  }

  async function cancelRun() {
    abortRef.current?.abort();
    if (activeRunId) {
      try {
        await fetch(`${api.terminal}/runs/${encodeURIComponent(activeRunId)}/cancel`, { method: "POST" });
      } catch {
        // fetch abort is already enough for UI; backend may have finished.
      }
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      runCommand(command);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (commandHistory.length > 0 && historyIndex < commandHistory.length - 1) {
        const next = historyIndex + 1;
        setHistoryIndex(next);
        setCommand(commandHistory[next]);
      }
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      if (historyIndex > 0) {
        const next = historyIndex - 1;
        setHistoryIndex(next);
        setCommand(commandHistory[next]);
      } else {
        setHistoryIndex(-1);
        setCommand("");
      }
    } else if (e.ctrlKey && e.key.toLowerCase() === "l") {
      e.preventDefault();
      setOutput([]);
    }
  }

  if (!visible) return null;

  return (
    <section className="live-terminal-panel">
      <header className="terminal-toolbar">
        <div>
          <strong>Live Terminal</strong>
          <span>{statusText}</span>
        </div>
        <input value={cwd} onChange={(e) => setCwd(e.target.value || ".")} aria-label="Working directory" />
        <button onClick={() => setAutoScroll((value) => !value)}>{autoScroll ? "Auto-scroll on" : "Auto-scroll off"}</button>
        <button onClick={() => setOutput([])}>Clear</button>
        {isRunning && <button className="danger" onClick={cancelRun}>Cancel</button>}
      </header>

      <div ref={outputRef} className="terminal-output" role="log" aria-live="polite">
        {output.length === 0 ? (
          <div className="terminal-empty">
            Live command output will stream here line-by-line. Use this panel while the Agent installs packages, runs builds, executes tests, or debugs a workspace.
          </div>
        ) : output.map((line) => (
          <pre key={line.id} className={lineClass(line.type)}>{line.content}</pre>
        ))}
      </div>

      <footer className="terminal-input-row">
        <span>$</span>
        <input
          value={command}
          onChange={(e) => setCommand(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="npm test, pytest, npm run build, git status..."
          disabled={isRunning}
        />
        <button onClick={() => runCommand(command)} disabled={isRunning || !command.trim()}>{isRunning ? "Running" : "Run"}</button>
      </footer>
    </section>
  );
}
