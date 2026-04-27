/**
 * PlanPanel — shows the AI's upfront execution plan before it starts.
 * User can approve, reorder or skip steps.
 * Inspired by GPT-5's "upfront thinking" feature.
 */
import { useState } from "react";

const STEP_ICONS = {
  research:    "🔍",
  code:        "💻",
  test:        "🧪",
  review:      "📋",
  document:    "📝",
  deploy:      "🚀",
  file:        "📁",
  terminal:    "⌨️",
  search:      "🌐",
  plan:        "🗺️",
  default:     "⚙️",
};

function stepIcon(type) {
  return STEP_ICONS[type?.toLowerCase()] ?? STEP_ICONS.default;
}

export default function PlanPanel({ plan, onApprove, onSkipStep, onCancel }) {
  const [steps, setSteps] = useState(plan?.steps ?? []);
  const [dragging, setDragging] = useState(null);

  if (!plan) return null;

  function toggleStep(idx) {
    setSteps(prev =>
      prev.map((s, i) => i === idx ? { ...s, skipped: !s.skipped } : s)
    );
  }

  function handleDragStart(idx) { setDragging(idx); }
  function handleDragOver(e, idx) {
    e.preventDefault();
    if (dragging === null || dragging === idx) return;
    setSteps(prev => {
      const next = [...prev];
      const [item] = next.splice(dragging, 1);
      next.splice(idx, 0, item);
      setDragging(idx);
      return next;
    });
  }
  function handleDrop() { setDragging(null); }

  const activeSteps = steps.filter(s => !s.skipped);

  return (
    <div style={{
      background: "linear-gradient(135deg,#0d1117 0%,#161b22 100%)",
      border: "1px solid #30363d",
      borderRadius: 12,
      padding: "16px 18px",
      marginBottom: 12,
      fontFamily: "'Inter', system-ui, sans-serif",
    }}>
      {/* Header */}
      <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:12 }}>
        <span style={{ fontSize:18 }}>🗺️</span>
        <span style={{ color:"#e6edf3", fontWeight:700, fontSize:15 }}>
          Execution Plan
        </span>
        <span style={{
          marginLeft:"auto", background:"#21262d", borderRadius:20,
          padding:"2px 10px", color:"#8b949e", fontSize:12,
        }}>
          {activeSteps.length} of {steps.length} steps active
        </span>
      </div>

      {/* Goal */}
      {plan.goal && (
        <div style={{
          background:"#0d1117", borderRadius:8, padding:"8px 12px",
          marginBottom:12, color:"#cdd9e5", fontSize:13, lineHeight:1.5,
        }}>
          <span style={{ color:"#58a6ff", fontWeight:600 }}>Goal: </span>
          {plan.goal}
        </div>
      )}

      {/* Step list */}
      <div style={{ display:"flex", flexDirection:"column", gap:6 }}>
        {steps.map((step, idx) => (
          <div
            key={idx}
            draggable
            onDragStart={() => handleDragStart(idx)}
            onDragOver={e => handleDragOver(e, idx)}
            onDrop={handleDrop}
            onClick={() => toggleStep(idx)}
            style={{
              display:"flex", alignItems:"flex-start", gap:10,
              background: step.skipped ? "#161b22" : "#21262d",
              border: `1px solid ${step.skipped ? "#21262d" : "#30363d"}`,
              borderRadius:8, padding:"8px 12px", cursor:"pointer",
              opacity: step.skipped ? 0.45 : 1,
              transition:"all 0.15s ease",
              userSelect:"none",
            }}
          >
            {/* Drag handle */}
            <span style={{ color:"#484f58", fontSize:13, marginTop:1 }}>⠿</span>

            {/* Step number */}
            <span style={{
              minWidth:20, height:20, borderRadius:"50%",
              background: step.skipped ? "#21262d" : "#388bfd22",
              border:`1px solid ${step.skipped ? "#30363d" : "#388bfd"}`,
              color: step.skipped ? "#484f58" : "#58a6ff",
              display:"flex", alignItems:"center", justifyContent:"center",
              fontSize:11, fontWeight:700,
            }}>
              {idx + 1}
            </span>

            {/* Icon + content */}
            <div style={{ flex:1, minWidth:0 }}>
              <div style={{ display:"flex", alignItems:"center", gap:6 }}>
                <span style={{ fontSize:14 }}>{stepIcon(step.type)}</span>
                <span style={{
                  color: step.skipped ? "#484f58" : "#e6edf3",
                  fontWeight:600, fontSize:13,
                  textDecoration: step.skipped ? "line-through" : "none",
                }}>
                  {step.agent ? `[${step.agent}] ` : ""}{step.title}
                </span>
              </div>
              {step.description && !step.skipped && (
                <p style={{ margin:"3px 0 0 0", color:"#8b949e", fontSize:12, lineHeight:1.5 }}>
                  {step.description}
                </p>
              )}
            </div>

            {/* Skip badge */}
            <span style={{
              fontSize:10, color: step.skipped ? "#484f58" : "#6e7681",
              marginTop:2,
            }}>
              {step.skipped ? "SKIPPED" : "click to skip"}
            </span>
          </div>
        ))}
      </div>

      {/* Action buttons */}
      <div style={{ display:"flex", gap:8, marginTop:14 }}>
        <button
          onClick={() => onApprove?.(steps)}
          disabled={activeSteps.length === 0}
          style={{
            flex:1, padding:"9px 16px", borderRadius:8, border:"none",
            background: activeSteps.length ? "#238636" : "#21262d",
            color: activeSteps.length ? "#fff" : "#484f58",
            fontWeight:700, fontSize:13, cursor: activeSteps.length ? "pointer" : "not-allowed",
            transition:"background 0.15s",
          }}
        >
          ▶ Execute Plan
        </button>
        <button
          onClick={onCancel}
          style={{
            padding:"9px 16px", borderRadius:8,
            border:"1px solid #30363d", background:"transparent",
            color:"#8b949e", fontWeight:600, fontSize:13, cursor:"pointer",
          }}
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
