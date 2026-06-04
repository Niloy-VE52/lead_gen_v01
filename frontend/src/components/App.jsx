import { useState, useEffect, useCallback } from "react";

import "../styles/global.css";
import { apiPost, apiGet } from "../api/client";
import { DEFAULT_CONFIG } from "../constants/defaults";

import Topbar from "./Topbar";
import Sidebar from "./Sidebar";
import RunPage from "./RunPage";
import RunHistory from "./RunHistory";

export default function App() {
  const [config, setConfig]           = useState(DEFAULT_CONFIG);
  const [activeRunId, setActiveRunId] = useState(null);
  const [runs, setRuns]               = useState([]);
  const [launching, setLaunching]     = useState(false);
  const [error, setError]             = useState(null);
  const [tab, setTab]                 = useState("run");
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const handleRunDone = useCallback((data) => {
    setRuns((prev) =>
      prev.map((r) => (r.run_id === data.run_id ? { ...r, ...data } : r))
    );
  }, []);

  useEffect(() => {
    const runningRuns = runs.filter((r) => r.status === "running");
    if (runningRuns.length === 0) return;

    const timers = runningRuns.map((r) =>
      setInterval(async () => {
        try {
          const d = await apiGet(`/status/${r.run_id}`);
          setRuns((prev) =>
            prev.map((x) => (x.run_id === d.run_id ? { ...x, ...d } : x))
          );
        } catch (_) {}
      }, 3000)
    );

    return () => timers.forEach(clearInterval);
  }, [runs.length]);

  const launch = async () => {
    setError(null);
    setLaunching(true);
    try {
      const res = await apiPost("/run-full", config);
      const newRun = { run_id: res.run_id, status: "running", step: "Starting…" };
      setRuns((prev) => [...prev, newRun]);
      setActiveRunId(res.run_id);
      setTab("run");
    } catch (e) {
      setError(e.message);
    } finally {
      setLaunching(false);
    }
  };

  return (
    <div className="app">
      <Topbar
        runs={runs}
        sidebarOpen={sidebarOpen}
        onToggleSidebar={() => setSidebarOpen((v) => !v)}
      />

      <div className="main">
        <Sidebar
          tab={tab}
          onTabChange={setTab}
          runCount={runs.length}
          className={sidebarOpen ? "" : "collapsed"}
        />

        <div className="content">
          {tab === "run" && (
            <RunPage
              config={config}
              onConfigChange={setConfig}
              onLaunch={launch}
              launching={launching}
              error={error}
              activeRunId={activeRunId}
              onRunDone={handleRunDone}
            />
          )}

          {tab === "history" && (
            <>
              <div className="section-heading">All Pipeline Runs — This Session</div>
              <RunHistory runs={runs} activeRunId={activeRunId} />
            </>
          )}
        </div>
      </div>
    </div>
  );
}