import { MessageSquare, Settings, RotateCcw, Bot } from "lucide-react";
import { useChatStore } from "../stores/chatStore";

interface Props {
  onOpenSettings: () => void;
}

export default function Sidebar({ onOpenSettings }: Props) {
  const { clearSession } = useChatStore();

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="sidebar-logo-icon">
          <Bot size={18} color="white" />
        </div>
        <span className="sidebar-logo-text">Agent Framework</span>
      </div>

      <button className="sidebar-btn active">
        <MessageSquare size={16} />
        Chat
      </button>

      <div className="sidebar-spacer" />

      <button className="sidebar-btn" onClick={clearSession}>
        <RotateCcw size={16} />
        Sesi Baru
      </button>

      <button className="sidebar-btn" onClick={onOpenSettings}>
        <Settings size={16} />
        Pengaturan
      </button>
    </aside>
  );
}
