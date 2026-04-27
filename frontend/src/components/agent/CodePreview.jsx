export default function CodePreview({ filename = "code", language = "text", code = "" }) {
  const lines = String(code).split("\n");
  return <section className="code-preview-v2"><header><strong>{filename}</strong><span>{language}</span></header><pre><code>{lines.map((line, index) => <span className="code-line" key={`${index}-${line.slice(0, 12)}`}><i>{index + 1}</i>{line || " "}</span>)}</code></pre></section>;
}
