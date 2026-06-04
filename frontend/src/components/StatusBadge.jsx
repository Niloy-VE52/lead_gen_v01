const STATUS_MAP = {
  running: { label: "RUNNING", cls: "badge-running" },
  done:    { label: "DONE",    cls: "badge-done"    },
  error:   { label: "ERROR",   cls: "badge-error"   },
};

export default function StatusBadge({ status }) {
  const { label, cls } = STATUS_MAP[status] || {
    label: status?.toUpperCase(),
    cls: "badge-idle",
  };
  return <span className={`badge ${cls}`}>{label}</span>;
}
