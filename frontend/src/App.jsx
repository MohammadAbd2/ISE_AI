import { useEffect, useRef, useState } from "react";
import ChatLayout from "./components/ChatLayout";
import Composer from "./components/Composer";
import DashboardView from "./components/DashboardView";
import MessageList from "./components/MessageList";
import TerminalPanel from "./components/TerminalPanel";
import { api, executeEvolutionTool, fetchJson } from "./lib/api";
import {
  buildVisualizationArtifacts,
  buildVisualizationSpec,
  summarizeVisualization,
} from "./lib/visualization";
import { classifyTaskIntent } from "./lib/taskIntent";

const DEFAULT_MODEL = "llama3";
const DRAFT_SESSION_ID = "draft-chat";

function createDraftContextId() {
  if (globalThis.crypto?.randomUUID) {
    return `draft:${globalThis.crypto.randomUUID()}`;
  }
  return `draft:${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

function readFileAsBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result;
      if (typeof dataUrl !== "string") {
        reject(new Error("File could not be read"));
        return;
      }
      resolve(dataUrl.split(",")[1] || "");
    };
    reader.onerror = () => reject(new Error("File upload failed"));
    reader.readAsDataURL(file);
  });
}

const initialMessages = [
  {
    role: "assistant",
    content: "ISE AI is online. Ask for code changes, uploads, charts, maps, or project analysis.",
    search_logs: [],
    image_logs: [],
  },
];

export default function App() {
  const [messages, setMessages] = useState(initialMessages);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [activeModel, setActiveModel] = useState(DEFAULT_MODEL);
  const [responseEffort, setResponseEffort] = useState("medium");
  const [models, setModels] = useState([DEFAULT_MODEL]);
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [draftContextId, setDraftContextId] = useState(createDraftContextId);
  const [pendingAttachments, setPendingAttachments] = useState([]);
  const [customInstructions, setCustomInstructions] = useState("");
  const [memoryText, setMemoryText] = useState("");
  const [profileSaved, setProfileSaved] = useState("");
  const [error, setError] = useState("");
  const [copiedKey, setCopiedKey] = useState("");
  const [mode, setMode] = useState("auto");
  const [activeView, setActiveView] = useState("chat");
  const [showIndexedFiles, setShowIndexedFiles] = useState(false);
  const [tokenUsage, setTokenUsage] = useState({
    inputTokens: 0,
    outputTokens: 0,
    totalTokens: 0,
    availableTokens: 100000,
  });
  const [tools, setTools] = useState([]);
  const [capabilities, setCapabilities] = useState([]);
  const [dashboardStats, setDashboardStats] = useState({});
  const [artifacts, setArtifacts] = useState([]);
  const [activeVisualization, setActiveVisualization] = useState(null);
  const [operationState, setOperationState] = useState({ loading: false, message: "", error: "" });
  const abortRef = useRef(null);
  const copiedTimeoutRef = useRef(null);

  function currentContextId() {
    return currentSessionId || draftContextId;
  }

  function buildArtifactReportBlocks(nextArtifacts) {
    if (!Array.isArray(nextArtifacts) || nextArtifacts.length === 0) {
      return [];
    }
    const latest = nextArtifacts.slice(0, 5);
    return [
      {
        type: "report",
        payload: {
          title: "Session context updated",
          summary: "New artifacts are available to ground the assistant in your uploaded files and generated outputs.",
          highlights: latest.map((artifact) => `${artifact.kind}: ${artifact.title}`),
        },
      },
      {
        type: "file_result",
        payload: {
          title: "Recent artifacts",
          files: latest.map((artifact) => ({
            title: artifact.title,
            summary: artifact.preview,
            artifact_id: artifact.id,
          })),
        },
      },
    ];
  }

  useEffect(() => {
    loadModels();
    loadSessions();
    loadProfile();
    loadDashboard();
    return () => {
      copiedTimeoutRef.current && clearTimeout(copiedTimeoutRef.current);
      abortRef.current?.abort();
    };
  }, []);

  useEffect(() => {
    loadArtifacts(currentContextId());
  }, [currentSessionId, draftContextId]);

  async function loadModels() {
    try {
      const data = await fetchJson(api.models);
      if (Array.isArray(data.models) && data.models.length > 0) {
        setModels(data.models);
        setActiveModel((current) => (data.models.includes(current) ? current : data.models[0]));
      }
    } catch {
      setModels([DEFAULT_MODEL]);
    }
  }

  async function loadSessions() {
    try {
      const data = await fetchJson(api.chats);
      setSessions(Array.isArray(data.sessions) ? data.sessions : []);
    } catch {
      setSessions([]);
    }
  }

  async function loadProfile() {
    try {
      const data = await fetchJson(api.profile);
      setCustomInstructions(data.custom_instructions || "");
      setMemoryText(data.memory || "");
    } catch {
      setCustomInstructions("");
      setMemoryText("");
    }
  }

  async function loadDashboard() {
    const tasks = await Promise.allSettled([
      fetchJson(api.tools),
      fetchJson(api.capabilities),
      fetchJson(api.stats),
    ]);
    setTools(tasks[0].status === "fulfilled" ? tasks[0].value.tools || [] : []);
    setCapabilities(tasks[1].status === "fulfilled" ? tasks[1].value.capabilities || [] : []);
    setDashboardStats(tasks[2].status === "fulfilled" ? tasks[2].value : {});
  }

  async function loadArtifacts(sessionId) {
    if (!sessionId) {
      setArtifacts([]);
      return [];
    }
    try {
      const data = await fetchJson(`${api.artifacts}?session_id=${encodeURIComponent(sessionId)}`);
      const nextArtifacts = data.artifacts || [];
      setArtifacts(nextArtifacts);
      return nextArtifacts;
    } catch {
      setArtifacts([]);
      return [];
    }
  }

  async function refreshIndexedFiles() {
    const latestArtifacts = await loadArtifacts(currentContextId());
    // Auto-close modal if no artifacts
    if (latestArtifacts.length === 0) {
      setShowIndexedFiles(false);
    }
  }

  async function saveProfile() {
    try {
      const data = await fetchJson(api.profile, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ custom_instructions: customInstructions, memory: memoryText }),
      });
      setCustomInstructions(data.custom_instructions || "");
      setMemoryText(data.memory || "");
      setProfileSaved("Saved");
      setTimeout(() => setProfileSaved(""), 1500);
    } catch {
      setError("Failed to save AI profile.");
    }
  }

  function resetTokenUsage() {
    setTokenUsage({ inputTokens: 0, outputTokens: 0, totalTokens: 0, availableTokens: 100000 });
  }

  function calculateTokenUsage(text) {
    return Math.ceil((text || "").length / 4);
  }

  function updateInputTokens(text) {
    setTokenUsage((current) => ({ ...current, inputTokens: calculateTokenUsage(text) }));
  }

  function consumeInputTokens(text) {
    const count = calculateTokenUsage(text);
    setTokenUsage((current) => ({
      ...current,
      totalTokens: current.totalTokens + count,
      availableTokens: Math.max(0, current.availableTokens - count),
    }));
  }

  function consumeOutputTokens(text) {
    const count = calculateTokenUsage(text);
    setTokenUsage((current) => ({
      ...current,
      outputTokens: current.outputTokens + count,
      totalTokens: current.totalTokens + count,
      availableTokens: Math.max(0, current.availableTokens - count),
    }));
  }

  function resetChat() {
    abortRef.current?.abort();
    abortRef.current = null;
    setMessages(initialMessages);
    setCurrentSessionId(null);
    setDraftContextId(createDraftContextId());
    setPendingAttachments([]);
    setInput("");
    setError("");
    setIsLoading(false);
    setCopiedKey("");
    setActiveVisualization(null);
    setArtifacts([]);
    setShowIndexedFiles(false);
    resetTokenUsage();
  }

  async function openSession(sessionId) {
    if (sessionId === DRAFT_SESSION_ID) {
      resetChat();
      return;
    }
    try {
      const data = await fetchJson(`${api.chats}/${sessionId}`);
      setCurrentSessionId(data.id);
      setActiveModel(data.model || DEFAULT_MODEL);
      setMessages(
        data.messages.length > 0
          ? data.messages.map((message) => ({
              ...message,
              search_logs: message.search_logs || [],
              image_logs: message.image_logs || [],
              render_blocks: message.render_blocks || [],
            }))
          : initialMessages,
      );
      setPendingAttachments([]);
      setError("");
      await loadArtifacts(data.id);
    } catch {
      setError("Failed to load chat history.");
    }
  }

  async function deleteSession(sessionId) {
    if (sessionId === DRAFT_SESSION_ID) {
      return;
    }
    try {
      await fetchJson(`${api.chats}/${sessionId}`, { method: "DELETE" });
      if (sessionId === currentSessionId) {
        resetChat();
      }
      await loadSessions();
    } catch {
      setError("Failed to delete chat.");
    }
  }

  async function clearHistory() {
    try {
      await fetchJson(api.chats, { method: "DELETE" });
      resetChat();
      setSessions([]);
    } catch {
      setError("Failed to clear chat history.");
    }
  }

  async function handleCopyMessage(message, index) {
    try {
      await navigator.clipboard.writeText(message.content);
      const key = `${message.role}-${index}`;
      setCopiedKey(key);
      copiedTimeoutRef.current && clearTimeout(copiedTimeoutRef.current);
      copiedTimeoutRef.current = setTimeout(() => setCopiedKey(""), 1500);
    } catch {
      setError("Copy failed.");
    }
  }

  async function handleUploadFiles(files) {
    setIsUploading(true);
    setError("");
    try {
      const uploaded = [];
      for (const file of files) {
        const response = await fetchJson(api.upload, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: currentContextId(),
            filename: file.name,
            content_type: file.type || "application/octet-stream",
            data_base64: await readFileAsBase64(file),
          }),
        });
        uploaded.push(response.attachment);
      }
      setPendingAttachments((current) => [...current, ...uploaded]);
      const latestArtifacts = await loadArtifacts(currentContextId());
      // Don't redirect to dashboard - stay in chat
      if (uploaded.length > 0) {
        setMessages((current) => [
          ...current,
          {
            role: "assistant",
            content: "I added the uploaded material to the active session context.",
            search_logs: [],
            image_logs: [],
            render_blocks: buildArtifactReportBlocks(latestArtifacts),
          },
        ]);
      }
    } catch (uploadError) {
      setError(uploadError.message || "File upload failed.");
    } finally {
      setIsUploading(false);
    }
  }

  function handleOpenArtifact(artifact) {
    if (!artifact) {
      return;
    }

    if (artifact.kind === "research") {
      const metadata = artifact.metadata || {};
      const sources = Array.isArray(metadata.sources) ? metadata.sources : [];
      const researchBlock = {
        type: "research_result",
        payload: {
          query: metadata.query || artifact.title,
          provider: metadata.provider || "web",
          status: metadata.status || "completed",
          query_plan: metadata.query_variants || [],
          freshness: metadata.freshness || "",
          confidence: metadata.confidence || "medium",
          conflict: metadata.conflict || "",
          sources: sources.slice(0, 6).map((source) => ({
            title: source.title,
            url: source.url,
            domain: source.domain,
            snippet: source.snippet,
            freshness: source.page_excerpt || source.snippet || "",
            authority: source.domain?.includes("docs.") || source.domain?.endsWith(".gov") ? "official" : "standard",
          })),
        },
      };
      const reportBlock = {
        type: "report",
        payload: {
          title: artifact.title,
          summary: artifact.preview || "Reopened research artifact.",
          highlights: [
            metadata.provider || "web",
            metadata.freshness || "",
            metadata.confidence ? `${metadata.confidence} confidence` : "",
          ].filter(Boolean),
        },
      };
      const fileBlock = {
        type: "file_result",
        payload: {
          title: "Research sources",
          files: sources.slice(0, 6).map((source) => ({
            path: source.url,
            summary: [source.domain, source.snippet].filter(Boolean).join(" | "),
          })),
        },
      };
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: `Reopened saved research: ${metadata.query || artifact.title}`,
          search_logs: [],
          image_logs: [],
          render_blocks: [researchBlock, reportBlock, fileBlock],
        },
      ]);
      setActiveView("chat");
      return;
    }

    setMessages((current) => [
      ...current,
      {
        role: "assistant",
        content: `Opened artifact: ${artifact.title}`,
        search_logs: [],
        image_logs: [],
        render_blocks: [
          {
            type: "file_result",
            payload: {
              title: "Artifact preview",
              files: [
                {
                  title: artifact.title,
                  summary: artifact.preview,
                  artifact_id: artifact.id,
                },
              ],
            },
          },
        ],
      },
    ]);
    setActiveView("chat");
  }

  function appendAssistantMessage(content, renderBlocks = []) {
    setMessages((current) => [
      ...current,
      {
        role: "assistant",
        content,
        search_logs: [],
        image_logs: [],
        render_blocks: renderBlocks,
      },
    ]);
    setActiveView("chat");
  }

  async function runDashboardOperation(kind) {
    const sessionId = currentContextId();
    if (!sessionId) {
      setOperationState({ loading: false, message: "", error: "Start or open a chat session first." });
      return;
    }

    setOperationState({ loading: true, message: "", error: "" });
    try {
      if (kind === "session_analytics") {
        const result = await executeEvolutionTool("session_analytics", { session_id: sessionId });
        const blocks = [...(result.render_blocks || [])];
        if (result.visualization) {
          setActiveVisualization(result.visualization);
          blocks.unshift({ type: "visualization", payload: result.visualization });
        }
        appendAssistantMessage("Loaded the latest session analytics context.", blocks);
        setOperationState({ loading: false, message: "Session analytics loaded into chat.", error: "" });
        return;
      }

      if (kind === "reopen_latest_research") {
        const latestResearch = artifacts.find((artifact) => artifact.kind === "research");
        if (!latestResearch) {
          setOperationState({ loading: false, message: "", error: "No research memory is available in this session." });
          return;
        }
        const result = await executeEvolutionTool("reopen_artifact", {
          artifact_id: latestResearch.id,
          session_id: sessionId,
        });
        appendAssistantMessage(`Reopened research memory: ${latestResearch.title}`, result.render_blocks || []);
        setOperationState({ loading: false, message: "Latest research memory reopened in chat.", error: "" });
        return;
      }

      if (kind === "session_history") {
        const result = await executeEvolutionTool("session_history", { session_id: sessionId });
        const summary = [
          `Session history: ${result.message_count} messages in "${result.title}".`,
          "",
          ...(result.messages || []).map((item) => `- ${item.role}: ${item.content}`),
        ].join("\n");
        appendAssistantMessage(summary);
        setOperationState({ loading: false, message: "Conversation trace added to chat.", error: "" });
      }
    } catch (runError) {
      setOperationState({
        loading: false,
        message: "",
        error: runError.message || "Operation failed.",
      });
    }
  }

  function detectRequiredMode(text) {
    return classifyTaskIntent(text, mode).useAgent ? "agent" : "chat";
  }

  async function handleStreamEvent(data, assistantIndex) {
    if (data.type === "meta" && data.model) {
      setActiveModel(data.model);
    }
    if (data.type === "meta" && data.session_id) {
      setCurrentSessionId(data.session_id);
      await loadArtifacts(data.session_id);
    }
    if (data.type === "search" && data.log) {
      setMessages((current) =>
        current.map((message, index) =>
          index === assistantIndex
            ? { ...message, search_logs: [...(message.search_logs || []), data.log] }
            : message,
        ),
      );
    }
    if (data.type === "images" && data.log) {
      setMessages((current) =>
        current.map((message, index) =>
          index === assistantIndex
            ? { ...message, image_logs: [...(message.image_logs || []), data.log] }
            : message,
        ),
      );
    }
    if (data.type === "render" && data.block) {
      setMessages((current) =>
        current.map((message, index) =>
          index === assistantIndex
            ? {
                ...message,
                render_blocks: [...(message.render_blocks || []), data.block],
              }
            : message,
        ),
      );
    }
    if (data.type === "token") {
      setMessages((current) =>
        current.map((message, index) =>
          index === assistantIndex ? { ...message, content: `${message.content}${data.content}` } : message,
        ),
      );
      consumeOutputTokens(data.content);
    }
    if (data.type === "done") {
      await loadSessions();
      await loadProfile();
    }
    if (data.type === "error") {
      throw new Error(data.message || "Streaming failed");
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const value = input.trim();
    const requestMessage = value || "Please analyze the uploaded files.";
    if ((!value && pendingAttachments.length === 0) || isLoading || isUploading) {
      return;
    }

    const visualization = buildVisualizationSpec(requestMessage);
    const visualizationArtifacts = buildVisualizationArtifacts(visualization);
    if (visualization) {
      setActiveVisualization(visualization);
    }

    const requestMode = detectRequiredMode(requestMessage);
    consumeInputTokens(requestMessage);
    const assistantSeed = summarizeVisualization(visualization);
    const nextMessages = [
      ...messages,
      { role: "user", content: value || "Uploaded files", attachments: pendingAttachments },
      {
        role: "assistant",
        content: assistantSeed,
        search_logs: [],
        image_logs: [],
        visualization,
        render_blocks: visualization
          ? [{ type: "visualization", payload: visualization }, ...visualizationArtifacts]
          : [],
      },
    ];
    const assistantIndex = nextMessages.length - 1;
    const attachmentsForRequest = pendingAttachments;
    const conversation =
      currentSessionId && currentSessionId !== DRAFT_SESSION_ID
        ? []
        : nextMessages.slice(0, -2).filter((message) => message.role !== "assistant" || messages.length > 1);

    setMessages(nextMessages);
    setPendingAttachments([]);
    setInput("");
    setError("");
    setIsLoading(true);
    setActiveView("chat");

    try {
      const controller = new AbortController();
      abortRef.current = controller;
      const response = await fetch(api.chatStream, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: controller.signal,
        body: JSON.stringify({
          message: requestMessage,
          model: activeModel,
          effort: responseEffort,
          attachments: attachmentsForRequest,
          conversation,
          session_id: currentContextId(),
          mode: requestMode,
        }),
      });
      if (!response.ok || !response.body) {
        throw new Error("Backend request failed");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value: chunk, done } = await reader.read();
        if (done) {
          break;
        }
        buffer += decoder.decode(chunk, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.trim()) {
            continue;
          }
          await handleStreamEvent(JSON.parse(line), assistantIndex);
        }
      }

      if (buffer.trim()) {
        await handleStreamEvent(JSON.parse(buffer), assistantIndex);
      }
    } catch (requestError) {
      if (requestError.name === "AbortError") {
        setMessages((current) =>
          current.map((message, index) =>
            index === assistantIndex ? { ...message, content: `${message.content}\nGeneration stopped.`.trim() } : message,
          ),
        );
      } else {
        setError("The backend is unavailable. Start FastAPI and your local model services.");
        setMessages((current) =>
          current.map((message, index) =>
            index === assistantIndex
              ? {
                  ...message,
                  content: `${message.content}\nBackend connection failed. Start FastAPI on port 8000.`.trim(),
                }
              : message,
          ),
        );
      }
    } finally {
      abortRef.current = null;
      setIsLoading(false);
      await loadSessions();
      await loadArtifacts(currentContextId());
    }
  }

  function stopGeneration() {
    abortRef.current?.abort();
    abortRef.current = null;
    setIsLoading(false);
  }

  function handleVoiceCommand(payload) {
    if (payload.action === "dashboard") {
      setActiveView("dashboard");
      return;
    }
    if (payload.action === "chat") {
      setActiveView("chat");
      return;
    }
    if (payload.action === "rag_search" && payload.suggested_params.query) {
      setInput(payload.suggested_params.query);
      setActiveView("dashboard");
      return;
    }
    if (payload.transcript) {
      // Set the transcript as input and auto-submit
      setInput(payload.transcript);
      updateInputTokens(payload.transcript);
      
      // Auto-submit after a short delay to let user see what was captured
      setTimeout(() => {
        // Create a synthetic event to trigger submit
        const syntheticEvent = { preventDefault: () => {} };
        handleSubmit(syntheticEvent);
      }, 500);
    }
  }

  const displayedSessions =
    currentSessionId === null || currentSessionId === DRAFT_SESSION_ID
      ? [{ id: DRAFT_SESSION_ID, title: "New chat", preview: "Draft session" }, ...sessions]
      : sessions;

  return (
    <ChatLayout
      activeModel={activeModel}
      models={models}
      onModelChange={setActiveModel}
      responseEffort={responseEffort}
      onResponseEffortChange={setResponseEffort}
      sessions={displayedSessions}
      currentSessionId={currentSessionId || DRAFT_SESSION_ID}
      messageCount={messages.length}
      onResetChat={resetChat}
      onOpenSession={openSession}
      onDeleteSession={deleteSession}
      onClearHistory={clearHistory}
      customInstructions={customInstructions}
      memoryText={memoryText}
      onCustomInstructionsChange={setCustomInstructions}
      onMemoryTextChange={setMemoryText}
      onSaveProfile={saveProfile}
      profileSaved={profileSaved}
      activeView={activeView}
      onViewChange={setActiveView}
      chatContent={
        <div className="chat-view">
          <MessageList messages={messages} isLoading={isLoading} copiedKey={copiedKey} onCopyMessage={handleCopyMessage} />
          <Composer
            value={input}
            onChange={(nextValue) => {
              setInput(nextValue);
              updateInputTokens(nextValue);
            }}
            onSubmit={handleSubmit}
            onStop={stopGeneration}
            onUploadFiles={handleUploadFiles}
            onRemoveAttachment={(attachmentId) =>
              setPendingAttachments((current) => current.filter((attachment) => attachment.id !== attachmentId))
            }
            attachments={pendingAttachments}
            disabled={false}
            isLoading={isLoading}
            isUploading={isUploading}
            error={error}
            mode={mode}
            onModeChange={setMode}
            tokenUsage={tokenUsage}
            onVoiceCommand={handleVoiceCommand}
            activeModel={activeModel}
            onModelChange={setActiveModel}
            responseEffort={responseEffort}
            onResponseEffortChange={setResponseEffort}
            indexedFiles={artifacts}
            onViewIndexedFiles={() => setShowIndexedFiles(!showIndexedFiles)}
            onRefreshIndexedFiles={refreshIndexedFiles}
          />

          {/* Indexed Files Modal */}
          {showIndexedFiles && (
            <div className="indexed-files-modal" style={{
              position: 'fixed',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              background: 'white',
              borderRadius: '12px',
              padding: '24px',
              boxShadow: '0 4px 24px rgba(0,0,0,0.15)',
              zIndex: 1000,
              maxWidth: '600px',
              maxHeight: '80vh',
              overflow: 'auto',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <h3 style={{ margin: 0 }}>📁 Indexed Files ({artifacts.length})</h3>
                <button
                  onClick={() => setShowIndexedFiles(false)}
                  style={{
                    background: 'none',
                    border: 'none',
                    fontSize: '20px',
                    cursor: 'pointer',
                    padding: '4px 8px',
                  }}
                >
                  ✕
                </button>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {artifacts.map((artifact) => (
                  <div
                    key={artifact.id}
                    style={{
                      padding: '12px',
                      background: '#f5f5f5',
                      borderRadius: '8px',
                      cursor: 'pointer',
                    }}
                    onClick={() => {
                      handleOpenArtifact(artifact);
                      setShowIndexedFiles(false);
                    }}
                  >
                    <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>{artifact.title}</div>
                    <div style={{ fontSize: '12px', color: '#666' }}>{artifact.kind}</div>
                    {artifact.preview && (
                      <div style={{ fontSize: '12px', color: '#888', marginTop: '4px' }}>
                        {artifact.preview.substring(0, 100)}...
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
          {showIndexedFiles && (
            <div
              className="indexed-files-modal-backdrop"
              onClick={() => setShowIndexedFiles(false)}
              style={{
                position: 'fixed',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                background: 'rgba(0,0,0,0.5)',
                zIndex: 999,
              }}
            />
          )}
        </div>
      }
      dashboardContent={
        <DashboardView
          currentSessionId={currentContextId()}
          tools={tools}
          capabilities={capabilities}
          stats={dashboardStats}
          artifacts={artifacts}
          visualization={activeVisualization}
          operationState={operationState}
          onArtifactRefresh={() => loadArtifacts(currentContextId())}
          onOpenArtifact={handleOpenArtifact}
          onRunOperation={runDashboardOperation}
        />
      }
      terminalContent={<TerminalPanel visible={true} />}
    />
  );
}
