const API_ROOT = import.meta.env.VITE_API_ROOT || "http://localhost:8000";

export const apiRoot = API_ROOT;

export const api = {
  chatStream: `${API_ROOT}/api/chat/stream`,
  models: `${API_ROOT}/api/models`,
  chats: `${API_ROOT}/api/chats`,
  profile: `${API_ROOT}/api/ai/profile`,
  upload: `${API_ROOT}/api/files/upload`,
  tools: `${API_ROOT}/api/evolution/tools`,
  capabilities: `${API_ROOT}/api/evolution/capabilities`,
  stats: `${API_ROOT}/api/stats`,
  artifacts: `${API_ROOT}/api/artifacts`,
  sessionAnalytics: `${API_ROOT}/api/session-analytics`,
  terminal: `${API_ROOT}/api/terminal/run`,
  ragSearch: `${API_ROOT}/api/rag/search`,
  gitStatus: `${API_ROOT}/api/git/status`,
  codeReview: `${API_ROOT}/api/code/review`,
  fileOperation: `${API_ROOT}/api/files/operation`,
  learningStats: `${API_ROOT}/api/learning/stats`,
  planningDemo: `${API_ROOT}/api/planning/demo`,
};

export async function fetchJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "Request failed");
  }
  return response.json();
}

export function artifactDownloadUrl(artifactId) {
  return `${api.artifacts}/${artifactId}/download`;
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
