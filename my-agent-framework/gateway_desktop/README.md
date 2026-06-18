# gateway_desktop — Electron + React Desktop Gateway

Desktop client untuk My Agent Framework (Windows, Mac, Linux).

## Setup

```bash
npm install
```

## Development

```bash
# Browser-only (Vite)
npm run dev

# Electron + React
npm run electron:dev
```

## Build

```bash
# Build distributable
npm run package
```

Output: `release/` folder

## Konfigurasi

Buka Settings (⚙️) dan ubah API Base URL ke alamat server framework kamu.

## Struktur

```
src/
├── main.tsx             # React entry point
├── App.tsx              # Root component
├── index.css            # Global styles (dark theme)
├── api/
│   └── client.ts        # REST + WebSocket client
├── stores/
│   ├── chatStore.ts     # Zustand chat state
│   └── settingsStore.ts # Zustand settings
└── components/
    ├── ChatWindow.tsx   # Main chat area
    ├── MessageBubble.tsx# Pesan user/assistant
    ├── InputBar.tsx     # Text input + send button
    ├── Sidebar.tsx      # Navigation sidebar
    └── SettingsModal.tsx# Popup settings
electron/
├── main.js              # Electron main process
└── preload.js           # Context bridge
```
