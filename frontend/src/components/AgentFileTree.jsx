import { useMemo, useState } from "react";
import { buildFileTree, downloadTextFile, getFileMeta } from "../lib/fileVisuals";
import "../styles/agent-file-tree.css";

function normalizeFilePath(file) {
  if (typeof file === "string") return file;
  if (file && typeof file === "object") {
    return String(file.path || file.file || file.filename || file.name || file.title || file.id || "");
  }
  return String(file || "");
}

function normalizeFileContents(contents = {}) {
  if (!contents || typeof contents !== "object" || Array.isArray(contents)) return {};
  return Object.fromEntries(
    Object.entries(contents).map(([key, value]) => [
      normalizeFilePath(key),
      typeof value === "string" ? value : JSON.stringify(value ?? "", null, 2),
    ]),
  );
}

function TreeNode({ node, depth, fileContents = {}, onPreview }) {
  const [open, setOpen] = useState(depth < 2);
  const isFolder = node.type === "folder";
  const meta = getFileMeta(node.path);
  const content = fileContents[node.path] || "";

  if (isFolder) {
    return (
      <div className="agent-tree-node">
        <button type="button" className="agent-tree-row folder" style={{ paddingLeft: `${depth * 14 + 8}px` }} onClick={() => setOpen(!open)}>
          <span className={`agent-tree-arrow ${open ? "open" : ""}`}>▸</span>
          <span className="agent-tree-folder-icon">📁</span>
          <strong>{node.name}</strong>
          <em>{node.children.length}</em>
        </button>
        {open ? node.children.map((child) => <TreeNode key={child.path} node={child} depth={depth + 1} fileContents={fileContents} onPreview={onPreview} />) : null}
      </div>
    );
  }

  return (
    <div className="agent-tree-row file" style={{ paddingLeft: `${depth * 14 + 8}px` }}>
      <span className={`agent-file-icon ${meta.className}`}>{meta.icon}</span>
      <span className="agent-tree-file-name">{node.name}</span>
      <span className={`agent-file-pill ${meta.className}`}>{meta.label}</span>
      <div className="agent-tree-actions">
        <button type="button" onClick={() => onPreview?.(node.path)}>Preview</button>
        <button type="button" onClick={() => downloadTextFile(node.name, content)}>Download</button>
      </div>
    </div>
  );
}

export default function AgentFileTree({ files = [], fileContents = {}, title = "Generated files", onPreview }) {
  const normalizedContents = useMemo(() => normalizeFileContents(fileContents), [fileContents]);
  const paths = useMemo(() => {
    const fromFiles = Array.isArray(files) ? files.map(normalizeFilePath) : [];
    const fromContents = Object.keys(normalizedContents || {}).map(normalizeFilePath);
    return Array.from(new Set([...fromFiles, ...fromContents].filter(Boolean)));
  }, [files, normalizedContents]);
  const tree = useMemo(() => buildFileTree(paths), [paths]);
  const [filter, setFilter] = useState("");
  const safeFilter = String(filter || "").toLowerCase();
  const filteredPaths = paths.filter((path) => String(path || "").toLowerCase().includes(safeFilter));
  const filteredTree = useMemo(() => buildFileTree(filteredPaths), [filteredPaths]);

  return (
    <section className="agent-file-tree-card">
      <div className="agent-file-tree-head">
        <div>
          <p className="maximum-agent-kicker">Workspace Tree</p>
          <h4>{title}</h4>
        </div>
        <span>{paths.length} files</span>
      </div>
      <input className="agent-file-filter" value={filter} onChange={(event) => setFilter(event.target.value)} placeholder="Filter files by path or extension..." />
      <div className="agent-file-tree-list">
        {(filter ? filteredTree : tree).children.map((node) => <TreeNode key={node.path || node.name} node={node} depth={0} fileContents={normalizedContents} onPreview={onPreview} />)}
      </div>
    </section>
  );
}
