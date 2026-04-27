/**
 * ResearchCard — displays web search results as a clean "research card"
 * separated from the main chat flow.
 *
 * Instead of dumping raw search snippets into the chat, results appear
 * in a collapsible card at the end of the message.
 */
import { useState } from "react";

function Favicon({ url }) {
  const domain = (() => {
    try { return new URL(url).hostname; } catch { return ""; }
  })();
  return domain ? (
    <img
      src={`https://www.google.com/s2/favicons?domain=${domain}&sz=16`}
      alt=""
      width={14} height={14}
      style={{ borderRadius:2, flexShrink:0 }}
      onError={e => { e.target.style.display = "none"; }}
    />
  ) : null;
}

function SourceItem({ source, index }) {
  return (
    <a
      href={source.url}
      target="_blank"
      rel="noopener noreferrer"
      style={{
        display:"flex", alignItems:"flex-start", gap:8,
        padding:"8px 10px", borderRadius:8,
        background:"#0d1117", border:"1px solid #21262d",
        textDecoration:"none", color:"inherit",
        transition:"border-color 0.15s",
      }}
      onMouseEnter={e => e.currentTarget.style.borderColor="#388bfd"}
      onMouseLeave={e => e.currentTarget.style.borderColor="#21262d"}
    >
      <span style={{
        minWidth:18, height:18, borderRadius:"50%",
        background:"#21262d", color:"#8b949e",
        display:"flex", alignItems:"center", justifyContent:"center",
        fontSize:10, fontWeight:700, flexShrink:0,
      }}>
        {index + 1}
      </span>
      <Favicon url={source.url} />
      <div style={{ minWidth:0, flex:1 }}>
        <div style={{
          color:"#58a6ff", fontSize:12, fontWeight:600,
          whiteSpace:"nowrap", overflow:"hidden", textOverflow:"ellipsis",
        }}>
          {source.title || source.url}
        </div>
        {source.snippet && (
          <div style={{
            color:"#8b949e", fontSize:11, marginTop:2, lineHeight:1.5,
            display:"-webkit-box", WebkitLineClamp:2,
            WebkitBoxOrient:"vertical", overflow:"hidden",
          }}>
            {source.snippet}
          </div>
        )}
        <div style={{
          color:"#484f58", fontSize:10, marginTop:2,
          whiteSpace:"nowrap", overflow:"hidden", textOverflow:"ellipsis",
        }}>
          {source.url}
        </div>
      </div>
      {source.confidence != null && (
        <span style={{
          flexShrink:0, fontSize:10,
          color: source.confidence > 0.7 ? "#3fb950" : source.confidence > 0.4 ? "#d29922" : "#f85149",
          fontWeight:600,
        }}>
          {Math.round(source.confidence * 100)}%
        </span>
      )}
    </a>
  );
}

export default function ResearchCard({ log }) {
  const [expanded, setExpanded] = useState(false);

  if (!log) return null;

  const { query, summary, sources = [], depth = "normal", timestamp } = log;
  const visibleSources = expanded ? sources : sources.slice(0, 3);
  const depthColor = depth === "deep" ? "#388bfd" : depth === "normal" ? "#3fb950" : "#8b949e";

  return (
    <div style={{
      background:"linear-gradient(135deg,#0d1117 0%,#161b22 100%)",
      border:"1px solid #21262d",
      borderLeft:`3px solid ${depthColor}`,
      borderRadius:"0 8px 8px 0",
      padding:"10px 14px",
      marginTop:8,
      fontFamily:"'Inter',system-ui,sans-serif",
    }}>
      {/* Header */}
      <div style={{ display:"flex", alignItems:"center", gap:6, marginBottom:6 }}>
        <span style={{ fontSize:13 }}>🔍</span>
        <span style={{ color:"#8b949e", fontSize:11, fontWeight:600 }}>
          WEB RESEARCH
        </span>
        <span style={{
          background: depthColor + "22", color: depthColor,
          borderRadius:20, padding:"1px 7px", fontSize:10, fontWeight:700,
        }}>
          {depth.toUpperCase()}
        </span>
        <span style={{ color:"#484f58", fontSize:10, marginLeft:"auto" }}>
          {timestamp && new Date(timestamp).toLocaleTimeString()}
        </span>
      </div>

      {/* Query */}
      <div style={{
        color:"#cdd9e5", fontSize:12, marginBottom:6,
        fontStyle:"italic",
      }}>
        "{query}"
      </div>

      {/* Summary */}
      {summary && (
        <div style={{
          background:"#21262d", borderRadius:6, padding:"8px 10px",
          color:"#e6edf3", fontSize:12, lineHeight:1.6, marginBottom:8,
        }}>
          {summary}
        </div>
      )}

      {/* Sources */}
      {sources.length > 0 && (
        <>
          <div style={{ color:"#484f58", fontSize:10, marginBottom:4, fontWeight:600 }}>
            SOURCES ({sources.length})
          </div>
          <div style={{ display:"flex", flexDirection:"column", gap:4 }}>
            {visibleSources.map((source, i) => (
              <SourceItem key={i} source={source} index={i} />
            ))}
          </div>
          {sources.length > 3 && (
            <button
              onClick={() => setExpanded(e => !e)}
              style={{
                marginTop:6, background:"none", border:"none",
                color:"#388bfd", fontSize:11, cursor:"pointer", padding:0,
              }}
            >
              {expanded ? "▲ Show less" : `▼ Show ${sources.length - 3} more sources`}
            </button>
          )}
        </>
      )}
    </div>
  );
}
