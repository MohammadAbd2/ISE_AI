import { useEffect, useRef, useState } from "react";
import ChatLayout from "./components/ChatLayout";
import Composer from "./components/Composer";
import DashboardView from "./components/DashboardView";
import DocumentationView from "./components/DocumentationView";
import MessageList from "./components/MessageList";
import TerminalPanel from "./components/TerminalPanel";
import PlatformPanel from "./components/PlatformPanel";
import AutonomousDevPlatformV4Panel from "./components/AutonomousDevPlatformV4Panel";
import AutonomousIntelligenceV5Panel from "./components/AutonomousIntelligenceV5Panel";
import AgenticVisualPanel from "./components/AgenticVisualPanel";
import SuperAgentPanel from "./components/SuperAgentPanel";
import UXIntelligenceWorkspace from "./components/UXIntelligenceWorkspace";
import EliteAgentCommandCenter from "./components/EliteAgentCommandCenter";
import AGISystemV3Panel from "./components/AGISystemV3Panel";
import AGISystemV4Panel from "./components/AGISystemV4Panel";
import DailyProgrammingAGIPanel from "./components/DailyProgrammingAGIPanel";
import MaximumDynamicAgentPanel from "./components/MaximumDynamicAgentPanel";
import { api, executeEvolutionTool, fetchJson, uploadToolCode, enableTool, disableTool, deleteTool, saveResponsePreference, classifyIntentRemote, deleteArtifact } from "./lib/api";
import {
  buildVisualizationArtifacts,
  buildVisualizationSpec,
  summarizeVisualization,
} from "./lib/visualization";
import { classifyTaskIntent } from "./lib/taskIntent";

const DEFAULT_MODEL = "qwen2.5-coder:14b";
const DRAFT_SESSION_ID = "draft-chat";

function createDraftContextId() {
  if (globalThis.crypto?.randomUUID) {
    return `draft:${globalThis.crypto.randomUUID()}`;
  }
  return `draft:${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}


function detectDirectFileArtifactRequest(text, routeDecision = {}) {
  const raw = String(text || "");
  const lower = raw.toLowerCase();
  const routeExt = routeDecision.suggested_extension || "";
  const extMatch = lower.match(/\b(pdf|docx|txt|md|markdown|json|js|jsx|ts|tsx|html|css|py)\s+file\b|\bfile\s+.*\b(pdf|docx|txt|md|markdown|json|js|jsx|ts|tsx|html|css|py)\b|\bdownloadable\s+(pdf|docx|txt|md|markdown|json|js|jsx|ts|tsx|html|css|py)\b/);
  const extToken = routeExt || (extMatch ? `.${(extMatch[1] || extMatch[2] || extMatch[3] || "txt").replace("markdown", "md")}` : "");
  if (!extToken) return null;
  const asksFile = routeDecision.route === "artifact_generate" || /\b(create|make|generate|put|write|save).{0,80}\b(pdf|docx|txt|md|markdown|json|js|jsx|ts|tsx|html|css|py)\b|\bdownloadable\b|\bgive me .*file\b/.test(lower);
  const asksApp = /\b(app|website|frontend|backend|project|component|route|endpoint|full stack|preview)\b/.test(lower);
  if (!asksFile || asksApp) return null;
  const quotedDouble = raw.match(/["“]([\s\S]{1,20000})["”]/);
  const quotedSingleAfterToBe = raw.match(/(?:content\s+to\s+be|to\s+be|content\s*=|message\s*->)\s*'([\s\S]{1,20000})'/i);
  const arrow = raw.match(/(?:message|content)\s*(?:->|:|=)\s*["“']?([\s\S]{1,20000}?)["”']?\s+(?:into|in|to)\s+(?:a\s+)?(?:pdf|docx|txt|md|markdown|json|js|jsx|ts|tsx|html|css|py)/i);
  const content = (quotedDouble?.[1] || quotedSingleAfterToBe?.[1] || arrow?.[1] || raw.replace(/^(create|make|generate|put|write|save)\b/i, "").trim() || "Generated file").trim();
  const cleanExt = extToken.startsWith(".") ? extToken : `.${extToken}`;
  const baseName = cleanExt === ".pdf" ? "generated-message" : "generated-file";
  return { extension: cleanExt, filename: `${baseName}${cleanExt}`, title: `${cleanExt.slice(1).toUpperCase()} file`, content };
}


function extractFirstUrl(text) {
  return String(text || "").match(/https?:\/\/[^\s)]+/i)?.[0] || "";
}
function extractHtmlPayload(text) {
  const raw = String(text || "");
  const quoted = raw.match(/["“]([\s\S]{1,20000})["”]/)?.[1] || raw.match(/'([\s\S]{1,20000})'/)?.[1] || "Hi from Agent";
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Agent Preview</title>
  <style>
    body { margin: 0; min-height: 100vh; display: grid; place-items: center; font-family: Inter, Arial, sans-serif; background: #f8fafc; }
    .dev-element { padding: 32px 42px; border-radius: 24px; background: white; color: #2563eb; box-shadow: 0 24px 80px rgba(15, 23, 42, 0.16); font-size: clamp(2rem, 6vw, 4rem); font-weight: 900; }
  </style>
</head>
<body>
  <div class="dev-element">${quoted.replace(/</g, "&lt;").replace(/>/g, "&gt;")}</div>
</body>
</html>`;
}
function extractLikelyFilename(text) {
  return String(text || "").match(/([A-Za-z0-9_.-]+\.(?:html|txt|pdf|docx|js|jsx|ts|tsx|css|json|md|py))/i)?.[1] || "index.html";
}

