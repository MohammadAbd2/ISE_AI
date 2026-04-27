import { artifactDownloadUrl, fileIconForExtension } from "../lib/api";

export default function DownloadableFileCard({ file }) {
  if (!file) return null;
  const artifactId = file.artifact_id || file.artifactId || file.id;
  const ext = file.extension || (file.filename?.match(/\.[^.]+$/)?.[0] ?? "");
  const href = file.download_url || (artifactId ? artifactDownloadUrl(artifactId) : "#");
  return <article className="downloadable-file-card">
    <div className="file-icon" aria-hidden>{file.icon || fileIconForExtension(ext)}</div>
    <div className="file-card-main">
      <strong>{file.filename || file.title || "Generated file"}</strong>
      <small>{ext || "file"} · {Math.ceil((file.size_bytes || 0) / 1024)} KB</small>
    </div>
    {artifactId && <a className="file-download-button" href={href} download>Download</a>}
  </article>;
}
