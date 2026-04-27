export const FILE_TYPE_META = {
  jsx: { label: "JSX", icon: "⚛️", className: "jsx" },
  js: { label: "JS", icon: "🟨", className: "js" },
  ts: { label: "TS", icon: "🔷", className: "ts" },
  tsx: { label: "TSX", icon: "⚛️", className: "tsx" },
  css: { label: "CSS", icon: "🎨", className: "css" },
  scss: { label: "SCSS", icon: "💅", className: "scss" },
  html: { label: "HTML", icon: "🌐", className: "html" },
  json: { label: "JSON", icon: "{}", className: "json" },
  md: { label: "MD", icon: "📝", className: "md" },
  py: { label: "PY", icon: "🐍", className: "py" },
  cs: { label: "C#", icon: "#️⃣", className: "cs" },
  sql: { label: "SQL", icon: "🗄️", className: "sql" },
  yml: { label: "YML", icon: "⚙️", className: "yml" },
  yaml: { label: "YAML", icon: "⚙️", className: "yaml" },
  zip: { label: "ZIP", icon: "📦", className: "zip" },
  csproj: { label: "CSPROJ", icon: "#️⃣", className: "cs" },
  env: { label: "ENV", icon: "🔐", className: "env" },
  dockerfile: { label: "Docker", icon: "🐳", className: "docker" },
};

export function getFileExtension(path = "") {
  const clean = String(path).split("?")[0].split("#")[0];
  const last = clean.split("/").pop() || "";
  const index = last.lastIndexOf(".");
  if (last.toLowerCase() === "dockerfile") return "dockerfile";
  if (last.startsWith(".")) return last.slice(1).toLowerCase();
  return index > -1 ? last.slice(index + 1).toLowerCase() : "file";
}

export function getFileMeta(path = "") {
  const ext = getFileExtension(path);
  return FILE_TYPE_META[ext] || { label: ext.toUpperCase(), icon: "📄", className: "file" };
}

export function normalizePathInput(rawPath) {
  if (typeof rawPath === "string") return rawPath;
  if (rawPath && typeof rawPath === "object") {
    return String(rawPath.path || rawPath.file || rawPath.filename || rawPath.name || rawPath.title || rawPath.id || "");
  }
  return String(rawPath || "");
}

export function buildFileTree(paths = []) {
  const root = { name: "workspace", path: "", type: "folder", children: new Map() };
  const list = Array.isArray(paths) ? paths : [];
  for (const rawPath of list.map(normalizePathInput).filter(Boolean)) {
    const normalized = String(rawPath).replace(/^\/+/, "");
    const parts = normalized.split("/").filter(Boolean);
    let cursor = root;
    parts.forEach((part, index) => {
      const path = parts.slice(0, index + 1).join("/");
      const isFile = index === parts.length - 1;
      if (!cursor.children.has(part)) {
        cursor.children.set(part, { name: part, path, type: isFile ? "file" : "folder", children: new Map() });
      }
      cursor = cursor.children.get(part);
    });
  }
  const toArray = (node) => ({ ...node, children: Array.from(node.children.values()).sort((a, b) => (a.type === b.type ? a.name.localeCompare(b.name) : a.type === "folder" ? -1 : 1)).map(toArray) });
  return toArray(root);
}

export function downloadTextFile(filename, content = "") {
  if (typeof window === "undefined") return;
  const meta = getFileMeta(filename);
  const mime = meta.className === "json" ? "application/json" : meta.className === "html" ? "text/html" : "text/plain";
  const blob = new Blob([content], { type: `${mime};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename.split("/").pop() || "download.txt";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
