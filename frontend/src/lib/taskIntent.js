export function classifyTaskIntent(text, mode = "auto") {
  const lower = text.toLowerCase().trim();

  const visualTerms = [
    "chart", "diagram", "graph", "plot", "visualize", "visualise", "2d", "3d",
    "map", "globe", "scatter", "salary data", "profit data", "revenue data",
    "excel", "spreadsheet",
  ];
  const visualCodeTerms = [
    "component", "file", "code", "react", "jsx", "tsx", "python", "api", "endpoint",
    "build the chart", "create chart component", "write chart code",
  ];
  const researchTerms = [
    "latest", "recent", "today", "news", "research", "look up", "find on the web",
    "search the web", "sources", "citation", "compare",
  ];
  const projectTerms = [
    "project", "repo", "repository", "zip", "archive", "codebase", "folder",
    "analyze files", "analyse files", "read the project", "inspect files",
  ];
  const codingTerms = [
    "create file", "write file", "save to", "edit file", "update file", "delete file",
    "modify", "fix", "debug", "refactor", "implement", "add endpoint", "add route",
    "install", "run tests", "write tests", "create component", "update component",
  ];

  if (mode === "agent") {
    return { kind: "coding", useAgent: true };
  }
  if (mode === "chat") {
    return { kind: "chat", useAgent: false };
  }
  if (visualTerms.some((term) => lower.includes(term)) && !visualCodeTerms.some((term) => lower.includes(term))) {
    return { kind: "visualization", useAgent: false };
  }
  if (researchTerms.some((term) => lower.includes(term))) {
    return { kind: "research", useAgent: false };
  }
  if (projectTerms.some((term) => lower.includes(term))) {
    return { kind: "project_analysis", useAgent: false };
  }
  if (codingTerms.some((term) => lower.includes(term)) || /(?:frontend|backend|src|app|components|utils|api)\/[\w/.-]+/.test(lower)) {
    return { kind: "coding", useAgent: true };
  }
  return { kind: "chat", useAgent: false };
}
