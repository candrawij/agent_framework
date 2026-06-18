interface Props {
  status: "idle" | "thinking" | "responding" | "error";
}

const STATUS_CONFIG = {
  idle: { label: "", dot: "" },
  thinking: { label: "Thinking...", dot: "dot-thinking" },
  responding: { label: "Responding...", dot: "dot-responding" },
  error: { label: "Error", dot: "dot-error" },
};

export default function StatusBar({ status }: Props) {
  const config = STATUS_CONFIG[status];
  if (status === "idle") return null;

  return (
    <div className="status-bar">
      <span className={`status-dot ${config.dot}`} />
      <span className="status-label">{config.label}</span>
    </div>
  );
}
