import { useEffect, useState } from "react";
import { api, fetchJson } from "../lib/api";

export default function useSessionArtifacts(sessionId, initialArtifacts = []) {
  const [artifacts, setArtifacts] = useState(initialArtifacts);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!sessionId) {
      setArtifacts(initialArtifacts);
      return undefined;
    }

    let cancelled = false;

    async function loadArtifacts() {
      setLoading(true);
      setError("");
      try {
        const data = await fetchJson(`${api.artifacts}?session_id=${encodeURIComponent(sessionId)}`);
        if (!cancelled) {
          setArtifacts(data.artifacts || []);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError.message || "Failed to load session artifacts.");
          setArtifacts(initialArtifacts);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadArtifacts();
    return () => {
      cancelled = true;
    };
  }, [initialArtifacts, sessionId]);

  return {
    artifacts,
    loading,
    error,
  };
}
