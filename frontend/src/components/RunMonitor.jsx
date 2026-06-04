import { useState, useEffect, useCallback, useRef } from "react";
import { apiGet } from "../api/client";
import StatusBadge from "./StatusBadge";

export default function RunMonitor({ runId, onDone }) {
  const [data, setData] = useState(null);
  const intervalRef = useRef(null);

  const poll = useCallback(async () => {
    try {
      const d = await apiGet(`/status/${runId}`);
      setData(d);
      if (d.status === "done" || d.status === "error") {
        clearInterval(intervalRef.current);
        onDone?.(d);
      }
    } catch (e) {
      console.error(e);
    }
  }, [runId, onDone]);

  useEffect(() => {
    poll();
    intervalRef.current = setInterval(poll, 2500);
    return () => clearInterval(intervalRef.current);
  }, [poll]);

  if (!data) return <div className="monitor-loading">Connecting…</div>;

  return (
    <div className="monitor-card">
      <div className="monitor-header">
        <span className="monitor-id">#{data.run_id}</span>
        <StatusBadge status={data.status} />
      </div>

      <div className="monitor-step">{data.step}</div>

      {data.jobs_added !== undefined && (
        <div className="monitor-meta">
          Jobs saved: <strong>{data.jobs_added}</strong>
        </div>
      )}
      {data.scored !== undefined && (
        <div className="monitor-meta">
          Jobs scored: <strong>{data.scored}</strong>
        </div>
      )}
      {data.error && (
        <div className="monitor-error">{data.error}</div>
      )}
      {data.status === "running" && <div className="pulse-bar" />}
    </div>
  );
}
