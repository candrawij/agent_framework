import { create } from "zustand";

interface SettingsState {
  apiBaseUrl: string;
  theme: "dark" | "light";
  temperature: number;
  setApiBaseUrl: (url: string) => void;
  setTheme: (theme: "dark" | "light") => void;
  setTemperature: (t: number) => void;
}

const DEFAULT_API_URL =
  typeof window !== "undefined" && (window as any).electronAPI?.isElectron
    ? "http://localhost:8000"
    : "http://localhost:8000";

export const useSettingsStore = create<SettingsState>((set) => ({
  apiBaseUrl: localStorage.getItem("api_url") ?? DEFAULT_API_URL,
  theme: (localStorage.getItem("theme") as "dark" | "light") ?? "dark",
  temperature: Number(localStorage.getItem("temperature") ?? "0.7"),

  setApiBaseUrl: (apiBaseUrl) => {
    localStorage.setItem("api_url", apiBaseUrl);
    set({ apiBaseUrl });
  },
  setTheme: (theme) => {
    localStorage.setItem("theme", theme);
    set({ theme });
  },
  setTemperature: (temperature) => {
    localStorage.setItem("temperature", String(temperature));
    set({ temperature });
  },
}));
