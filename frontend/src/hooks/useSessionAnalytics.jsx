import { useEffect, useState } from "react";
import { api, fetchJson } from "../lib/api";

export default function useSessionAnalytics(sessionId, fallback = {}) {
  const [data, setData] = useState({
    session_id: sessionId || "",
    visualization: fallback.visualization || null,
    render_blocks: fallback.render_blocks || [],
    artifacts: fallback.artifacts || [],
    has_context: Boolean(
      fallback.visualization || (fallback.render_blocks || []).length || (fallback.artifacts || []).length,
    ),
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!sessionId) {
      setData({
        session_id: "",
        visualization: fallback.visualization || null,
        render_blocks: fallback.render_blocks || [],
        artifacts: fallback.artifacts || [],
        has_context: Boolean(
          fallback.visualization || (fallback.render_blocks || []).length || (fallback.artifacts || []).length,
        ),
      });
      return undefined;
    }

    let cancelled = false;

    async function loadAnalytics() {
      setLoading(true);
      setError("");
      try {
        const response = await fetchJson(`${api.sessionAnalytics}?session_id=${encodeURIComponent(sessionId)}`);
        if (!cancelled) {
          setData(response);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError.message || "Failed to load session analytics.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadAnalytics();
    return () => {
      cancelled = true;
    };
  }, [fallback.artifacts, fallback.render_blocks, fallback.visualization, sessionId]);

  return { data, loading, error };
}
