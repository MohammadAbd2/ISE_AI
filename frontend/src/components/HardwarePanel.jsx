/**
 * HardwarePanel — displays current hardware profile and model tier.
 * Shows available RAM, GPU, and what model ISE AI is using.
 */
import { useEffect, useState } from "react";
import { apiRoot } from "../lib/api";

const TIER_COLORS = {
  tiny:   "#d29922",
  small:  "#58a6ff",
  medium: "#3fb950",
  large:  "#a371f7",
  xlarge: "#f0883e",
};

const TIER_LABELS = {
  tiny:   "Tiny (≤6 GB)",
  small:  "Small (6–12 GB)",
  medium: "Medium (12–22 GB)",
  large:  "Large (22–44 GB)",
  xlarge: "XLarge (44+ GB)",
};

function Bar({ value, max, color }) {
  const pct = Math.min(100, Math.round((value / max) * 100));
  return (
    <div style={{
      height:6, borderRadius:3, background:"#21262d",
      overflow:"hidden", margin:"3px 0",
    }}>
      <div style={{
        height:"100%", width:`${pct}%`,
        background: color,
        borderRadius:3, transition:"width 0.5s ease",
      }} />
    </div>
  );
}

function Row({ label, value, sub }) {
  return (
    <div style={{ marginBottom:6 }}>
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"baseline" }}>
        <span style={{ color:"#8b949e", fontSize:11 }}>{label}</span>
        <span style={{ color:"#e6edf3", fontSize:12, fontWeight:600 }}>{value}</span>
      </div>
      {sub}
    </div>
  );
}

export default function HardwarePanel({ apiBase = apiRoot || "" }) {
  const [hw, setHw] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${apiBase}/api/hardware/profile`)
      .then(r => r.json())
      .then(setHw)
      .catch(() => setError("Could not load hardware info"))
      .finally(() => setLoading(false));
  }, [apiBase]);

  const tierColor = hw ? (TIER_COLORS[hw.tier] ?? "#8b949e") : "#8b949e";

  return (
    <div style={{
      background:"#161b22", border:"1px solid #30363d",
      borderRadius:10, padding:"14px 16px",
      fontFamily:"'Inter',system-ui,sans-serif",
    }}>
      {/* Header */}
      <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:12 }}>
        <span style={{ fontSize:18 }}>🖥️</span>
        <span style={{ color:"#e6edf3", fontWeight:700, fontSize:14 }}>Hardware Profile</span>
        {hw && (
          <span style={{
            marginLeft:"auto",
            background: tierColor + "22", color: tierColor,
            borderRadius:20, padding:"2px 10px", fontSize:11, fontWeight:700,
          }}>
            {TIER_LABELS[hw.tier] ?? hw.tier}
          </span>
        )}
      </div>

      {loading && (
        <div style={{ color:"#8b949e", fontSize:12, textAlign:"center", padding:8 }}>
          Detecting hardware…
        </div>
      )}

      {error && (
        <div style={{ color:"#f85149", fontSize:12 }}>{error}</div>
      )}

      {hw && (
        <>
          <Row
            label="RAM Total"
            value={`${hw.total_ram_gb} GB`}
          />
          <Row
            label="RAM Available"
            value={`${hw.available_ram_gb} GB`}
            sub={<Bar value={hw.available_ram_gb} max={hw.total_ram_gb} color="#3fb950" />}
          />
          {hw.gpu_vram_gb > 0 && (
            <Row
              label="GPU VRAM"
              value={`${hw.gpu_vram_gb} GB`}
              sub={<Bar value={hw.gpu_vram_gb} max={24} color="#a371f7" />}
            />
          )}
          <Row label="CPU Cores" value={hw.cpu_count} />
          <Row label="Safe Model Limit" value={`${hw.safe_limit_gb} GB`} />

          <hr style={{ border:"none", borderTop:"1px solid #21262d", margin:"10px 0" }} />

          <div style={{ marginBottom:4 }}>
            <span style={{ color:"#8b949e", fontSize:11 }}>Active Models</span>
          </div>
          <div style={{ display:"flex", flexDirection:"column", gap:4 }}>
            {[
              ["Chat",     hw.active_models?.default ?? hw.chat_model,   "#58a6ff"],
              ["Coding",   hw.active_models?.coding  ?? hw.coding_model, "#3fb950"],
            ].map(([label, model, color]) => (
              <div key={label} style={{
                display:"flex", alignItems:"center", gap:8,
                background:"#0d1117", borderRadius:6, padding:"5px 8px",
              }}>
                <span style={{
                  fontSize:10, fontWeight:700, color,
                  minWidth:42,
                }}>
                  {label}
                </span>
                <code style={{
                  color:"#e6edf3", fontSize:11,
                  overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap",
                }}>
                  {model ?? "—"}
                </code>
              </div>
            ))}
          </div>

          <div style={{ marginTop:10, fontSize:11, color:"#8b949e", lineHeight:1.5 }}>
            💡 ISE AI automatically selects the best model for your hardware.
            Override with <code style={{ color:"#58a6ff" }}>DEFAULT_MODEL</code> in <code>.env</code>.
          </div>
        </>
      )}
    </div>
  );
}
