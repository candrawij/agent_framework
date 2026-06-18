import { useState } from "react";
import { useSettingsStore } from "../stores/settingsStore";

interface Props {
  onClose: () => void;
}

export default function SettingsModal({ onClose }: Props) {
  const { apiBaseUrl, temperature, setApiBaseUrl, setTemperature } = useSettingsStore();
  const [localUrl, setLocalUrl] = useState(apiBaseUrl);
  const [localTemp, setLocalTemp] = useState(temperature);

  const handleSave = () => {
    setApiBaseUrl(localUrl.trim());
    setTemperature(localTemp);
    onClose();
  };

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <h2 className="modal-title">⚙️ Pengaturan</h2>

        <div className="form-group">
          <label className="form-label">API Base URL</label>
          <input
            type="text"
            className="form-input"
            value={localUrl}
            onChange={(e) => setLocalUrl(e.target.value)}
            placeholder="http://localhost:8000"
          />
        </div>

        <div className="form-group">
          <label className="form-label">Temperature: {localTemp.toFixed(1)}</label>
          <input
            type="range"
            min="0" max="1" step="0.1"
            value={localTemp}
            onChange={(e) => setLocalTemp(Number(e.target.value))}
            style={{ width: "100%" }}
          />
        </div>

        <div className="btn-row">
          <button className="btn btn-secondary" onClick={onClose}>Batal</button>
          <button className="btn btn-primary" onClick={handleSave}>Simpan</button>
        </div>
      </div>
    </div>
  );
}