function shouldUseUnifiedAgent(text, requestMode) {
  const lower = String(text || "").toLowerCase();
  if (requestMode === "agent") return true;
  return /\b(create|build|implement|fix|debug|rewrite|update|improve|backend|frontend|full stack|website|component|zip|preview|merge|sandbox|develop your|self[- ]?improve)\b/.test(lower);
}

async function resolveTaskRoute(text, requestMode, hasAttachments) {
  try {
    return await fetchJson(api.agentRouteTask, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, mode: requestMode || "auto", has_attachments: Boolean(hasAttachments) }),
    });
  } catch {
    const useAgent = shouldUseUnifiedAgent(text, requestMode) && !hasAttachments;
    return {
      route: useAgent ? "agent_execute" : "memory_chat",
      requires_agent: useAgent,
      export_zip: /\b(zip|download|export|give me the file)\b/i.test(text),
      confidence: useAgent ? 0.62 : 0.5,
      reason: "Local fallback router used because backend routing check failed.",
    };
  }
}


function buildDeveloperConsoleV3Blocks({ request, routeDecision, agentRun, agiRun }) {
  const timeline = Array.isArray(agentRun?.timeline) ? agentRun.timeline : [];
  const steps = Array.isArray(agentRun?.plan?.steps) ? agentRun.plan.steps : (Array.isArray(agiRun?.steps) ? agiRun.steps : []);
  const files = Array.from(new Set([
    ...(Array.isArray(agentRun?.ui_contract?.files_changed) ? agentRun.ui_contract.files_changed : []),
    ...(Array.isArray(agiRun?.files) ? agiRun.files : []),
    ...(Array.isArray(agiRun?.files_changed) ? agiRun.files_changed : []),
  ].map((file) => typeof file === "string" ? file : file?.path).filter(Boolean)));
  const validation = agiRun?.validation || agentRun?.execution?.validation || {};
  const failed = Array.isArray(validation.failed) ? validation.failed : [];
  const preview = agiRun?.preview || {};
  const exportInfo = agentRun?.ui_contract?.export || agiRun?.export || {};
  const command = preview.command || agiRun?.preview_command || "";
  const commandEvents = timeline.filter((event) => /executor|verifier|preview|export/i.test(event.agent || ""));
  const terminalCommands = [
    command ? { title: "Preview command", cwd: preview.cwd || "sandbox/frontend", command, status: "ready", output: preview.url ? `Preview available at ${preview.url}` : "Command prepared." } : null,
    ...(Array.isArray(agiRun?.verification_commands) ? agiRun.verification_commands.map((item) => ({
      title: "Verification command",
      cwd: item.cwd || "sandbox",
      command: item.command || String(item),
      status: item.exit_code === 0 || item.passed ? "completed" : "ready",
      output: item.output || item.stdout || item.evidence || "Verification command registered.",
      stderr: item.stderr || "",
      exit_code: item.exit_code,
    })) : []),
    ...commandEvents.slice(0, 4).map((event) => ({
      title: event.agent || "Agent event",
      cwd: "agent-runtime",
      command: event.message || "agent step",
      status: event.status || "completed",
      output: event.data ? JSON.stringify(event.data, null, 2).slice(0, 3000) : "",
    })),
  ].filter(Boolean);
  const phases = [
    { id: "plan", label: "Plan", status: timeline.some((e) => /planner/i.test(e.agent || "")) ? "completed" : "pending" },
    { id: "execute", label: "Execute", status: timeline.some((e) => /executor/i.test(e.agent || "")) ? "completed" : "pending" },
    { id: "verify", label: "Verify", status: failed.length ? "failed" : validation.passed ? "completed" : "pending" },
    { id: "repair", label: "Repair", status: Array.isArray(agiRun?.repairs) && agiRun.repairs.length ? "completed" : failed.length ? "ready" : "skipped" },
    { id: "export", label: "Export", status: exportInfo?.artifact_id || exportInfo?.path ? "completed" : "pending" },
  ];
  return [
    { type: "live_thinking_stream", payload: { title: "Thinking", status: agentRun?.status || agiRun?.status || "completed", request, events: timeline.map((event) => ({ label: event.agent, status: event.status, message: event.message, progress: event.progress, timestamp: event.timestamp })), summary: routeDecision?.reason || "Agent selected the developer execution pipeline." } },
    { type: "interactive_terminal", payload: { title: "Terminal / tool calls", streaming: false, commands: terminalCommands, actions: ["copy", "rerun-planned", "cancel-planned"] } },
    { type: "editable_agent_plan", payload: { title: "Editable Agent plan", readonly: true, note: "Plan editing UI is enabled. Backend approval/reorder actions are the next transport step.", steps: steps.map((step, index) => ({ id: step.id || `step-${index + 1}`, title: step.title || step.description || step.agent || `Step ${index + 1}`, detail: step.description || step.title || "", status: step.status || "planned" })) } },
    { type: "file_explorer", payload: { title: "Generated / touched files", root: agiRun?.sandbox_path || agiRun?.output_root || "AGI_Output", files: files.map((file) => ({ path: file, status: "changed", summary: "Generated or touched by Agent" })), artifact: exportInfo } },
    { type: "agent_loop_visualizer", payload: { title: "Agent loop", phases, retry_count: Array.isArray(agiRun?.repairs) ? agiRun.repairs.length : 0 } },
    { type: "smart_error_explainer", payload: { title: failed.length ? "Issues found" : "No blocking errors", errors: failed, stderr: terminalCommands.map((cmd) => cmd.stderr).filter(Boolean).join("\n"), explanation: failed.length ? "The verifier reported blocked gates. Review the failed gates, then rerun or let the RepairAgent patch them." : "The run did not report blocking validation errors.", proposed_fix: failed.length ? "Route back through RepairAgent, then rerun verification before export." : "No repair required." } },
    { type: "developer_controls", payload: { title: "Developer controls", autonomy_level: "safe", retry_limit: 2, sandbox: true, preview_enabled: Boolean(preview.url || preview.command), export_enabled: Boolean(exportInfo?.artifact_id || exportInfo?.path), destructive_actions_require_approval: true } },
    { type: "self_improvement_panel", payload: { title: "Self-improvement notes", learned: ["Prefer direct file artifacts when the user asks for PDF/DOCX/TXT output.", "Show command and output evidence in chat instead of one noisy generic run card.", "Keep Agent and AGI merged under the single Agent experience."], proposed_upgrades: ["Stream backend Agent events over NDJSON/SSE into these v3 blocks.", "Add approve/reorder endpoints for editable plan steps.", "Add file-open and file-save endpoints for the explorer."], approval_required: true } },
  ];
}

