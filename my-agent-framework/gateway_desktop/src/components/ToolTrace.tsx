import { useState } from "react";
import { ChevronDown, ChevronRight, Terminal, Clock, Calculator, File, Globe, Zap } from "lucide-react";

export interface ToolCallEntry {
  tool: string;
  arguments: Record<string, any>;
  success: boolean;
  output?: string;
  error?: string;
  duration_ms?: number;
}

interface Props {
  trace: ToolCallEntry[];
}

const TOOL_ICONS: Record<string, React.ElementType> = {
  get_datetime: Clock,
  calculator: Calculator,
  read_file: File,
  write_file: File,
  list_folder: File,
  search_files: File,
  http_request: Globe,
};

function ToolIcon({ name }: { name: string }) {
  const Icon = TOOL_ICONS[name] ?? Terminal;
  return <Icon size={13} />;
}

function SingleTrace({ entry }: { entry: ToolCallEntry }) {
  const [open, setOpen] = useState(false);
  const argStr = JSON.stringify(entry.arguments, null, 2);
  const hasArgs = Object.keys(entry.arguments).length > 0;

  return (
    <div className={`tool-trace-entry ${entry.success ? "trace-ok" : "trace-err"}`}>
      <button className="trace-header" onClick={() => setOpen((v) => !v)}>
        <span className="trace-icon">
          <ToolIcon name={entry.tool} />
        </span>
        <span className="trace-name">{entry.tool}</span>
        {entry.duration_ms !== undefined && (
          <span className="trace-duration">{entry.duration_ms}ms</span>
        )}
        <span className={`trace-badge ${entry.success ? "badge-ok" : "badge-err"}`}>
          {entry.success ? "✓" : "✗"}
        </span>
        {open ? <ChevronDown size={12} className="trace-chevron" /> : <ChevronRight size={12} className="trace-chevron" />}
      </button>

      {open && (
        <div className="trace-body">
          {hasArgs && (
            <div className="trace-section">
              <span className="trace-section-label">Arguments</span>
              <pre className="trace-code">{argStr}</pre>
            </div>
          )}
          <div className="trace-section">
            <span className="trace-section-label">
              {entry.success ? "Output" : "Error"}
            </span>
            <pre className={`trace-code ${entry.success ? "" : "trace-code-err"}`}>
              {entry.success ? (entry.output ?? "—") : (entry.error ?? "Unknown error")}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}

export default function ToolTrace({ trace }: Props) {
  const [collapsed, setCollapsed] = useState(false);
  if (!trace || trace.length === 0) return null;

  const allOk = trace.every((t) => t.success);

  return (
    <div className="tool-trace-container">
      <button className="tool-trace-toggle" onClick={() => setCollapsed((v) => !v)}>
        <Zap size={12} className="trace-zap" />
        <span>{trace.length} tool{trace.length > 1 ? "s" : ""} dipanggil</span>
        <span className={`trace-summary-badge ${allOk ? "badge-ok" : "badge-err"}`}>
          {allOk ? "Semua berhasil" : "Ada error"}
        </span>
        {collapsed ? <ChevronRight size={12} /> : <ChevronDown size={12} />}
      </button>
      {!collapsed && (
        <div className="tool-trace-list">
          {trace.map((entry, i) => (
            <SingleTrace key={i} entry={entry} />
          ))}
        </div>
      )}
    </div>
  );
}
