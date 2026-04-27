import { useEffect, useState } from "react";
import { fetchJson } from "../../lib/api";
export default function AdminControlDashboard() {
  const [policy, setPolicy] = useState(null);
  const [status, setStatus] = useState("");
  useEffect(() => { fetchJson("/api/real-intelligence-v2/policy").then(setPolicy).catch((err) => setStatus(err.message)); }, []);
  async function update(key, value) {
    const next = { ...policy, [key]: value }; setPolicy(next);
    try { const saved = await fetchJson("/api/real-intelligence-v2/policy", { method: "PATCH", body: JSON.stringify({ [key]: value }) }); setPolicy(saved); setStatus("Saved"); }
    catch (err) { setStatus(err.message); }
  }
  if (!policy) return <section className="admin-control-dashboard"><strong>Loading admin controls...</strong><p>{status}</p></section>;
  return <section className="admin-control-dashboard"><header><div><p className="eyebrow">Admin control layer</p><h3>Agent policy dashboard</h3></div><span>{status}</span></header><label>Autonomy mode<select value={policy.autonomy_mode} onChange={(e) => update("autonomy_mode", e.target.value)}><option value="manual">Manual</option><option value="assisted">Assisted</option><option value="autonomous">Autonomous</option></select></label><label>Max repair attempts<input type="number" min="0" max="10" value={policy.max_repair_attempts} onChange={(e) => update("max_repair_attempts", Number(e.target.value))} /></label><label><input type="checkbox" checked={!!policy.require_build_before_export} onChange={(e) => update("require_build_before_export", e.target.checked)} /> Require build before export</label><label><input type="checkbox" checked={!!policy.block_generic_output} onChange={(e) => update("block_generic_output", e.target.checked)} /> Block generic/template output</label><label><input type="checkbox" checked={!!policy.allow_shell_commands} onChange={(e) => update("allow_shell_commands", e.target.checked)} /> Allow shell commands</label></section>;
}
