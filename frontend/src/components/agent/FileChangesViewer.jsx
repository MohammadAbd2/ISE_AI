export default function FileChangesViewer({ files = [] }) {
  return <section className="file-changes-viewer-v2"><header><strong>Files changed</strong><span>{files.length}</span></header>{files.map((file) => <article key={file.path || file}><span>{file.status || "changed"}</span><b>{file.path || file}</b>{file.reason ? <small>{file.reason}</small> : null}</article>)}</section>;
}
