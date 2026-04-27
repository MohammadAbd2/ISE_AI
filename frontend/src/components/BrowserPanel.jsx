/**
 * BrowserPanel — shows the AI's sandboxed browser activity.
 * Displays page content, screenshots, mouse movements, and action logs.
 * Inspired by ChatGPT Codex / Manus AI browser view.
 */
import { useEffect, useRef, useState } from "react";

const ACTION_ICONS = {
  navigate:    "🌐",
  click:       "🖱️",
  type:        "⌨️",
  scroll:      "↕️",
  screenshot:  "📸",
  extract:     "📋",
  wait:        "⏳",
  close:       "✖",
};

function ActionLog({ action }) {
  return (
    <div style={{
      display:"flex", alignItems:"flex-start", gap:6,
      padding:"4px 8px", borderRadius:6,
      background:"#0d1117", marginBottom:3, fontSize:11,
    }}>
      <span style={{ flexShrink:0 }}>
        {ACTION_ICONS[action.type] ?? "⚙️"}
      </span>
      <div style={{ minWidth:0, flex:1 }}>
        <span style={{ color:"#cdd9e5" }}>{action.description}</span>
        {action.url && (
          <div style={{
            color:"#484f58", whiteSpace:"nowrap",
            overflow:"hidden", textOverflow:"ellipsis", fontSize:10,
          }}>
            {action.url}
          </div>
        )}
      </div>
      <span style={{ color:"#484f58", flexShrink:0, fontSize:10 }}>
        {action.elapsed_ms != null ? `${action.elapsed_ms}ms` : ""}
      </span>
    </div>
  );
}

function MouseCursor({ x, y }) {
  if (x == null || y == null) return null;
  return (
    <div style={{
      position:"absolute", pointerEvents:"none",
      left: x - 6, top: y - 6,
      width:12, height:12, borderRadius:"50%",
      background:"rgba(56,139,253,0.6)",
      border:"2px solid #388bfd",
      boxShadow:"0 0 8px #388bfd88",
      transition:"left 0.15s ease, top 0.15s ease",
      zIndex:10,
    }} />
  );
}

export default function BrowserPanel({ session }) {
  const [tab, setTab] = useState("preview"); // preview | actions | source
  const logsRef = useRef(null);

  useEffect(() => {
    if (logsRef.current && tab === "actions") {
      logsRef.current.scrollTop = logsRef.current.scrollHeight;
    }
  }, [session?.actions, tab]);

  if (!session) {
    return (
      <div style={{
        background:"#0d1117", border:"1px solid #21262d",
        borderRadius:10, padding:24, textAlign:"center",
        color:"#484f58", fontFamily:"'Inter',system-ui,sans-serif",
      }}>
        <div style={{ fontSize:32, marginBottom:8 }}>🌐</div>
        <div style={{ fontSize:13, fontWeight:600, marginBottom:4 }}>Browser Panel</div>
        <div style={{ fontSize:12 }}>
          When ISE AI browses the web or controls a GUI,<br />
          the activity will appear here.
        </div>
      </div>
    );
  }

  const { url, title, screenshot, actions = [], mouseX, mouseY, status } = session;

  return (
    <div style={{
      background:"#0d1117", border:"1px solid #21262d",
      borderRadius:10, overflow:"hidden",
      fontFamily:"'Inter',system-ui,sans-serif",
      display:"flex", flexDirection:"column", height:"100%",
    }}>
      {/* Address bar */}
      <div style={{
        display:"flex", alignItems:"center", gap:8,
        padding:"8px 12px", background:"#161b22",
        borderBottom:"1px solid #21262d",
      }}>
        <div style={{
          display:"flex", gap:4, flexShrink:0,
        }}>
          {["#f85149","#d29922","#3fb950"].map(c => (
            <div key={c} style={{ width:10, height:10, borderRadius:"50%", background:c }} />
          ))}
        </div>
        <div style={{
          flex:1, background:"#21262d", borderRadius:6,
          padding:"4px 10px", color:"#8b949e", fontSize:11,
          overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap",
        }}>
          {url || "about:blank"}
        </div>
        <span style={{
          fontSize:10, fontWeight:700, borderRadius:20,
          padding:"2px 8px",
          background: status === "loading" ? "#d2992222" : status === "done" ? "#3fb95022" : "#21262d",
          color: status === "loading" ? "#d29922" : status === "done" ? "#3fb950" : "#8b949e",
        }}>
          {status ?? "idle"}
        </span>
      </div>

      {/* Tab bar */}
      <div style={{
        display:"flex", gap:0, background:"#161b22",
        borderBottom:"1px solid #21262d",
      }}>
        {["preview","actions","source"].map(t => (
          <button key={t} onClick={() => setTab(t)} style={{
            padding:"6px 14px", border:"none", cursor:"pointer",
            background: tab === t ? "#0d1117" : "transparent",
            color: tab === t ? "#e6edf3" : "#8b949e",
            borderBottom: tab === t ? "2px solid #388bfd" : "2px solid transparent",
            fontSize:11, fontWeight:600, textTransform:"uppercase",
          }}>
            {t === "preview" ? "🖼 Preview" : t === "actions" ? "📋 Actions" : "📄 Source"}
          </button>
        ))}
        <span style={{
          marginLeft:"auto", padding:"0 12px",
          color:"#484f58", fontSize:10, display:"flex", alignItems:"center",
        }}>
          {actions.length} actions
        </span>
      </div>

      {/* Content */}
      <div style={{ flex:1, overflow:"hidden", position:"relative", minHeight:200 }}>
        {tab === "preview" && (
          <div style={{ position:"relative", width:"100%", height:"100%" }}>
            {screenshot ? (
              <>
                <img
                  src={`data:image/png;base64,${screenshot}`}
                  alt="Browser screenshot"
                  style={{ width:"100%", height:"100%", objectFit:"contain", display:"block" }}
                />
                <MouseCursor x={mouseX} y={mouseY} />
              </>
            ) : (
              <div style={{
                display:"flex", alignItems:"center", justifyContent:"center",
                height:200, color:"#484f58", flexDirection:"column", gap:8,
              }}>
                <span style={{ fontSize:28 }}>📸</span>
                <span style={{ fontSize:12 }}>Screenshot will appear here</span>
              </div>
            )}
          </div>
        )}

        {tab === "actions" && (
          <div
            ref={logsRef}
            style={{ padding:8, overflow:"auto", maxHeight:350 }}
          >
            {actions.length === 0 ? (
              <div style={{ color:"#484f58", fontSize:12, textAlign:"center", padding:16 }}>
                No actions recorded yet
              </div>
            ) : (
              actions.map((a, i) => <ActionLog key={i} action={a} />)
            )}
          </div>
        )}

        {tab === "source" && (
          <pre style={{
            margin:0, padding:10, overflow:"auto", maxHeight:350,
            color:"#8b949e", fontSize:10, lineHeight:1.5,
            background:"#0d1117",
          }}>
            {session.pageSource || "Page source not available"}
          </pre>
        )}
      </div>

      {/* Page title */}
      {title && (
        <div style={{
          padding:"4px 12px", background:"#161b22",
          borderTop:"1px solid #21262d",
          color:"#8b949e", fontSize:10,
          overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap",
        }}>
          📄 {title}
        </div>
      )}
    </div>
  );
}
