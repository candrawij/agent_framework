import { useState, useEffect } from "react";
import { MessageSquare, Settings, Plus, Trash2, Bot, Wifi, WifiOff } from "lucide-react";
import { useSessionStore } from "../stores/sessionStore";
import { useChatStore } from "../stores/chatStore";
import { useSettingsStore } from "../stores/settingsStore";
import { ApiClient } from "../api/client";

interface Props {
  onOpenSettings: () => void;
}

export default function Sidebar({ onOpenSettings }: Props) {
  const { sessions, activeSessionId, createSession, deleteSession, setActiveSession } = useSessionStore();
  const { clearSession } = useChatStore();
  const { apiBaseUrl } = useSettingsStore();
  const [connected, setConnected] = useState<boolean | null>(null);
  const [model, setModel] = useState<string>("");
  const [renamingId, setRenamingId] = useState<string | null>(null);

  // Health check setiap 10 detik
  useEffect(() => {
    const check = async () => {
      const client = new ApiClient(apiBaseUrl);
      const result = await client.checkHealth();
      setConnected(result.ok);
      if (result.model) setModel(result.model);
    };
    check();
    const timer = setInterval(check, 10000);
    return () => clearInterval(timer);
  }, [apiBaseUrl]);

  const handleNewSession = () => {
    createSession(`Sesi ${sessions.length + 1}`);
  };

  const handleDeleteSession = (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation();
    clearSession(sessionId);
    deleteSession(sessionId);
  };

  const handleSelectSession = (sessionId: string) => {
    setActiveSession(sessionId);
  };

  return (
    <aside className="sidebar">
      {/* Logo */}
      <div className="sidebar-logo">
        <div className="sidebar-logo-icon">
          <Bot size={18} color="white" />
        </div>
        <div className="sidebar-logo-info">
          <span className="sidebar-logo-text">Agent Framework</span>
          {model && <span className="sidebar-model-tag">{model}</span>}
        </div>
      </div>

      {/* Connection Status */}
      <div className="connection-status">
        {connected === null ? (
          <><span className="conn-dot conn-checking" /><span>Memeriksa...</span></>
        ) : connected ? (
          <><Wifi size={13} className="conn-icon conn-ok" /><span className="conn-label">Terhubung</span></>
        ) : (
          <><WifiOff size={13} className="conn-icon conn-err" /><span className="conn-label conn-label-err">Tidak terhubung</span></>
        )}
      </div>

      {/* New Session Button */}
      <button className="sidebar-new-btn" onClick={handleNewSession}>
        <Plus size={14} />
        Sesi Baru
      </button>

      {/* Session List */}
      <div className="session-list">
        {sessions.length === 0 && (
          <p className="session-empty">Belum ada sesi</p>
        )}
        {sessions.map((sess) => (
          <div
            key={sess.id}
            className={`session-item ${sess.id === activeSessionId ? "active" : ""}`}
            onClick={() => handleSelectSession(sess.id)}
          >
            <MessageSquare size={14} className="session-icon" />
            <div className="session-info">
              <span className="session-name">{sess.name}</span>
              {sess.lastMessage && (
                <span className="session-preview">{sess.lastMessage}</span>
              )}
            </div>
            <button
              className="session-delete-btn"
              onClick={(e) => handleDeleteSession(e, sess.id)}
              title="Hapus sesi"
            >
              <Trash2 size={12} />
            </button>
          </div>
        ))}
      </div>

      <div className="sidebar-spacer" />

      {/* Settings */}
      <button className="sidebar-btn" onClick={onOpenSettings}>
        <Settings size={16} />
        Pengaturan
      </button>
    </aside>
  );
}