function summarizeAgentRun(run) {
  if (!run) return "Agent run failed before producing evidence.";
  const failed = run.validation?.failed || [];
  const isReady = run.export_allowed || run.status === "completed" || run.validation?.passed;
  if (isReady && failed.length === 0) return `Agent run verified. ${run.summary || "Preview/export evidence is ready."}`;
  return run.summary || `Agent run needs repair: ${failed.join(", ") || run.status || "unknown state"}`;
}

function normalizeAgentRunBlock(run) {
  const progress = Number(run?.progress ?? (Array.isArray(run?.events) && run.events.length ? run.events.at(-1).progress : 0));
  const failed = run?.validation?.failed || [];
  return {
    status: run?.status || (run?.export_allowed ? "complete" : failed.length === 0 && run?.validation?.passed ? "verified" : "needs repair"),
    progress,
    steps: run?.steps || [],
    files_changed: run?.files || [],
    preview: run?.preview || {},
    export: run?.export || {},
    validation: run?.validation || {},
    repairs: run?.repairs || [],
    verification_commands: run?.verification_commands || [],
    capabilities: run?.capabilities || [],
    working_directory: run?.working_directory || {},
    file_contents: run?.file_contents || {},
  };
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
    content: "ISE AI is online. Chat normally or ask the unified Agent to plan, edit, debug, search, generate files, or work on projects.",
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
  const [backendStatus, setBackendStatus] = useState({ state: "checking", label: "Connecting", detail: "Checking backend…" });
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
    refreshBackendStatus();
    const backendStatusTimer = window.setInterval(refreshBackendStatus, 5000);
    loadModels();
    loadSessions();
    loadProfile();
    loadDashboard();
    return () => {
      window.clearInterval(backendStatusTimer);
      copiedTimeoutRef.current && clearTimeout(copiedTimeoutRef.current);
      abortRef.current?.abort();
    };
  }, []);

  useEffect(() => {
    loadArtifacts(currentContextId());
  }, [currentSessionId, draftContextId]);

  async function refreshBackendStatus() {
    try {
      const data = await fetchJson(api.agentHealth);
      const degraded = data?.status && data.status !== "ok";
      setBackendStatus({
        state: degraded ? "degraded" : "online",
        label: degraded ? "Agent degraded" : "Agent online",
        detail: degraded ? (data?.memory?.error || "Backend responded with warnings") : "Backend connected · routing active",
      });
    } catch {
      setBackendStatus({
        state: "offline",
        label: "Backend offline",
        detail: "Trying to connect to port 8000…",
      });
    }
  }

  async function loadModels() {
    try {
      const [modelsData, hardwareData] = await Promise.all([
        fetchJson(api.models),
        fetchJson("/api/hardware/profile").catch(() => ({})),
      ]);
      
      if (Array.isArray(modelsData.models) && modelsData.models.length > 0) {
        setModels(modelsData.models);
        
        // Priority: 1. Hardware recommended model, 2. Current selection (if valid), 3. First available
        const recommended = hardwareData.recommended_model;
        setActiveModel((current) => {
          if (recommended && modelsData.models.includes(recommended)) return recommended;
          if (modelsData.models.includes(current)) return current;
          return modelsData.models[0];
        });
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

  async function handleResponsePreference(style, message) {
    try {
      await saveResponsePreference(style, message?.content || "");
      appendAssistantMessage(
        style === "concise"
          ? "Preference saved. I’ll keep future replies shorter, sharper, and more direct."
          : "Preference saved. I’ll use clearer structure and stronger visual hierarchy in future replies.",
      );
    } catch {
      setError("Failed to save response preference.");
    }
  }

  async function submitMessage(requestMessage, options = {}) {
    const {
      displayMessage = requestMessage,
      attachmentsOverride = pendingAttachments,
      forceMode = null,
      skipInputReset = false,
    } = options;

    const trimmedDisplay = (displayMessage || "").trim();
    const normalizedRequest = (requestMessage || "").trim() || "Please continue.";
    if ((!trimmedDisplay && attachmentsOverride.length === 0) || isLoading || isUploading) {
      return;
    }

    const intent = forceMode
      ? { kind: forceMode === "agent" ? "coding" : "chat", use_agent: forceMode === "agent" }
      : await detectIntent(normalizedRequest);
    const requestMode = forceMode || (intent.use_agent ? "agent" : "chat");
    const visualization = !intent.use_agent ? buildVisualizationSpec(normalizedRequest) : null;
    const visualizationArtifacts = buildVisualizationArtifacts(visualization);

    consumeInputTokens(normalizedRequest);

    const nextMessages = [
      ...messages,
      { role: "user", content: trimmedDisplay || normalizedRequest, attachments: attachmentsOverride },
    ];

    if (visualization && requestMode !== "coding" && attachmentsOverride.length === 0) {
      setMessages([
        ...nextMessages,
        {
          role: "assistant",
          content: summarizeVisualization(visualization),
          search_logs: [],
          image_logs: [],
          visualization,
          render_blocks: visualizationArtifacts,
        },
      ]);
      if (!skipInputReset) {
        setInput("");
      }
      setPendingAttachments([]);
      setError("");
      setActiveView("chat");
      return;
    }

    if (visualization) {
      setActiveVisualization(visualization);
    }

    const assistantSeed = summarizeVisualization(visualization);
    const fullNextMessages = [
      ...nextMessages,
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
    const assistantIndex = fullNextMessages.length - 1;
    const conversation =
      currentSessionId && currentSessionId !== DRAFT_SESSION_ID
        ? []
        : fullNextMessages.slice(0, -2).filter((message) => message.role !== "assistant" || messages.length > 1);

    setMessages(fullNextMessages);
    setPendingAttachments([]);
    if (!skipInputReset) {
      setInput("");
    }
    setError("");
    setIsLoading(true);
    setActiveView("chat");

    const routeDecision = await resolveTaskRoute(normalizedRequest, requestMode, attachmentsOverride.length > 0);
    const dynamicOutputPlan = await fetchJson(api.agenticVisualDynamicOutputPlan, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task: normalizedRequest }),
    }).catch(() => null);

    if (routeDecision.route === "debug_repair") {
      try {
        const repair = await fetchJson(api.agenticVisualDebugSelfHeal, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ error_text: normalizedRequest, context: "chat debug request" }),
        });
        setMessages((current) => current.map((message, index) => index === assistantIndex ? {
          ...message,
          content: "DebuggingAgent analyzed the error and prepared a self-healing repair plan.",
          render_blocks: [
            { type: "thinking_trace", payload: { title: "Thinking", summary: "DebuggingAgent selected", steps: ["Classified error", "Created repair steps", "Prepared rerun policy"], collapsed: true } },
            repair.render_block,
          ].filter(Boolean),
        } : message));
      } catch (debugError) {
        setMessages((current) => current.map((message, index) => index === assistantIndex ? { ...message, content: `DebuggingAgent failed: ${debugError.message || debugError}` } : message));
      } finally { setIsLoading(false); }
      return;
    }

    if (routeDecision.route === "file_location_lookup") {
      try {
        const filename = extractLikelyFilename(normalizedRequest);
        const locationResult = await fetchJson(`${api.agentLatestFileLocation}?filename=${encodeURIComponent(filename)}`);
        const files = (locationResult.locations || []).map((item) => ({ path: item.path, kind: "located file", summary: `${item.relative_path} · ${(item.size_bytes / 1024).toFixed(1)} KB`, content: item.preview }));
        setMessages((current) => current.map((message, index) => index === assistantIndex ? {
          ...message,
          content: locationResult.message || `Searched for ${filename}.`,
          render_blocks: [
            { type: "thinking_trace", payload: { title: "Thinking", summary: "Looked up the file location instead of starting a new Agent build.", steps: [`Target file: ${filename}`, `Matches: ${files.length}`], collapsed: true } },
            { type: "visual_file_gallery", payload: { title: `Locations for ${filename}`, files } },
          ],
        } : message));
      } catch (lookupError) {
        setMessages((current) => current.map((message, index) => index === assistantIndex ? { ...message, content: `File location lookup failed: ${lookupError.message || lookupError}` } : message));
      } finally { setIsLoading(false); }
      return;
    }

    if (routeDecision.route === "figma_design") {
      try {
        const url = extractFirstUrl(normalizedRequest);
        const endpoint = url ? api.figmaAgentInspect : api.figmaAgentPrototype;
        const payload = url ? { url, prompt: normalizedRequest } : { prompt: normalizedRequest, title: "Agent prototype" };
        setMessages((current) => current.map((message, index) => index === assistantIndex ? {
          ...message,
          content: url ? "Inspecting Figma/design URL and preparing design-to-code brief…" : "Creating a browser-previewable prototype from your prompt…",
          render_blocks: [{ type: "thinking_trace", payload: { title: "Thinking", summary: "DesignAgent selected", steps: [url ? `Source URL: ${url}` : "Prompt-to-prototype mode", "Extract design intent", "Prepare visual render blocks"] } }],
        } : message));
        const result = await fetchJson(endpoint, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
        setMessages((current) => current.map((message, index) => index === assistantIndex ? {
          ...message,
          content: result.status === "generated" ? "Prototype generated and previewed in chat." : "Design brief prepared for code generation.",
          render_blocks: [
            { type: "thinking_trace", payload: { title: "Thinking", summary: `${result.agent || "DesignAgent"} completed`, steps: ["Normalized design input", "Extracted tokens/layout", "Prepared implementation-ready visual blocks"], collapsed: true } },
            ...(result.render_blocks || []),
          ],
        } : message));
      } catch (designError) {
        setMessages((current) => current.map((message, index) => index === assistantIndex ? { ...message, content: `DesignAgent failed: ${designError.message || designError}` } : message));
      } finally { setIsLoading(false); }
      return;
    }

    if (routeDecision.route === "static_html_preview") {
      try {
        const result = await fetchJson(api.agenticVisualStaticHtmlGenerate, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ session_id: currentContextId(), filename: "index.html", message: normalizedRequest }) });
        setMessages((current) => current.map((message, index) => index === assistantIndex ? {
          ...message,
          content: "Created index.html and rendered the preview directly in chat.",
          render_blocks: [
            { type: "thinking_trace", payload: { title: "Thinking", summary: "Generated direct static HTML instead of a generic React app.", steps: ["Created index.html", "Verified artifact write", "Rendered browser preview with srcDoc"], collapsed: true } },
            ...(result.render_blocks || []),
          ],
        } : message));
        await loadArtifacts(currentContextId());
      } catch (htmlError) {
        setMessages((current) => current.map((message, index) => index === assistantIndex ? { ...message, content: `Static HTML generation failed: ${htmlError.message || htmlError}` } : message));
      } finally { setIsLoading(false); }
      return;
    }

    const directArtifact = attachmentsOverride.length === 0 ? detectDirectFileArtifactRequest(normalizedRequest, routeDecision) : null;

    if (directArtifact) {
      try {
        setMessages((current) => current.map((message, index) =>
          index === assistantIndex
            ? {
                ...message,
                content: `Creating ${directArtifact.extension.toUpperCase()} downloadable artifact…`,
                render_blocks: [{ type: "thinking_trace", payload: { title: "Thinking", summary: "Creating the requested downloadable file", steps: ["Detected direct artifact request", `Preparing ${directArtifact.filename}`, "Skipping app preview because the expected result is a file"] } }],
              }
            : message,
        ));
        const generatedFile = await fetchJson(api.devxGenerateFile, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: currentContextId(),
            filename: directArtifact.filename,
            extension: directArtifact.extension,
            title: directArtifact.title,
            content: directArtifact.content,
          }),
        });
        setMessages((current) => current.map((message, index) =>
          index === assistantIndex
            ? {
                ...message,
                content: `Created ${generatedFile.filename || directArtifact.filename}.`,
                render_blocks: [
                  { type: "thinking_trace", payload: { title: "Thinking", summary: "File generated and registered as a downloadable artifact", steps: ["Generated file bytes", "Stored artifact metadata", "Verified full file content", "Prepared download card"], collapsed: true } },
                  { type: "download_card", payload: {
                    title: generatedFile.filename || directArtifact.filename,
                    artifact_id: generatedFile.artifact_id,
                    download_url: generatedFile.download_url,
                    content_type: generatedFile.content_type,
                    extension: generatedFile.extension || directArtifact.extension,
                    icon: generatedFile.icon,
                    size_bytes: generatedFile.size_bytes,
                    sha256: generatedFile.sha256,
                    file_count: 1,
                    write_verified: generatedFile.write_verified,
                  } },
                  { type: "file_preview", payload: {
                    title: "Generated file content",
                    path: generatedFile.filename || directArtifact.filename,
                    language: directArtifact.extension.replace(".", ""),
                    content: directArtifact.content,
                  } },
                ],
              }
            : message,
        ));
        await loadArtifacts(currentContextId());
      } catch (artifactError) {
        setError(artifactError.message || "File generation failed.");
        setMessages((current) => current.map((message, index) =>
          index === assistantIndex
            ? { ...message, content: `File generation failed: ${artifactError.message || artifactError}` }
            : message,
        ));
      } finally {
        setIsLoading(false);
      }
      return;
    }

    if (routeDecision.requires_agent && attachmentsOverride.length === 0) {

      try {
        setMessages((current) => current.map((message, index) =>
          index === assistantIndex
            ? {
                ...message,
                content: `Agent selected: ${routeDecision.reason || "planning, memory lookup, execution, verification"}`,
                render_blocks: [{ type: "thinking_trace", payload: { title: "Thinking", summary: routeDecision.reason || "Choosing the best execution path", steps: ["Inspecting request intent", `Route: ${routeDecision.route}`, `Confidence: ${Math.round((routeDecision.confidence || 0) * 100)}%`] } }],
              }
            : message,
        ));
        let agentRun;
        let agiRun;
        try {
          agentRun = await fetchJson(api.unifiedAgentExecute, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ task: normalizedRequest, source_path: null, max_attempts: 4 }),
          });
          agiRun = agentRun.execution || agentRun;
        } catch (unifiedError) {
          const agiResponse = await fetch(api.agentPlanExecute, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            request: normalizedRequest,
            source_path: null,
            export_zip: Boolean(routeDecision.export_zip),
            // Backend selects a conflict-safe generated-app preview port.
            session_id: currentContextId(),
          }),
        });
        if (!agiResponse.ok) throw new Error(await agiResponse.text());
          agentRun = await agiResponse.json();
          agentRun.fallback_reason = unifiedError.message || String(unifiedError);
          agiRun = agentRun.execution || agentRun;
        }
        setMessages((current) => current.map((message, index) =>
          index === assistantIndex
            ? {
                ...message,
                content: agentRun.summary || summarizeAgentRun(agiRun),
                render_blocks: [
                  { type: "thinking_trace", payload: { title: "Thinking", summary: "Agent planned, executed, verified, and prepared results", steps: (agentRun.timeline || agentRun.events || []).map((event) => `${event.agent || event.phase || "Agent"}: ${event.message || event.status}`).slice(0, 8), collapsed: false } },
                  ...(Array.isArray(agentRun.render_blocks) ? agentRun.render_blocks : []),
                  ...(dynamicOutputPlan?.render_blocks || []),
                  { type: "agent_timeline", payload: {
                    run_id: agentRun.run_id || agiRun.run_id || "agent-run",
                    status: agentRun.status || agiRun.status || "completed",
                    events: agentRun.timeline || agentRun.events || [],
                    artifacts: agentRun.ui_contract?.artifact_id ? [agentRun.ui_contract.artifact_id] : [],
                    files: agentRun.ui_contract?.files_changed || [],
                    title: "Agent execution",
                  }},
                  { type: "plan_result", payload: {
                    title: "Agent plan",
                    summary: agentRun.plan_summary || "Planner, memory, execution, verification",
                    steps: agentRun.plan?.steps || agiRun.steps || [],
                  }},
                  ...(Array.isArray(agentRun.ui_contract?.blocks) ? agentRun.ui_contract.blocks.filter((block) => !["agent_timeline"].includes(block?.type)) : []),
                  { type: "programming_agi_run", payload: normalizeAgentRunBlock({ ...agiRun, export: agentRun.ui_contract?.export || agiRun.export, folder_listing: agentRun.ui_contract?.folder_listing || agiRun.folder_listing, file_content: agentRun.ui_contract?.file_content || agiRun.file_content }) },
                  ...buildDeveloperConsoleV3Blocks({ request: normalizedRequest, routeDecision, agentRun, agiRun }),
                ].filter(Boolean),
              }
            : message,
        ));
      } catch (runError) {
        setError(runError.message || "Agent run failed.");
        setMessages((current) => current.map((message, index) =>
          index === assistantIndex
            ? { ...message, content: `Agent execution failed: ${runError.message || runError}` }
            : message,
        ));
      } finally {
        setIsLoading(false);
        await loadSessions();
        await loadArtifacts(currentContextId());
      }
      return;
    }

    try {
      const controller = new AbortController();
      abortRef.current = controller;
      const response = await fetch(api.chatStream, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: controller.signal,
        body: JSON.stringify({
          message: normalizedRequest,
          model: activeModel,
          effort: responseEffort,
          attachments: attachmentsOverride,
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
        const errorMsg = "The backend connection was interrupted. This usually happens if the server is restarting or a request timed out.";
        setError(errorMsg);
        setMessages((current) =>
          current.map((message, index) =>
            index === assistantIndex
              ? {
                  ...message,
                  content: `${message.content}\n⚠️ Backend connection failed. Please try again or check if the server is running on port 8000.`.trim(),
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

  async function handleContinueMessage() {
    return submitMessage(
      "Continue from your last answer exactly where you stopped. Do not restart from the beginning. Keep it concise and complete the unfinished work only.",
      {
        displayMessage: "Continue",
        attachmentsOverride: [],
        forceMode: "chat",
      },
    );
  }

  async function handleExecutePacket(packet) {
    if (!packet?.ready) {
      return;
    }

    let executionPacket = packet;

    try {
      const freshness = await fetchJson(api.executionPacketFreshness, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          packet_id: packet.packet_id || "",
          generated_at: packet.generated_at || "",
          ready: Boolean(packet.ready),
        }),
      });
      if (freshness?.is_stale && freshness?.latest_packet?.ready) {
        executionPacket = freshness.latest_packet;
        if (executionPacket.packet_id !== packet.packet_id) {
          appendAssistantMessage(
            `I refreshed the remediation packet before execution. Using packet ${executionPacket.packet_id}.`,
          );
        } else if (freshness.reason) {
          appendAssistantMessage(
            `I revalidated the remediation packet before execution: ${freshness.reason}`,
          );
        }
      }
    } catch {
      // Keep the existing packet if freshness check fails.
    }

    try {
      setMessages((current) => [
        ...current,
        {
          role: "user",
          content: `Start remediation: ${executionPacket.subsystem || "execution packet"}`,
          search_logs: [],
          image_logs: [],
          render_blocks: [],
        },
      ]);
      setActiveView("chat");

      const result = await fetchJson(api.executionPacketExecute, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ready: Boolean(executionPacket.ready),
          packet_id: executionPacket.packet_id || "",
          subsystem: executionPacket.subsystem || "",
          summary: executionPacket.summary || "",
          targets: executionPacket.targets || [],
          checks: executionPacket.checks || [],
          verification: executionPacket.verification || [],
          steps: executionPacket.steps || [],
          agent_prompt: executionPacket.agent_prompt || "",
          generated_at: executionPacket.generated_at || "",
          eval_score: executionPacket.eval_score || 0,
          session_id: currentContextId(),
        }),
      });
      appendAssistantMessage(result.reply || "Remediation executed.", result.render_blocks || []);
      return;
    } catch {
      appendAssistantMessage("Remediation execution failed before the isolated run could finish.");
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

  async function handleExecuteTool(toolName) {
    setOperationState({ loading: true, message: `Executing ${toolName}...`, error: "" });
    try {
      const result = await executeEvolutionTool(toolName, { sandbox: true });
      appendAssistantMessage(`Tool ${toolName} executed.`, [
        { type: "report", payload: { title: `Tool ${toolName}`, summary: JSON.stringify(result).slice(0, 800) } },
      ]);
      await loadDashboard();
      setOperationState({ loading: false, message: `Tool ${toolName} executed.`, error: "" });
    } catch (e) {
      setOperationState({ loading: false, message: "", error: e.message || String(e) });
    }
  }

  async function handleUploadToolCode(toolName, code) {
    setOperationState({ loading: true, message: `Uploading code for ${toolName}...`, error: "" });
    try {
      const res = await uploadToolCode(toolName, code);
      await loadDashboard();
      setOperationState({ loading: false, message: `Code uploaded for ${toolName}`, error: "" });
      appendAssistantMessage(`Uploaded code for ${toolName}.`, []);
      return res;
    } catch (e) {
      setOperationState({ loading: false, message: "", error: e.message || String(e) });
      throw e;
    }
  }

  async function handleToggleTool(tool) {
    setOperationState({ loading: true, message: `${tool.enabled ? 'Disabling' : 'Enabling'} ${tool.name}...`, error: "" });
    try {
      const res = tool.enabled ? await disableTool(tool.name) : await enableTool(tool.name);
      await loadDashboard();
      setOperationState({ loading: false, message: res.status === 'success' ? 'Updated' : 'Failed', error: res.error || "" });
      return res;
    } catch (e) {
      setOperationState({ loading: false, message: "", error: e.message || String(e) });
      throw e;
    }
  }

  async function handleDeleteTool(toolName) {
    if (!window.confirm(`Delete tool ${toolName}? This will remove persisted code if present.`)) return;
    setOperationState({ loading: true, message: `Deleting ${toolName}...`, error: "" });
    try {
      const res = await deleteTool(toolName);
      await loadDashboard();
      setOperationState({ loading: false, message: res.status === 'success' ? 'Deleted' : 'Failed', error: res.error || "" });
      appendAssistantMessage(`Tool ${toolName} deleted.`, []);
      return res;
    } catch (e) {
      setOperationState({ loading: false, message: "", error: e.message || String(e) });
      throw e;
    }
  }

  async function detectIntent(text) {
    try {
      return await classifyIntentRemote(text, mode);
    } catch {
      const fallback = classifyTaskIntent(text, mode);
      return {
        kind: fallback.kind,
        confidence: 0.5,
        use_agent: fallback.useAgent,
        use_visualization: fallback.kind === "visualization",
        use_research: fallback.kind === "research",
        use_project_context: fallback.kind === "project_analysis",
        use_filesystem: fallback.kind === "filesystem",
      };
    }
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
                render_blocks:
                  data.block.type === "coding_progress" || data.block.type === "research_progress"
                    ? [
                        ...(message.render_blocks || []).filter((block) => block?.type !== data.block.type),
                        data.block,
                      ]
                    : data.block.type === "coding_result"
                      ? [
                          ...(message.render_blocks || []).filter((block) => block?.type !== "coding_progress" && block?.type !== "coding_result"),
                          data.block,
                        ]
                      : data.block.type === "agent_timeline"
                      ? (() => {
                          const existing = (message.render_blocks || []).find((block) => block?.type === "agent_timeline" && block?.payload?.run_id === data.block?.payload?.run_id);
                          if (!existing) return [...(message.render_blocks || []), data.block];
                          return (message.render_blocks || []).map((block) => {
                            if (block?.type !== "agent_timeline" || block?.payload?.run_id !== data.block?.payload?.run_id) return block;
                            const priorEvents = Array.isArray(block.payload?.events) ? block.payload.events : [];
                            const nextEvents = Array.isArray(data.block.payload?.events) ? data.block.payload.events : [];
                            return { ...block, payload: { ...block.payload, ...data.block.payload, events: [...priorEvents, ...nextEvents].slice(-60) } };
                          });
                        })()
                      : data.block.type === "plan_result" || data.block.type === "execution_packet"
                        ? [
                            ...(message.render_blocks || []).filter(
                              (block) => block?.type !== data.block.type || block?.payload?.title !== data.block?.payload?.title,
                            ),
                            data.block,
                          ]
                        : [...(message.render_blocks || []), data.block],
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
    await submitMessage(requestMessage, {
      displayMessage: value || "Uploaded files",
      attachmentsOverride: pendingAttachments,
    });
  }

  function stopGeneration() {
    abortRef.current?.abort();
    abortRef.current = null;
    setIsLoading(false);
  }

  async function handleRemoveIndexedArtifact(artifactId) {
    try {
      await deleteArtifact(artifactId);
      await refreshIndexedFiles();
    } catch (err) {
      setError(err.message || String(err));
    }
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
          <MessageList
            messages={messages}
            isLoading={isLoading}
            copiedKey={copiedKey}
            onCopyMessage={handleCopyMessage}
            onResponsePreference={handleResponsePreference}
            onContinue={handleContinueMessage}
            onExecutePacket={handleExecutePacket}
          />
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
            models={models}
            onModelChange={setActiveModel}
            responseEffort={responseEffort}
            onResponseEffortChange={setResponseEffort}
            indexedFiles={artifacts}
            onViewIndexedFiles={() => setShowIndexedFiles(!showIndexedFiles)}
            onRefreshIndexedFiles={refreshIndexedFiles}
          />

          {/* Indexed Files Modal */}
          {showIndexedFiles && (
            <>
              <div className="indexed-files-overlay" onClick={() => setShowIndexedFiles(false)} />
              <div className="indexed-files-modal">
                <div className="indexed-files-header">
                  <h3>📁 Indexed Files ({artifacts.length})</h3>
                  <button className="icon-button" onClick={() => setShowIndexedFiles(false)} aria-label="Close indexed files">✕</button>
                </div>
                <div className="indexed-files-list">
                  {artifacts.map((artifact) => (
                    <div key={artifact.id} className="indexed-file-row">
                      <button
                        type="button"
                        className="indexed-file-main"
                        onClick={() => {
                          handleOpenArtifact(artifact);
                          setShowIndexedFiles(false);
                        }}
                      >
                        <div className="indexed-file-title">{artifact.title}</div>
                        <div className="indexed-file-meta">{artifact.kind}</div>
                        {artifact.preview ? (
                          <div className="indexed-file-date">{artifact.preview.substring(0, 120)}...</div>
                        ) : null}
                      </button>
                      <button
                        type="button"
                        className="icon-button danger"
                        aria-label={`Remove ${artifact.title}`}
                        onClick={async (event) => {
                          event.stopPropagation();
                          await handleRemoveIndexedArtifact(artifact.id);
                        }}
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </>
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
          onExecuteTool={handleExecuteTool}
          onUploadToolCode={handleUploadToolCode}
          onToggleTool={handleToggleTool}
          onDeleteTool={handleDeleteTool}
        />
      }
      documentationContent={<DocumentationView />}
      terminalContent={<TerminalPanel visible={true} />}
      superAgentContent={<><AGISystemV4Panel /><AGISystemV3Panel /><EliteAgentCommandCenter /><SuperAgentPanel /></>}
      uxContent={<UXIntelligenceWorkspace />}
      backendStatus={backendStatus}
      programmingAgiContent={<><MaximumDynamicAgentPanel /><DailyProgrammingAGIPanel /></>}
      platformContent={<><AutonomousIntelligenceV5Panel /><AgenticVisualPanel /><AutonomousDevPlatformV4Panel /><PlatformPanel /></>}
    />
  );
}
