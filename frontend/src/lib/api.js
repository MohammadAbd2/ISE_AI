const browserDefaultApiRoot = typeof window !== "undefined" ? "" : "http://localhost:8000";
const configuredApiRoot = import.meta.env.VITE_API_ROOT;
const API_ROOT = configuredApiRoot === "same-origin" ? "" : (configuredApiRoot ?? browserDefaultApiRoot);

export const apiRoot = API_ROOT;

export const api = {
  chatStream: `${API_ROOT}/api/chat/stream`,
  models: `${API_ROOT}/api/models`,
  chats: `${API_ROOT}/api/chats`,
  profile: `${API_ROOT}/api/ai/profile`,
  classifyIntent: `${API_ROOT}/api/intent/classify`,
  upload: `${API_ROOT}/api/files/upload`,
  tools: `${API_ROOT}/api/evolution/tools`,
  capabilities: `${API_ROOT}/api/evolution/capabilities`,
  stats: `${API_ROOT}/api/stats`,
  artifacts: `${API_ROOT}/api/artifacts`,
  sessionAnalytics: `${API_ROOT}/api/session-analytics`,
  terminal: `${API_ROOT}/api/terminal`,
  terminalStream: `${API_ROOT}/api/terminal/run-stream`,
  terminalStreamingCapabilities: `${API_ROOT}/api/terminal/streaming-capabilities`,
  projectExport: `${API_ROOT}/api/project/export`,
  ragSearch: `${API_ROOT}/api/rag/search`,
  gitStatus: `${API_ROOT}/api/git/status`,
  codeReview: `${API_ROOT}/api/code/review`,
  fileOperation: `${API_ROOT}/api/files/operation`,
  learningStats: `${API_ROOT}/api/learning/stats`,
  improvementPlan: `${API_ROOT}/api/learning/improvement-plan`,
  turnDiagnostics: `${API_ROOT}/api/learning/turn-diagnostics`,
  memorySummary: `${API_ROOT}/api/learning/memory-summary`,
  selfReflection: `${API_ROOT}/api/learning/self-reflection`,
  executionPacket: `${API_ROOT}/api/learning/execution-packet`,
  executionPacketFreshness: `${API_ROOT}/api/learning/execution-packet/freshness`,
  executionPacketLaunch: `${API_ROOT}/api/learning/execution-packet/launch`,
  executionPacketExecute: `${API_ROOT}/api/learning/execution-packet/execute`,
  executionPacketHistory: `${API_ROOT}/api/learning/execution-packet/history`,
  responsePreference: `${API_ROOT}/api/learning/response-preference`,
  developerHandbook: `${API_ROOT}/api/docs/developer-handbook`,
  evals: `${API_ROOT}/api/evals/run`,
  evalHistory: `${API_ROOT}/api/evals/history`,
  evalDrift: `${API_ROOT}/api/evals/drift`,
  evalUnstable: `${API_ROOT}/api/evals/unstable`,
  evalPrioritizedInstability: `${API_ROOT}/api/evals/prioritized-instability`,
  evalHotspots: `${API_ROOT}/api/evals/hotspots`,
  projectMap: `${API_ROOT}/api/project/map`,
  planningDemo: `${API_ROOT}/api/planning/demo`,
  approvals: `${API_ROOT}/api/evolution/approvals/pending`,
  platformReliability: `${API_ROOT}/api/platform/reliability/react-smoke`,
  platformPreview: `${API_ROOT}/api/platform/preview`,
  platformTraces: `${API_ROOT}/api/platform/traces`,
  approve: `${API_ROOT}/api/evolution/approvals`,
  agiV3Roadmap: `${API_ROOT}/api/agi-system-v3/roadmap`,
  agiV3Reason: `${API_ROOT}/api/agi-system-v3/reason`,
  agiV3Evaluate: `${API_ROOT}/api/agi-system-v3/evaluate`,
  agiV3Debug: `${API_ROOT}/api/agi-system-v3/debug`,
  agiV3Compress: `${API_ROOT}/api/agi-system-v3/compress-context`,
  agiV3Graph: `${API_ROOT}/api/agi-system-v3/knowledge-graph`,
  agiV3Cycle: `${API_ROOT}/api/agi-system-v3/continuous-cycle`,
  agiV3Integrations: `${API_ROOT}/api/agi-system-v3/integrations`,
  agiV3Risk: `${API_ROOT}/api/agi-system-v3/risk`,
  agiV3Control: `${API_ROOT}/api/agi-system-v3/control-summary`,
  agiV4Roadmap: `${API_ROOT}/api/agi-system-v4/roadmap`,
  agiV4Run: `${API_ROOT}/api/agi-system-v4/run`,
  agiV4Truth: `${API_ROOT}/api/agi-system-v4/truth/ground`,
  agiV4Trace: `${API_ROOT}/api/agi-system-v4/trace`,
  agiV4Evaluate: `${API_ROOT}/api/agi-system-v4/evaluate`,
  agiV4Certify: `${API_ROOT}/api/agi-system-v4/certify`,
  dailyAgiRoadmap: `${API_ROOT}/api/daily-programming-agi/roadmap`,
  dailyAgiAnalyze: `${API_ROOT}/api/daily-programming-agi/analyze`,
  dailyAgiValidate: `${API_ROOT}/api/daily-programming-agi/validate`,
  dailyAgiSimulateRestaurant: `${API_ROOT}/api/daily-programming-agi/simulate-restaurant-project`,
  dynamicAgentRoadmap: `${API_ROOT}/api/dynamic-agent-runtime/roadmap`,
  dynamicAgentContract: `${API_ROOT}/api/dynamic-agent-runtime/contract`,
  dynamicAgentRun: `${API_ROOT}/api/dynamic-agent-runtime/run`,
  dynamicAgentValidate: `${API_ROOT}/api/dynamic-agent-runtime/validate`,
  programmingAgiRoadmap: `${API_ROOT}/api/programming-agi/roadmap`,
  programmingAgiPaths: `${API_ROOT}/api/programming-agi/paths`,
  programmingAgiRememberPath: `${API_ROOT}/api/programming-agi/remember-path`,
  programmingAgiPlan: `${API_ROOT}/api/programming-agi/plan`,
  programmingAgiRun: `${API_ROOT}/api/programming-agi/run`,
  programmingAgiMerge: `${API_ROOT}/api/programming-agi/merge`,
  programmingAgiClearMemory: `${API_ROOT}/api/programming-agi/clear-stale-memory`,
  agentPlanExecute: `${API_ROOT}/api/agents/plan-and-execute`,
  agentRouteTask: `${API_ROOT}/api/agents/route-task`,
  agentHealth: `${API_ROOT}/api/agents/health`,
  agentProgrammerRoadmap: `${API_ROOT}/api/agents/programmer-roadmap`,
  agentExecute: `${API_ROOT}/api/agents/execute`,
  platformV4Roadmap: `${API_ROOT}/api/platform-v4/roadmap`,
  platformV4Status: `${API_ROOT}/api/platform-v4/status`,
  platformV4Jobs: `${API_ROOT}/api/platform-v4/jobs`,
  platformV4TerminalRun: `${API_ROOT}/api/platform-v4/terminal/run`,
  platformV4Workspaces: `${API_ROOT}/api/platform-v4/workspaces`,
  platformV4GitStatus: `${API_ROOT}/api/platform-v4/git/status`,
  platformV4GitCommit: `${API_ROOT}/api/platform-v4/git/commit`,
  platformV4CodebaseIndex: `${API_ROOT}/api/platform-v4/codebase/index`,
  platformV4DebugExplain: `${API_ROOT}/api/platform-v4/debug/explain`,
  platformV4Devtools: `${API_ROOT}/api/platform-v4/devtools`,
  platformV4Security: `${API_ROOT}/api/platform-v4/security/report`,
  platformV4SelfEvolution: `${API_ROOT}/api/platform-v4/self-evolution/propose`,
  devxGenerateFile: `${API_ROOT}/api/devx/files/generate`,
  devxGenerateDiagram: `${API_ROOT}/api/devx/diagrams/generate`,
  devxWorkspaces: `${API_ROOT}/api/devx/workspaces`,
  devxGenerateImage: `${API_ROOT}/api/devx/images/generate`,
  devxAnalyzeImage: `${API_ROOT}/api/devx/images/analyze`,
  agenticVisualRoadmap: `${API_ROOT}/api/agentic-visual/roadmap`,
  agenticVisualComponents: `${API_ROOT}/api/agentic-visual/components`,
  agenticVisualPanel: `${API_ROOT}/api/agentic-visual/panel`,
  agenticVisualRenderContract: `${API_ROOT}/api/agentic-visual/render-contract`,
  agenticVisualDesignFromUrl: `${API_ROOT}/api/agentic-visual/design/from-url`,
  agenticVisualDebugRepairPlan: `${API_ROOT}/api/agentic-visual/debug/repair-plan`,
  agenticVisualCriticalRoadmap: `${API_ROOT}/api/agentic-visual/critical-roadmap`,
  agenticVisualDebugSelfHeal: `${API_ROOT}/api/agentic-visual/debug/self-heal`,
  agenticVisualStaticHtmlGenerate: `${API_ROOT}/api/agentic-visual/static-html/generate`,
  agenticVisualIdePatch: `/api/agentic-visual/ide/patch`,
  agenticVisualDynamicOutputPlan: `/api/agentic-visual/dynamic-output-plan`,
  figmaAgentRoadmap: `${API_ROOT}/api/figma-agent/roadmap`,
  figmaAgentInspect: `${API_ROOT}/api/figma-agent/inspect`,
  figmaAgentPrototype: `${API_ROOT}/api/figma-agent/prototype`,
  agentLatestFileLocation: `${API_ROOT}/api/agents/latest-file-location`,
  unifiedAgentRoadmap: `${API_ROOT}/api/unified-agent/roadmap`,
  unifiedAgentExecute: `${API_ROOT}/api/unified-agent/execute`,
  unifiedAgentPrototype: `${API_ROOT}/api/unified-agent/design/prototype`,
  autonomousV5Roadmap: `${API_ROOT}/api/autonomous-v5/roadmap`,
  autonomousV5Run: `${API_ROOT}/api/autonomous-v5/run`,
  autonomousV5Status: `${API_ROOT}/api/autonomous-v5/status`,
};

