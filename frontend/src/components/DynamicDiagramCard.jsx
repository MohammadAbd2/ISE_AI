import DownloadableFileCard from "./DownloadableFileCard";

export default function DynamicDiagramCard({ diagram }) {
  if (!diagram) return null;
  return <section className="diagram-card">
    <header><strong>{diagram.title || "Dynamic diagram"}</strong><span>{diagram.kind || "flowchart"}</span></header>
    <pre className="mermaid-source">{diagram.mermaid}</pre>
    <DownloadableFileCard file={diagram.artifact} />
  </section>;
}
