# gateway_mobile — Flutter Mobile Gateway

Mobile client untuk My Agent Framework.

## Setup

```bash
flutter pub get
flutter run
```

## Konfigurasi

Ubah `apiBaseUrl` di Settings screen ke URL server framework kamu.

## Build

```bash
# Android APK
flutter build apk --release

# Android App Bundle
flutter build appbundle --release

# iOS (di Mac)
flutter build ios --release
```

## Struktur

```
lib/
├── main.dart               # Entry point
├── core/
│   ├── config.dart         # App configuration
│   └── api_client.dart     # REST + WebSocket client
├── models/
│   └── chat_message.dart   # Chat message model
├── providers/
│   ├── chat_provider.dart  # Chat state management
│   └── settings_provider.dart
└── screens/
    ├── chat_screen.dart    # Main chat UI
    └── settings_screen.dart
```