export async function fetchJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const text = await response.text();
    try {
      const parsed = JSON.parse(text);
      const detail = parsed?.detail?.error || parsed?.detail || parsed?.message;
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail || parsed));
    } catch (error) {
      if (error instanceof SyntaxError) throw new Error(text || "Request failed");
      throw error;
    }
  }
  const contentType = response.headers.get("content-type") || "";
  return contentType.includes("application/json") ? response.json() : response.text();
}

export function artifactDownloadUrl(artifactId) {
  const safeId = encodeURIComponent(artifactId);
  // Artifact downloads intentionally use same-origin URLs in the browser.
  // This works in both http:// and https:// dev sessions through the Vite proxy
  // and avoids certificate/CORS failures caused by crossing protocols.
  if (typeof window !== "undefined") {
    return `/api/artifacts/${safeId}/download`;
  }
  return `${api.artifacts}/${safeId}/download`;
}

export function artifactManifestUrl(artifactId) {
  const safeId = encodeURIComponent(artifactId);
  if (typeof window !== "undefined") {
    return `/api/artifacts/${safeId}/manifest`;
  }
  return `${api.artifacts}/${safeId}/manifest`;
}

export function evolutionToolUrl(toolName) {
  return `${api.tools}/${encodeURIComponent(toolName)}/execute`;
}

