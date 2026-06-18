import { useState } from "react";
import ChatWindow from "./components/ChatWindow";
import Sidebar from "./components/Sidebar";
import SettingsModal from "./components/SettingsModal";
import { useSettingsStore } from "./stores/settingsStore";

export default function App() {
  const [showSettings, setShowSettings] = useState(false);
  const { theme } = useSettingsStore();

  return (
    <div className={`app-root ${theme}`}>
      <div className="app-layout">
        <Sidebar onOpenSettings={() => setShowSettings(true)} />
        <main className="chat-main">
          <ChatWindow />
        </main>
      </div>
      {showSettings && <SettingsModal onClose={() => setShowSettings(false)} />}
    </div>
  );
}
