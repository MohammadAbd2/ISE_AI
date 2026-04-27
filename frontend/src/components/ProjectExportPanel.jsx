import { artifactDownloadUrl, fetchJson, api } from "../lib/api";
import { useState } from "react";

export default function ProjectExportPanel({ currentSessionId, onExported }) {
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const disabled = !currentSessionId || loading;

  async function handleExport() {
    if (!currentSessionId || loading) return;
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const result = await fetchJson(`${api.projectExport}?session_id=${encodeURIComponent(currentSessionId)}`, {
        method: "POST",
      });
      const artifact = result.artifact;
      setMessage(artifact ? `Created ${artifact.title} with ${result.file_count} files.` : "Export created.");
      onExported?.(artifact);
    } catch (err) {
      setError(err.message || "Project export failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Project Export</p>
          <h2>Download generated projects</h2>
        </div>
        <span className="panel-chip">ZIP</span>
      </div>
      <p>
        Package the current project workspace as a downloadable zip artifact so landing pages and other generated apps can be exported in one click.
      </p>
      <div className="artifact-actions">
        <button type="button" className="ghost-button" disabled={disabled} onClick={handleExport}>
          {loading ? "Packaging..." : "Create ZIP export"}
        </button>
      </div>
      {message ? <div className="panel-note">{message}</div> : null}
      {error ? <div className="panel-error">{error}</div> : null}
    </section>
  );
}
