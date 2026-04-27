import { useState, useMemo } from "react";

export default function DiffViewer({ oldContent = "", newContent = "", fileName = "" }) {
  const [viewMode, setViewMode] = useState("split"); // "split" or "unified"

  const diffLines = useMemo(() => {
    return computeDiff(oldContent, newContent);
  }, [oldContent, newContent]);

  function computeDiff(oldText, newText) {
    const oldLines = oldText.split("\n");
    const newLines = newText.split("\n");
    
    // Simple line-by-line diff
    const maxLines = Math.max(oldLines.length, newLines.length);
    const lines = [];
    
    for (let i = 0; i < maxLines; i++) {
      const oldLine = oldLines[i];
      const newLine = newLines[i];
      
      if (oldLine === newLine) {
        lines.push({ type: "unchanged", oldNum: i + 1, newNum: i + 1, content: oldLine || "" });
      } else {
        if (oldLine !== undefined) {
          lines.push({ type: "removed", oldNum: i + 1, newNum: null, content: oldLine });
        }
        if (newLine !== undefined) {
          lines.push({ type: "added", oldNum: null, newNum: i + 1, content: newLine });
        }
      }
    }
    
    return lines;
  }

  const stats = useMemo(() => {
    const added = diffLines.filter(l => l.type === "added").length;
    const removed = diffLines.filter(l => l.type === "removed").length;
    const unchanged = diffLines.filter(l => l.type === "unchanged").length;
    return { added, removed, unchanged, total: diffLines.length };
  }, [diffLines]);

  if (!oldContent && !newContent) {
    return (
      <div style={{ padding: "40px", textAlign: "center", color: "#666" }}>
        <div style={{ fontSize: "48px", marginBottom: "16px" }}>📊</div>
        <div style={{ fontSize: "18px", fontWeight: "bold", marginBottom: "8px" }}>No diff to display</div>
        <div>Select files to compare or make changes to see the diff</div>
      </div>
    );
  }

  return (
    <div className="diff-viewer" style={{
      display: "flex",
      flexDirection: "column",
      height: "100%",
      background: "#1e1e1e",
      color: "#d4d4d4",
      fontFamily: "'Fira Code', 'Cascadia Code', 'Consolas', monospace",
      fontSize: "13px",
    }}>
      {/* Diff Header */}
      <div style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: "8px 12px",
        background: "#2d2d2d",
        borderBottom: "1px solid #3e3e3e",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <span style={{ fontSize: "14px" }}>📊</span>
          <span style={{ fontWeight: "bold", fontSize: "12px" }}>
            DIFF: {fileName || "Changes"}
          </span>
          <div style={{ display: "flex", gap: "8px", fontSize: "11px" }}>
            <span style={{ color: "#4ec9b0" }}>+{stats.addadded}</span>
            <span style={{ color: "#f48771" }}>-{stats.removed}</span>
          </div>
        </div>
        <div style={{ display: "flex", gap: "8px" }}>
          <button
            onClick={() => setViewMode("split")}
            style={{
              background: viewMode === "split" ? "#0e639c" : "transparent",
              border: "1px solid #555",
              color: "white",
              padding: "2px 8px",
              borderRadius: "3px",
              cursor: "pointer",
              fontSize: "11px",
            }}
          >
            Split
          </button>
          <button
            onClick={() => setViewMode("unified")}
            style={{
              background: viewMode === "unified" ? "#0e639c" : "transparent",
              border: "1px solid #555",
              color: "white",
              padding: "2px 8px",
              borderRadius: "3px",
              cursor: "pointer",
              fontSize: "11px",
            }}
          >
            Unified
          </button>
        </div>
      </div>

      {/* Diff Stats */}
      <div style={{
        display: "flex",
        gap: "16px",
        padding: "6px 12px",
        background: "#252526",
        borderBottom: "1px solid #3e3e3e",
        fontSize: "11px",
      }}>
        <span style={{ color: "#4ec9b0" }}>✅ {stats.unchanged} unchanged</span>
        <span style={{ color: "#4ec9b0" }}>➕ {stats.added} added</span>
        <span style={{ color: "#f48771" }}>➖ {stats.removed} removed</span>
      </div>

      {/* Diff Content */}
      <div style={{
        flex: 1,
        overflow: "auto",
      }}>
        {viewMode === "split" ? (
          <div style={{ display: "flex" }}>
            {/* Old Content */}
            <div style={{ flex: 1, borderRight: "1px solid #3e3e3e" }}>
              <div style={{
                padding: "4px 8px",
                background: "#2d2d2d",
                borderBottom: "1px solid #3e3e3e",
                fontSize: "11px",
                color: "#aaa",
              }}>
                Original
              </div>
              <div>
                {diffLines.filter(l => l.type !== "added").map((line, idx) => (
                  <div
                    key={idx}
                    style={{
                      display: "flex",
                      background: line.type === "removed" ? "#4a2020" : "transparent",
                    }}
                  >
                    <div style={{
                      width: "40px",
                      textAlign: "right",
                      padding: "0 8px",
                      color: "#888",
                      background: "#252526",
                      borderRight: "1px solid #3e3e3e",
                      userSelect: "none",
                    }}>
                      {line.oldNum || ""}
                    </div>
                    <div style={{
                      flex: 1,
                      padding: "0 8px",
                      whiteSpace: "pre",
                      color: line.type === "removed" ? "#f48771" : "#d4d4d4",
                    }}>
                      {line.type === "removed" ? "- " : "  "}{line.content}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* New Content */}
            <div style={{ flex: 1 }}>
              <div style={{
                padding: "4px 8px",
                background: "#2d2d2d",
                borderBottom: "1px solid #3e3e3e",
                fontSize: "11px",
                color: "#aaa",
              }}>
                Modified
              </div>
              <div>
                {diffLines.filter(l => l.type !== "removed").map((line, idx) => (
                  <div
                    key={idx}
                    style={{
                      display: "flex",
                      background: line.type === "added" ? "#1f3a1f" : "transparent",
                    }}
                  >
                    <div style={{
                      width: "40px",
                      textAlign: "right",
                      padding: "0 8px",
                      color: "#888",
                      background: "#252526",
                      borderRight: "1px solid #3e3e3e",
                      userSelect: "none",
                    }}>
                      {line.newNum || ""}
                    </div>
                    <div style={{
                      flex: 1,
                      padding: "0 8px",
                      whiteSpace: "pre",
                      color: line.type === "added" ? "#4ec9b0" : "#d4d4d4",
                    }}>
                      {line.type === "added" ? "+ " : "  "}{line.content}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          /* Unified View */
          <div>
            {diffLines.map((line, idx) => (
              <div
                key={idx}
                style={{
                  display: "flex",
                  background:
                    line.type === "added" ? "#1f3a1f" :
                    line.type === "removed" ? "#4a2020" :
                    "transparent",
                }}
              >
                <div style={{
                  width: "40px",
                  textAlign: "right",
                  padding: "0 8px",
                  color: "#888",
                  background: "#252526",
                  borderRight: "1px solid #3e3e3e",
                  userSelect: "none",
                }}>
                  {line.oldNum || ""}
                </div>
                <div style={{
                  width: "40px",
                  textAlign: "right",
                  padding: "0 8px",
                  color: "#888",
                  background: "#252526",
                  borderRight: "1px solid #3e3e3e",
                  userSelect: "none",
                }}>
                  {line.newNum || ""}
                </div>
                <div style={{
                  flex: 1,
                  padding: "0 8px",
                  whiteSpace: "pre",
                  color:
                    line.type === "added" ? "#4ec9b0" :
                    line.type === "removed" ? "#f48771" :
                    "#d4d4d4",
                }}>
                  {line.type === "added" ? "+ " : line.type === "removed" ? "- " : "  "}{line.content}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