export async function executeEvolutionTool(toolName, payload = {}) {
  return fetchJson(evolutionToolUrl(toolName), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function registerTool(toolDef) {
  return fetchJson(api.tools, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(toolDef),
  });
}

export async function uploadToolCode(toolName, code, entrypoint = "run") {
  return fetchJson(`${api.tools}/${encodeURIComponent(toolName)}/code`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code, entrypoint }),
  });
}

export async function listPendingApprovals() {
  return fetchJson(api.approvals);
}

export async function approveRequest(requestId, options = {}) {
  return fetchJson(`${api.approve}/${encodeURIComponent(requestId)}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(options),
  });
}

export async function rejectRequest(requestId, options = {}) {
  return fetchJson(`${api.approve}/${encodeURIComponent(requestId)}/reject`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(options),
  });
}

export async function listApprovalsHistory(params = {}) {
  const qs = new URLSearchParams(params).toString();
  return fetchJson(`${api.approve}/history${qs ? `?${qs}` : ''}`);
}

export async function enableTool(toolName) {
  return fetchJson(`${api.tools}/${encodeURIComponent(toolName)}/enable`, { method: "POST" });
}

export async function disableTool(toolName) {
  return fetchJson(`${api.tools}/${encodeURIComponent(toolName)}/disable`, { method: "POST" });
}

export async function deleteTool(toolName) {
  return fetchJson(`${api.tools}/${encodeURIComponent(toolName)}`, { method: "DELETE" });
}

export async function saveResponsePreference(style, messageExcerpt = "") {
  return fetchJson(api.responsePreference, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ style, message_excerpt: messageExcerpt }),
  });
}

export async function readProjectFile(path) {
  return fetchJson(api.fileOperation, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ operation: "read", path }),
  });
}

export async function classifyIntentRemote(message, mode = "auto") {
  return fetchJson(api.classifyIntent, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, mode }),
  });
}

// Updated for task: fix the remaining intent and context regressions found by the internal routing suit

export async function deleteArtifact(artifactId) {
  return fetchJson(`${api.artifacts}/${encodeURIComponent(artifactId)}`, { method: "DELETE" });
}

export function fileIconForExtension(extension = "") {
  const ext = String(extension).toLowerCase();
  return ({".txt":"📄",".md":"📝",".js":"🟨",".jsx":"⚛️",".ts":"🔷",".tsx":"⚛️",".json":"{}",".html":"🌐",".css":"🎨",".py":"🐍",".pdf":"📕",".docx":"📘",".mmd":"📊"})[ext] || "📦";
}

export async function generateDownloadableFile({ session_id = "default", filename, extension = ".txt", title, content }) {
  return fetchJson(api.devxGenerateFile, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ session_id, filename, extension, title, content }) });
}

export async function generateDynamicDiagram({ session_id = "default", title, kind = "flowchart", data = {}, export_format = "mmd" }) {
  return fetchJson(api.devxGenerateDiagram, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ session_id, title, kind, data, export_format }) });
}

export async function rememberWorkspace(label, path) {
  return fetchJson(api.devxWorkspaces, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ label, path }) });
}
