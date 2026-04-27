import { useState } from "react";
import { rememberWorkspace } from "../lib/api";

export default function WorkspacePathPicker({ onSaved }) {
  const [label, setLabel] = useState("default");
  const [path, setPath] = useState("");
  const [status, setStatus] = useState("");
  async function save() {
    setStatus("Saving workspace…");
    try { const row = await rememberWorkspace(label, path); setStatus(`Workspace saved: ${row.path}`); onSaved?.(row); }
    catch (error) { setStatus(error.message || "Workspace save failed"); }
  }
  return <div className="workspace-path-picker">
    <input value={label} onChange={(e)=>setLabel(e.target.value)} placeholder="workspace label" />
    <input value={path} onChange={(e)=>setPath(e.target.value)} placeholder="/path/to/project" />
    <button type="button" onClick={save}>Use folder</button>
    {status && <small>{status}</small>}
  </div>;
}
