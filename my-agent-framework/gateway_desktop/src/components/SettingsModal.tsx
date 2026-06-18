import { useState, useEffect } from "react";
import { useSettingsStore } from "../stores/settingsStore";
import { ApiClient } from "../api/client";

interface Props {
  onClose: () => void;
}

export default function SettingsModal({ onClose }: Props) {
  const { apiBaseUrl, temperature, setApiBaseUrl, setTemperature } = useSettingsStore();
  const [localUrl, setLocalUrl] = useState(apiBaseUrl);
  const [localTemp, setLocalTemp] = useState(temperature);
  const [models, setModels] = useState<string[]>([]);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<"" | "ok" | "fail">("");

  useEffect(() => {
    const client = new ApiClient(localUrl);
    client.getModels().then(setModels).catch(() => setModels([]));
  }, []);

  const handleTest = async () => {
    setTesting(true);
    setTestResult("");
    const client = new ApiClient(localUrl.trim());
    const result = await client.checkHealth();
    setTestResult(result.ok ? "ok" : "fail");
    setTesting(false);
  };

  const handleSave = () => {
    setApiBaseUrl(localUrl.trim());
    setTemperature(localTemp);
    onClose();
  };

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <h2 className="modal-title">⚙️ Pengaturan</h2>

        {/* API URL */}
        <div className="form-group">
          <label className="form-label">API Base URL</label>
          <div className="input-with-btn">
            <input
              type="text"
              className="form-input"
              value={localUrl}
              onChange={(e) => setLocalUrl(e.target.value)}
              placeholder="http://localhost:8000"
            />
            <button
              className={`test-btn ${testResult === "ok" ? "test-ok" : testResult === "fail" ? "test-fail" : ""}`}
              onClick={handleTest}
              disabled={testing}
            >
              {testing ? "..." : testResult === "ok" ? "✓ OK" : testResult === "fail" ? "✗ Gagal" : "Test"}
            </button>
          </div>
          {testResult === "fail" && (
            <p className="form-hint-err">Tidak dapat terhubung ke server. Pastikan framework berjalan.</p>
          )}
        </div>

        {/* Model Info */}
        {models.length > 0 && (
          <div className="form-group">
            <label className="form-label">Model Tersedia</label>
            <div className="model-tags">
              {models.map((m) => (
                <span key={m} className="model-tag">{m}</span>
              ))}
            </div>
          </div>
        )}

        {/* Temperature */}
        <div className="form-group">
          <label className="form-label">
            Temperature: <strong>{localTemp.toFixed(1)}</strong>
            <span className="form-hint"> (0 = deterministik, 1 = kreatif)</span>
          </label>
          <input
            type="range"
            min="0" max="1" step="0.05"
            value={localTemp}
            onChange={(e) => setLocalTemp(Number(e.target.value))}
            className="range-input"
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
