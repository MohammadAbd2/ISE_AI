import AgentStatusBar from "./AgentStatusBar";
import ExecutionTimeline from "./ExecutionTimeline";
import LiveLogsPanel from "./LiveLogsPanel";
import FileChangesViewer from "./FileChangesViewer";
export default function AgentRunCard({ run }) {
  return <article className="agent-run-card-v2"><AgentStatusBar run={run} /><div className="agent-run-grid-v2"><ExecutionTimeline steps={run?.steps || []} /><LiveLogsPanel events={run?.events || []} /></div><FileChangesViewer files={run?.files || []} />{run?.artifact ? <a className="download-cta-v2" href={run.artifact}>Download verified ZIP</a> : null}</article>;
}
